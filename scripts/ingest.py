"""
Chat JSON → Supabase Vector Database Ingester
==============================================
Takes the JSON output from convert_export.py and:
  1. Generates 384-dim embeddings using sentence-transformers (all-MiniLM-L6-v2)
  2. Inserts them into Supabase's chat_embeddings table (pgvector)
  3. Supports per-contact collections and a global fallback

Usage:
    # Ingest a single contact's chat
    python ingest.py --chat chats/harshit.json --contact "harshit"

    # Ingest all JSON files in a folder + create global style
    python ingest.py --all-chats chats/ --global-style

    # Show stats for all ingested data
    python ingest.py --stats

    # Clear a contact's embeddings and re-ingest
    python ingest.py --clear "harshit"
    python ingest.py --chat chats/harshit.json --contact "harshit"
"""

import json
import argparse
import sys
import os
import random
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from server/.env
# Try multiple locations
for env_path in [
    Path(__file__).parent.parent / "server" / ".env",
    Path(__file__).parent / ".env",
    Path(".env"),
]:
    if env_path.exists():
        load_dotenv(env_path)
        break

# ─── Lazy imports (heavy libraries) ───
_model = None
_supabase = None


def get_embedding_model():
    """Lazy-load the sentence transformer model (downloads ~90MB on first run)."""
    global _model
    if _model is None:
        print("🔄 Loading embedding model (all-MiniLM-L6-v2)...")
        print("   (First run will download ~90MB — subsequent runs use cache)")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        print("   ✅ Model loaded!")
    return _model


def get_supabase_client():
    """Lazy-load the Supabase client."""
    global _supabase
    if _supabase is None:
        from supabase import create_client
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set!")
            print("   Set them in server/.env or as environment variables")
            print("   Get them from: Supabase Dashboard → Project Settings → API")
            sys.exit(1)
        
        _supabase = create_client(url, key)
        print(f"   ✅ Connected to Supabase: {url[:40]}...")
    return _supabase


