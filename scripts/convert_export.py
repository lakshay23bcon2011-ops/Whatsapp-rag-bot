"""
WhatsApp Chat Export → JSON Converter
=====================================
Converts a WhatsApp .txt export into structured JSON pairs:
  (what they said) → (how you replied)

Usage:
    python convert_export.py <chat_file.txt> --your-name "~" --output output.json

The script:
  1. Parses the WhatsApp export format: [DD/MM/YY, HH:MM:SS] Sender: message
  2. Identifies YOUR messages vs the OTHER person's messages
  3. Merges consecutive messages from the same sender into one block
  4. Creates trigger→reply pairs (they said X, you replied Y)
  5. Filters out system messages, media, calls, etc.
  6. Outputs clean JSON ready for embedding ingestion
"""

import re
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime


# ─── Patterns to skip (not actual chat messages) ───
SKIP_PATTERNS = [
    "image omitted",
    "video omitted",
    "audio omitted",
    "sticker omitted",
    "document omitted",
    "Contact card omitted",
    "GIF omitted",
    "Messages and calls are end-to-end encrypted",
    "This message was deleted",
    "You deleted this message",
    "missed voice call",
    "missed video call",
    "<This message was edited>",
    "location:",
    "https://maps.google.com",
]

# Regex for a WhatsApp message line
# Format: [DD/MM/YY, HH:MM:SS AM/PM] Sender: Message
# Handles both 12h and 24h formats, and various date separators
MESSAGE_PATTERN = re.compile(
    r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]?\s+(.+?):\s(.+)$"
)

# Patterns for system/call messages (no sender: prefix)
SYSTEM_PATTERNS = [
    "Video call",
    "Voice call",
    "Missed voice call",
    "Missed video call",
    "changed the subject",
    "changed this group",
    "added you",
    "removed you",
    "left the group",
    "created group",
    "changed the group",
    "security code changed",
]


def is_skip_message(text: str) -> bool:
    """Check if a message should be skipped (media, system, etc.)."""
    text_lower = text.lower().strip()
    # Remove the Unicode left-to-right mark and other control chars
    text_clean = text.replace("\u200e", "").replace("\u200f", "").strip()
    
    for pattern in SKIP_PATTERNS:
        if pattern.lower() in text_lower:
            return True
    
    for pattern in SYSTEM_PATTERNS:
        if pattern.lower() in text_lower:
            return True
    
    # Skip very short meaningless messages
    if text_clean in [".", "..", "...", "‎", ""]:
        return True
    
    return False


