"""
WhatsApp RAG Bot — FastAPI Server
==================================
The core server that:
  1. Receives messages from the Android app (POST /reply)
  2. Queries Supabase pgvector for style-matching examples (RAG)
  3. Retrieves recent conversation history from Supabase
  4. Builds a rich prompt and calls Groq for fast inference
  5. Returns a reply that sounds exactly like you

Run locally:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Endpoints:
    POST /reply     → Main endpoint (Android app calls this)
    GET  /health    → Health check
    GET  /stats     → Vector DB statistics
    GET  /contacts  → List all contacts + message counts
    DELETE /history/{contact_id} → Clear conversation history for a contact
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env file
load_dotenv()

# ─── Configuration ───
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DISABLE_RAG = os.getenv("DISABLE_RAG", "false").lower() in {"1", "true", "yes", "on"}

# LLM Settings
LLM_MODEL = "llama-3.3-70b-versatile"  # Fast, smart, great at following instructions
LLM_TEMPERATURE = 0.75                  # Slightly creative but consistent
LLM_MAX_TOKENS = 256                    # WhatsApp messages are short

# RAG Settings
RAG_TOP_K = 8              # Number of style examples to retrieve
HISTORY_LIMIT = 10         # Number of recent messages to include as context

# ─── Logging ───
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# SYSTEM PROMPT — CUSTOMIZE THIS TO MATCH YOUR TEXTING STYLE
# ═══════════════════════════════════════════════════════════
SYSTEM_PROMPT = """You are acting as the phone's owner. Reply to WhatsApp messages EXACTLY as they would — same tone, vocabulary, slang, length, and energy.

CRITICAL RULES:
1. You speak in Hinglish (Hindi + English mix) — casual, warm, sometimes sarcastic
2. Use short replies unless the question genuinely needs detail
3. Common words you use: arre, hnn, bhai, yaar, toh, kya, hm, ok, ni, meko, terko, yrr, chal, hmm, accha
4. Use ? for engagement, ! for emphasis, ... for trailing off
5. NEVER sound like a bot, AI, or assistant — you ARE the person
6. Match the energy of the incoming message (chill → chill, excited → excited, angry → angry)
7. Reply ONLY with the message text — no quotes, no "Reply:", no explanations
8. If someone asks something you genuinely don't know, say something like "pata ni yaar" or "baad me batata hu"
9. Use emojis sparingly — only when the real person would (😂, 😭, 🥲, 😅 are common)
10. Sometimes be lazy in replying — single word answers are fine: "hm", "ok", "acha", "hnn"
11. You can use mild slang/abuse with close friends (bhai, bsdk, etc.) — match the relationship tone
12. NEVER use formal Hindi or Shudh Hindi — always casual/broken Hinglish
13. AVOID COMMAS — Don't use commas to separate thoughts. Instead:
    - Use NEW LINES (press enter) to separate ideas
    - Or just keep replies SHORT AND SINGLE PHRASE
    - Example GOOD: "game khel rha hu" or "game khel rha hu\nmovies baad me"
    - Example BAD: "game khel rha hu, movies baad me"
14. One-word or two-word answers are BEST — show you're lazy texting
"""


# ─── Request/Response Models ───
class MessageRequest(BaseModel):
    contact_id: str
    contact_name: str
    message: str


class MessageResponse(BaseModel):
    reply: str
    rag_examples_used: int = 0
    response_time_ms: int = 0


# ─── Global objects (initialized at startup) ───
embedding_model = None
supabase_client = None
groq_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize heavy objects at server startup, not on every request."""
    global embedding_model, supabase_client, groq_client
    
    logger.info("🚀 Starting WhatsApp RAG Bot Server...")
    
    # Validate env vars
    if not GROQ_API_KEY:
        logger.error("❌ GROQ_API_KEY not set! Get one from https://console.groq.com")
        raise RuntimeError("GROQ_API_KEY is required")
    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.error("❌ SUPABASE_URL/SUPABASE_KEY not set! Configure in .env")
        raise RuntimeError("Supabase credentials are required")
    
    # Embed model is heavy; load on first request to avoid startup timeouts.
    if DISABLE_RAG:
        logger.warning("⚠️  DISABLE_RAG is enabled — skipping embedding model load")
    else:
        logger.info("🧠 Embedding model will load on first request")
    
    # Connect to Supabase
    logger.info("🔗 Connecting to Supabase...")
    from supabase import create_client
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    logger.info("   ✅ Supabase connected")
    
    # Initialize Groq client
    logger.info("🤖 Initializing Groq client...")
    from groq import Groq
    groq_client = Groq(api_key=GROQ_API_KEY)
    logger.info("   ✅ Groq client ready")
    
    logger.info("✨ Server ready! Listening for messages...")
    
    yield  # Server is running
    
    logger.info("👋 Shutting down server...")