def generate_embeddings(texts: list[str], batch_size: int = 64) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    Uses batching for efficiency with large datasets.
    
    Returns:
        List of 384-dimensional float vectors
    """
    model = get_embedding_model()
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = model.encode(batch, show_progress_bar=False)
        all_embeddings.extend(embeddings.tolist())
        
        if len(texts) > batch_size:
            progress = min(i + batch_size, len(texts))
            print(f"   📊 Embedded {progress}/{len(texts)} texts...")
    
    return all_embeddings


def ingest_single_contact(chat_file: str, contact_id: str):
    """
    Ingest a single contact's JSON chat file into Supabase.
    
    Args:
        chat_file: Path to the JSON file (output of convert_export.py)
        contact_id: Unique identifier for this contact (e.g., "harshit")
    """
    # Load JSON pairs
    file_path = Path(chat_file)
    if not file_path.exists():
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)
    
    with open(file_path, "r", encoding="utf-8") as f:
        pairs = json.load(f)
    
    if not pairs:
        print(f"⚠️  No pairs found in {file_path}")
        return
    
    print(f"\n📂 Ingesting: {file_path.name} → contact '{contact_id}'")
    print(f"   📝 {len(pairs)} trigger→reply pairs to embed")
    
    # Generate embeddings for the TRIGGER texts
    # (We search by what the other person said, to find how you replied)
    trigger_texts = [p["trigger"] for p in pairs]
    print("   🧮 Generating embeddings...")
    embeddings = generate_embeddings(trigger_texts)
    
    # Prepare rows for Supabase
    rows = []
    for pair, embedding in zip(pairs, embeddings):
        rows.append({
            "contact_id": contact_id,
            "trigger_text": pair["trigger"],
            "reply_text": pair["reply"],
            "embedding": embedding,
        })
    
    # Insert into Supabase in batches (Supabase has a row limit per insert)
    supabase = get_supabase_client()
    batch_size = 500
    total_inserted = 0
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        result = supabase.table("chat_embeddings").insert(batch).execute()
        total_inserted += len(batch)
        print(f"   💾 Inserted {total_inserted}/{len(rows)} rows...")
    
    print(f"   ✅ Done! {total_inserted} examples ingested for '{contact_id}'")


def ingest_all_chats(chats_dir: str, create_global: bool = False):
    """
    Ingest all JSON files in a directory.
    Contact ID is derived from the filename (e.g., harshit.json → "harshit").
    
    Args:
        chats_dir: Path to directory containing .json chat files
        create_global: If True, also create a 'global' collection with samples from all contacts
    """
    chats_path = Path(chats_dir)
    if not chats_path.exists():
        print(f"❌ Error: Directory not found: {chats_path}")
        sys.exit(1)
    
    json_files = sorted(chats_path.glob("*.json"))
    if not json_files:
        print(f"⚠️  No .json files found in {chats_path}")
        print("   Run convert_export.py first to create JSON files from WhatsApp exports")
        sys.exit(1)
    
    print(f"📁 Found {len(json_files)} JSON files in {chats_path}")
    
    all_pairs_for_global = []
    
    for json_file in json_files:
        contact_id = json_file.stem  # filename without extension
        ingest_single_contact(str(json_file), contact_id)
        
        if create_global:
            with open(json_file, "r", encoding="utf-8") as f:
                pairs = json.load(f)
                all_pairs_for_global.extend(pairs)
    
    # Create global style collection
    if create_global and all_pairs_for_global:
        print(f"\n🌍 Creating global style collection...")
        # Sample up to 200 pairs from all contacts combined
        max_global = min(200, len(all_pairs_for_global))
        sampled = random.sample(all_pairs_for_global, max_global)
        
        # Save to a temp file and ingest
        global_path = chats_path / "_global_temp.json"
        with open(global_path, "w", encoding="utf-8") as f:
            json.dump(sampled, f, ensure_ascii=False)
        
        ingest_single_contact(str(global_path), "global")
        global_path.unlink()  # Clean up temp file
        
        print(f"   ✅ Global collection: {max_global} examples from {len(json_files)} contacts")


def show_stats():
    """Show ingestion statistics from Supabase."""
    supabase = get_supabase_client()
    
    print("\n📊 Embedding Statistics:")
    print("=" * 50)
    
    # Get all unique contact IDs and their counts
    result = supabase.table("chat_embeddings") \
        .select("contact_id") \
        .execute()
    
    if not result.data:
        print("   (No data yet — run ingest.py with --chat or --all-chats first)")
        return
    
    # Count per contact
    contact_counts = {}
    for row in result.data:
        cid = row["contact_id"]
        contact_counts[cid] = contact_counts.get(cid, 0) + 1
    
    total = 0
    for contact_id, count in sorted(contact_counts.items()):
        icon = "🌍" if contact_id == "global" else "👤"
        print(f"   {icon} {contact_id:20s} → {count:5d} examples")
        total += count
    
    print("-" * 50)
    print(f"   📦 Total: {total} embeddings across {len(contact_counts)} collections")
    
    # Conversation history stats
    hist_result = supabase.table("conversation_history") \
        .select("contact_id") \
        .execute()
    
    if hist_result.data:
        hist_counts = {}
        for row in hist_result.data:
            cid = row["contact_id"]
            hist_counts[cid] = hist_counts.get(cid, 0) + 1
        
        print(f"\n💬 Conversation History:")
        for contact_id, count in sorted(hist_counts.items()):
            print(f"   💬 {contact_id:20s} → {count:5d} messages")
    else:
        print(f"\n💬 Conversation History: (empty — will fill as bot operates)")


def clear_contact(contact_id: str):
    """Delete all embeddings for a specific contact."""
    supabase = get_supabase_client()
    
    result = supabase.table("chat_embeddings") \
        .delete() \
        .eq("contact_id", contact_id) \
        .execute()
    
    print(f"🗑️  Cleared all embeddings for contact '{contact_id}'")


def main():
    parser = argparse.ArgumentParser(
        description="Ingest chat JSON files into Supabase vector database"
    )
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--chat",
        help="Path to a single JSON chat file to ingest"
    )
    group.add_argument(
        "--all-chats",
        help="Path to directory containing all JSON chat files"
    )
    group.add_argument(
        "--stats",
        action="store_true",
        help="Show ingestion statistics"
    )
    group.add_argument(
        "--clear",
        metavar="CONTACT_ID",
        help="Clear all embeddings for a contact"
    )
    
    parser.add_argument(
        "--contact",
        help="Contact ID for single chat ingestion (e.g., 'harshit')"
    )
    parser.add_argument(
        "--global-style",
        action="store_true",
        help="Also create a global style collection from all contacts"
    )
    
    args = parser.parse_args()
    
    if args.chat:
        if not args.contact:
            # Derive contact from filename
            args.contact = Path(args.chat).stem
            print(f"ℹ️  No --contact specified, using filename: '{args.contact}'")
        ingest_single_contact(args.chat, args.contact)
    
    elif args.all_chats:
        ingest_all_chats(args.all_chats, create_global=args.global_style)
    
    elif args.stats:
        show_stats()
    
    elif args.clear:
        clear_contact(args.clear)
    
    print("\n✨ Done!")


if __name__ == "__main__":
    main()