def parse_whatsapp_export(filepath: str, your_name: str) -> list[dict]:
    """
    Parse a WhatsApp .txt export file into a list of message dicts.
    
    Returns:
        List of {sender, message, timestamp, is_you} dicts
    """
    messages = []
    current_message = None
    
    with open(filepath, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            
            # Remove Unicode control characters that WhatsApp adds
            line = line.replace("\u200e", "").replace("\u200f", "")
            
            match = MESSAGE_PATTERN.match(line)
            
            if match:
                # Save previous message if exists
                if current_message:
                    messages.append(current_message)
                
                date_str = match.group(1)
                time_str = match.group(2)
                sender = match.group(3).strip()
                text = match.group(4).strip()
                
                # Remove the edited tag from message text
                text = re.sub(r"\s*‎?<This message was edited>", "", text).strip()
                
                current_message = {
                    "sender": sender,
                    "message": text,
                    "date": date_str,
                    "time": time_str,
                    "is_you": sender == your_name,
                }
            else:
                # Continuation of previous message (multi-line)
                if current_message:
                    current_message["message"] += "\n" + line
    
    # Don't forget the last message
    if current_message:
        messages.append(current_message)
    
    return messages


def merge_consecutive_messages(messages: list[dict]) -> list[dict]:
    """
    Merge consecutive messages from the same sender into one block.
    People often send multiple short messages in a row — combine them.
    
    Example:
        "Hiii" + "Sun" + "Kha h" → "Hiii\nSun\nKha h"
    """
    if not messages:
        return []
    
    merged = []
    current = {**messages[0]}
    
    for msg in messages[1:]:
        if msg["sender"] == current["sender"]:
            # Same sender — merge
            current["message"] += "\n" + msg["message"]
        else:
            # Different sender — save current and start new
            merged.append(current)
            current = {**msg}
    
    merged.append(current)  # Don't forget the last block
    return merged


def create_trigger_reply_pairs(messages: list[dict]) -> list[dict]:
    """
    Create (trigger → reply) pairs from the merged message blocks.
    
    A pair is formed when:
        1. The other person sends a message (trigger)
        2. You reply next (reply)
    
    Only YOUR replies are stored — these are the style examples for RAG.
    """
    pairs = []
    
    for i in range(len(messages) - 1):
        current = messages[i]
        next_msg = messages[i + 1]
        
        # Pattern: they said something → you replied
        if not current["is_you"] and next_msg["is_you"]:
            trigger = current["message"].strip()
            reply = next_msg["message"].strip()
            
            # Skip if either side is a skip-worthy message
            if is_skip_message(trigger) or is_skip_message(reply):
                continue
            
            # Skip if either side is too short (just emojis, single char)
            if len(reply.strip()) < 2:
                continue
            
            pairs.append({
                "trigger": trigger,
                "reply": reply,
                "timestamp": f"{current['date']} {current['time']}",
            })
    
    return pairs


def convert_chat(filepath: str, your_name: str) -> list[dict]:
    """Full pipeline: parse → filter → merge → pair."""
    
    print(f"📂 Reading: {filepath}")
    
    # Step 1: Parse raw messages
    raw_messages = parse_whatsapp_export(filepath, your_name)
    print(f"   📝 Raw messages parsed: {len(raw_messages)}")
    
    # Step 2: Filter out skip-worthy messages
    filtered = [m for m in raw_messages if not is_skip_message(m["message"])]
    print(f"   🔍 After filtering system/media: {len(filtered)}")
    
    # Step 3: Merge consecutive messages
    merged = merge_consecutive_messages(filtered)
    print(f"   🔗 After merging consecutive: {len(merged)}")
    
    # Step 4: Create trigger→reply pairs
    pairs = create_trigger_reply_pairs(merged)
    print(f"   ✅ Trigger→Reply pairs created: {len(pairs)}")
    
    return pairs


def main():
    parser = argparse.ArgumentParser(
        description="Convert WhatsApp .txt export to JSON trigger→reply pairs"
    )
    parser.add_argument(
        "chat_file",
        help="Path to the WhatsApp .txt export file"
    )
    parser.add_argument(
        "--your-name",
        default="~",
        help="Your name as it appears in the export (default: '~' for self-exports)"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path (default: same name with .json extension)"
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=0,
        help="Print N sample pairs to preview (default: 0)"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.chat_file)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        sys.exit(1)
    
    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(".json")
    
    # Convert
    pairs = convert_chat(str(input_path), args.your_name)
    
    if not pairs:
        print("⚠️  No trigger→reply pairs found! Check:")
        print(f"   - Is '{args.your_name}' your correct sender name in the export?")
        print("   - Does the file have the standard WhatsApp export format?")
        sys.exit(1)
    
    # Save output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pairs, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved {len(pairs)} pairs to: {output_path}")
    
    # Preview if requested
    if args.preview > 0:
        print(f"\n📋 Preview (first {args.preview} pairs):")
        print("-" * 60)
        for i, pair in enumerate(pairs[:args.preview], 1):
            print(f"\n  [{i}] They said:")
            for line in pair["trigger"].split("\n"):
                print(f"      > {line}")
            print(f"  [{i}] You replied:")
            for line in pair["reply"].split("\n"):
                print(f"      < {line}")
        print("-" * 60)
    
    # Print stats
    avg_trigger_len = sum(len(p["trigger"]) for p in pairs) / len(pairs)
    avg_reply_len = sum(len(p["reply"]) for p in pairs) / len(pairs)
    print(f"\n📊 Stats:")
    print(f"   Total pairs: {len(pairs)}")
    print(f"   Avg trigger length: {avg_trigger_len:.0f} chars")
    print(f"   Avg reply length:   {avg_reply_len:.0f} chars")


if __name__ == "__main__":
    main()