# ─── FastAPI App ───
app = FastAPI(
    title="WhatsApp RAG Bot",
    description="Personalized AI that replies to WhatsApp messages sounding exactly like you",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Android app to connect from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════
# CORE FUNCTIONS
# ═══════════════════════════════════════════════════════════

def _ensure_embedding_model() -> None:
    """Lazy-load the embedding model when needed."""
    global embedding_model
    if DISABLE_RAG:
        return
    if embedding_model is None:
        logger.info("🧮 Loading embedding model (all-MiniLM-L6-v2)...")
        from sentence_transformers import SentenceTransformer
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("   ✅ Embedding model ready")


def embed_text(text: str) -> list[float]:
    """Generate a 384-dim embedding for a single text."""
    _ensure_embedding_model()
    return embedding_model.encode(text).tolist()


def search_style_examples(contact_id: str, message: str, top_k: int = RAG_TOP_K) -> list[dict]:
    """
    Search Supabase pgvector for the most similar trigger messages.
    Returns style examples: how you replied to similar messages before.
    
    Falls back to 'global' collection if contact has no examples.
    """
    if DISABLE_RAG:
        return []
    query_embedding = embed_text(message)
    
    try:
        # Call the Supabase RPC function we created in schema.sql
        result = supabase_client.rpc("match_chat_embeddings", {
            "query_embedding": query_embedding,
            "match_contact_id": contact_id,
            "match_count": top_k,
        }).execute()
        
        if result.data:
            return result.data
        
        # If no results for this contact, try global fallback
        if contact_id != "global":
            logger.info(f"   ℹ️  No examples for '{contact_id}', using global fallback")
            result = supabase_client.rpc("match_chat_embeddings", {
                "query_embedding": query_embedding,
                "match_contact_id": "global",
                "match_count": top_k,
            }).execute()
            return result.data or []
        
        return []
    
    except Exception as e:
        logger.error(f"   ❌ RAG search failed: {e}")
        return []


def get_conversation_history(contact_id: str, limit: int = HISTORY_LIMIT) -> list[dict]:
    """Fetch recent conversation messages from Supabase for context."""
    try:
        result = supabase_client.table("conversation_history") \
            .select("role, message, created_at") \
            .eq("contact_id", contact_id) \
            .order("created_at", desc=True) \
            .limit(limit) \
            .execute()
        
        # Reverse to get chronological order (oldest first)
        messages = list(reversed(result.data)) if result.data else []
        return messages
    
    except Exception as e:
        logger.error(f"   ❌ History fetch failed: {e}")
        return []


def save_to_history(contact_id: str, contact_name: str, role: str, message: str):
    """Save a message to conversation history in Supabase."""
    try:
        supabase_client.table("conversation_history").insert({
            "contact_id": contact_id,
            "contact_name": contact_name,
            "role": role,
            "message": message,
        }).execute()
    except Exception as e:
        logger.error(f"   ❌ History save failed: {e}")


def build_prompt(
    contact_name: str,
    style_examples: list[dict],
    conversation_history: list[dict],
    new_message: str,
) -> list[dict]:
    """
    Build the full prompt for the LLM.
    
    Structure:
        1. System prompt (your persona/rules)
        2. Style examples from RAG (few-shot demonstrations)
        3. Recent conversation history (context)
        4. The new incoming message
    """
    messages = []
    
    # 1. System prompt
    messages.append({
        "role": "system",
        "content": SYSTEM_PROMPT,
    })
    
    # 2. Style examples (RAG results — the key to sounding like you)
    if style_examples:
        examples_text = "Here are examples of how you've replied to similar messages before. " \
                       "Match this EXACT style:\n\n"
        for i, ex in enumerate(style_examples, 1):
            examples_text += f"Example {i}:\n"
            examples_text += f"  They said: {ex['trigger_text']}\n"
            examples_text += f"  You replied: {ex['reply_text']}\n\n"
        
        messages.append({
            "role": "system",
            "content": examples_text,
        })
    
    # 3. Conversation history (recent messages for context)
    if conversation_history:
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["message"],
            })
    
    # 4. The new incoming message
    messages.append({
        "role": "user",
        "content": new_message,
    })
    
    return messages


