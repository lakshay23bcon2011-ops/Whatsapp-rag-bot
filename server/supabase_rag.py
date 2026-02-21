"""
Example: Supabase Integration for WhatsApp RAG Bot Server
This shows how to use Supabase for conversation storage and RAG retrieval
"""

import os
from typing import List, Dict, Optional
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Initialize embedding model (run once, reuse)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')


class SupabaseRAG:
    """Handles all Supabase operations for the RAG bot"""
    
    def __init__(self):
        self.supabase = supabase
        self.embedding_model = embedding_model
    
    async def save_incoming_message(
        self, 
        contact_id: str, 
        contact_name: str, 
        message: str
    ) -> int:
        """
        Save an incoming message from a user
        Returns the message ID
        """
        result = self.supabase.rpc("save_message", {
            "p_contact_id": contact_id,
            "p_contact_name": contact_name,
            "p_role": "user",
            "p_message": message,
            "p_was_bot_reply": False
        }).execute()
        
        return result.data
    
    async def save_bot_reply(
        self,
        contact_id: str,
        contact_name: str,
        reply: str,
        confidence: float,
        rag_sources: Optional[List[int]] = None
    ) -> int:
        """
        Save a bot-generated reply
        """
        result = self.supabase.rpc("save_message", {
            "p_contact_id": contact_id,
            "p_contact_name": contact_name,
            "p_role": "assistant",
            "p_message": reply,
            "p_was_bot_reply": True,
            "p_confidence_score": confidence,
            "p_rag_sources": {"examples": rag_sources} if rag_sources else None
        }).execute()
        
        return result.data
    
    async def get_conversation_history(
        self, 
        contact_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """
        Get recent conversation history for context
        Returns list of messages in chronological order (oldest first)
        """
        result = self.supabase.rpc("get_conversation_context", {
            "p_contact_id": contact_id,
            "message_limit": limit
        }).execute()
        
        # Reverse to get chronological order (function returns newest first)
        messages = list(reversed(result.data)) if result.data else []
        return messages
    
    async def search_similar_replies(
        self,
        contact_id: str,
        query_message: str,
        top_k: int = 8
    ) -> List[Dict]:
        """
        RAG: Find the most similar past replies using vector search
        
        Args:
            contact_id: The contact to search for (+ global fallback)
            query_message: The incoming message to find similar examples for
            top_k: Number of examples to return
            
        Returns:
            List of dicts with 'trigger_text', 'reply_text', 'similarity'
        """
        # Generate embedding for the incoming message
        query_embedding = self.embedding_model.encode(query_message).tolist()
        
        # Search for similar embeddings
        result = self.supabase.rpc("match_chat_embeddings", {
            "query_embedding": query_embedding,
            "match_contact_id": contact_id,
            "match_count": top_k
        }).execute()
        
        return result.data if result.data else []
    
    async def get_contact_info(self, contact_id: str) -> Optional[Dict]:
        """
        Get contact metadata (relationship type, custom instructions, etc.)
        """
        result = self.supabase.table("contacts").select("*").eq(
            "contact_id", contact_id
        ).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return None
    
    async def is_bot_enabled_for_contact(self, contact_id: str) -> bool:
        """
        Check if bot is enabled for this contact
        """
        contact = await self.get_contact_info(contact_id)
        if contact:
            return contact.get("bot_enabled", True)
        return True  # Default: enabled for new contacts
    
    async def update_contact_style(
        self,
        contact_id: str,
        relationship_type: Optional[str] = None,
        conversation_style: Optional[str] = None,
        custom_instructions: Optional[str] = None
    ):
        """
        Update contact metadata for personalized responses
        """
        update_data = {}
        if relationship_type:
            update_data["relationship_type"] = relationship_type
        if conversation_style:
            update_data["conversation_style"] = conversation_style
        if custom_instructions:
            update_data["custom_instructions"] = custom_instructions
        
        if update_data:
            self.supabase.table("contacts").update(update_data).eq(
                "contact_id", contact_id
            ).execute()
    
    async def get_contact_stats(self, contact_id: str) -> Dict:
        """
        Get statistics for a contact (message counts, confidence, etc.)
        """
        result = self.supabase.rpc("get_contact_stats", {
            "p_contact_id": contact_id
        }).execute()
        
        return result.data[0] if result.data else {}
    
    async def ingest_chat_history(
        self,
        contact_id: str,
        conversation_pairs: List[Dict[str, str]]
    ):
        """
        Ingest historical chat data into embeddings table
        
        Args:
            contact_id: The contact ID
            conversation_pairs: List of {"trigger": "...", "reply": "..."}
        """
        embeddings_to_insert = []
        
        for pair in conversation_pairs:
            trigger = pair["trigger"]
            reply = pair["reply"]
            
            # Generate embedding for the reply
            embedding = self.embedding_model.encode(reply).tolist()
            
            embeddings_to_insert.append({
                "contact_id": contact_id,
                "trigger_text": trigger,
                "reply_text": reply,
                "embedding": embedding,
                "relevance_score": 1.0
            })
        
        # Batch insert
        if embeddings_to_insert:
            self.supabase.table("chat_embeddings").insert(
                embeddings_to_insert
            ).execute()
            
        print(f"✅ Ingested {len(embeddings_to_insert)} examples for {contact_id}")


# Example usage in your FastAPI endpoint
async def generate_reply_endpoint(
    contact_id: str,
    contact_name: str,
    incoming_message: str
) -> str:
    """
    Main endpoint logic: Generate a personalized reply using RAG + conversation history
    """
    rag = SupabaseRAG()
    
    # 1. Check if bot is enabled for this contact
    if not await rag.is_bot_enabled_for_contact(contact_id):
        return None  # Don't reply
    
    # 2. Save the incoming message
    await rag.save_incoming_message(contact_id, contact_name, incoming_message)
    
    # 3. Get conversation history for context
    history = await rag.get_conversation_history(contact_id, limit=10)
    
    # 4. RAG: Search for similar past replies
    similar_examples = await rag.search_similar_replies(
        contact_id, 
        incoming_message, 
        top_k=8
    )
    
    # 5. Get contact metadata for personalization
    contact_info = await rag.get_contact_info(contact_id)
    
    # 6. Build the prompt
    system_prompt = build_system_prompt(contact_info)
    rag_examples = build_rag_examples(similar_examples)
    conversation_context = build_conversation_context(history)
    
    full_prompt = f"""
{system_prompt}

STYLE EXAMPLES (how you've replied to similar messages):
{rag_examples}

CONVERSATION HISTORY:
{conversation_context}

NEW MESSAGE: {incoming_message}

YOUR REPLY:"""
    
    # 7. Call Groq/LLM to generate reply (pseudo-code)
    # reply = await call_groq_llm(full_prompt)
    reply = "hnn bhai, let's do it!"  # placeholder
    
    # 8. Save the bot reply
    await rag.save_bot_reply(
        contact_id,
        contact_name,
        reply,
        confidence=0.85,
        rag_sources=[ex["id"] for ex in similar_examples[:3]]  # top 3 sources
    )
    
    return reply


def build_system_prompt(contact_info: Optional[Dict]) -> str:
    """Build personalized system prompt based on contact metadata"""
    base_prompt = """You are acting as the phone's owner. Reply to WhatsApp messages EXACTLY as they would.
CRITICAL RULES:
1. Speak in Hinglish (Hindi + English mix) - casual, warm
2. Use short replies unless the question needs detail
3. Common words: arre, hnn, bhai, yaar, toh, kya, hm, ok
4. NEVER sound like a bot - sound human, natural"""
    
    if contact_info:
        if contact_info.get("relationship_type") == "romantic":
            base_prompt += "\n5. Be warm and affectionate"
        elif contact_info.get("relationship_type") == "work":
            base_prompt += "\n5. Be professional but friendly"
        
        if contact_info.get("custom_instructions"):
            base_prompt += f"\n6. SPECIAL: {contact_info['custom_instructions']}"
    
    return base_prompt


def build_rag_examples(similar_examples: List[Dict]) -> str:
    """Format RAG examples for the prompt"""
    if not similar_examples:
        return "No similar examples found."
    
    examples = []
    for i, ex in enumerate(similar_examples[:5], 1):
        examples.append(f"{i}. Them: \"{ex['trigger_text']}\"\n   You: \"{ex['reply_text']}\"")
    
    return "\n".join(examples)


def build_conversation_context(history: List[Dict]) -> str:
    """Format conversation history for the prompt"""
    if not history:
        return "No previous conversation."
    
    context = []
    for msg in history[-10:]:  # last 10 messages
        role_label = "Them" if msg["role"] == "user" else "You"
        context.append(f"{role_label}: {msg['message']}")
    
    return "\n".join(context)


# Example: Ingestion script
if __name__ == "__main__":
    import asyncio
    
    async def test_ingestion():
        rag = SupabaseRAG()
        
        # Sample data from your WhatsApp export
        conversation_pairs = [
            {"trigger": "hey what's up?", "reply": "nm bhai, just chilling"},
            {"trigger": "wanna hang out?", "reply": "hnn sure! kab?"},
            {"trigger": "you free tomorrow?", "reply": "ya bro, evening me chalega?"},
        ]
        
        await rag.ingest_chat_history("harshit", conversation_pairs)
        
        # Test RAG search
        similar = await rag.search_similar_replies("harshit", "are you free today?")
        print("Similar examples:", similar)
    
    asyncio.run(test_ingestion())