def call_groq(messages: list[dict]) -> str:
    """Call Groq LLM and return the generated reply text."""
    try:
        response = groq_client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            top_p=0.9,
            stream=False,
        )
        
        reply = response.choices[0].message.content.strip()
        
        # Clean up common LLM artifacts
        # Remove quotes if the LLM wrapped the reply in them
        if reply.startswith('"') and reply.endswith('"'):
            reply = reply[1:-1]
        if reply.startswith("'") and reply.endswith("'"):
            reply = reply[1:-1]
        # Remove "Reply: " prefix if LLM added it
        for prefix in ["Reply:", "Reply :", "Response:", "Message:"]:
            if reply.startswith(prefix):
                reply = reply[len(prefix):].strip()
        
        return reply
    
    except Exception as e:
        logger.error(f"   ❌ Groq API call failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")


# ═══════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════

@app.post("/reply", response_model=MessageResponse)
async def generate_reply(request: MessageRequest):
    """
    Main endpoint — receives a WhatsApp message, returns an AI reply.
    Called by the Android app for every incoming WhatsApp notification.
    """
    start_time = time.time()
    
    logger.info(f"📩 Message from {request.contact_name} ({request.contact_id}): {request.message[:50]}...")
    
    # Simple hardcoded reply for testing (remove Groq dependency temporarily)
    reply = "hnn bhai sab badhiya"
    
    elapsed_ms = int((time.time() - start_time) * 1000)
    logger.info(f"   ✅ Reply ({elapsed_ms}ms): {reply}")
    
    return MessageResponse(
        reply=reply,
        rag_examples_used=0,
        response_time_ms=elapsed_ms,
    )


@app.get("/health")
async def health_check():
    """Health check endpoint for uptime monitoring."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "model": LLM_MODEL,
    }


@app.post("/test-reply")
async def test_reply(request: MessageRequest):
    """Simple test endpoint without Groq/Supabase dependencies."""
    return {
        "reply": "hnn bhai sab badhiya",
        "rag_examples_used": 0,
        "response_time_ms": 50,
    }


@app.get("/stats")
async def get_stats():
    """Get vector database statistics — how many examples per contact."""
    try:
        result = supabase_client.table("chat_embeddings") \
            .select("contact_id") \
            .execute()
        
        contact_counts = {}
        for row in result.data:
            cid = row["contact_id"]
            contact_counts[cid] = contact_counts.get(cid, 0) + 1
        
        return {
            "total_embeddings": sum(contact_counts.values()),
            "contacts": contact_counts,
            "collections": len(contact_counts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/contacts")
async def list_contacts():
    """List all contacts with their message counts in conversation history."""
    try:
        result = supabase_client.table("conversation_history") \
            .select("contact_id, contact_name") \
            .execute()
        
        contacts = {}
        for row in result.data:
            cid = row["contact_id"]
            if cid not in contacts:
                contacts[cid] = {
                    "contact_id": cid,
                    "contact_name": row.get("contact_name", "Unknown"),
                    "message_count": 0,
                }
            contacts[cid]["message_count"] += 1
        
        return {"contacts": list(contacts.values())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/history/{contact_id}")
async def clear_history(contact_id: str):
    """Clear conversation history for a specific contact."""
    try:
        supabase_client.table("conversation_history") \
            .delete() \
            .eq("contact_id", contact_id) \
            .execute()
        
        return {"status": "cleared", "contact_id": contact_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Run with: python main.py ───
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
