# 🚀 Supabase Setup Guide for WhatsApp RAG Bot

This guide will walk you through setting up Supabase as your database backend for storing conversation history and vector embeddings.

## 📋 Prerequisites

- A Supabase account (Sign up at [supabase.com](https://supabase.com) - FREE tier available)
- Your Supabase project created

## 🔧 Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign in
2. Click **"New Project"**
3. Fill in:
   - **Name**: `whatsapp-rag-bot` (or your choice)
   - **Database Password**: Choose a strong password (save it!)
   - **Region**: Choose closest to your location
4. Click **"Create new project"** (takes ~2 minutes)

## 📊 Step 2: Run the Database Schema

1. In your Supabase dashboard, navigate to **SQL Editor** (left sidebar)
2. Click **"New Query"**
3. Copy the entire contents of [`schema.sql`](schema.sql)
4. Paste it into the SQL Editor
5. Click **"Run"** (bottom right) or press `Ctrl+Enter`
6. You should see success messages like:
   ```
   ✅ Schema created successfully!
   ```

## 🔍 Step 3: Verify Tables Were Created

1. Go to **Table Editor** (left sidebar)
2. You should see 3 new tables:
   - `contacts` - Stores contact metadata
   - `conversation_history` - All past messages
   - `chat_embeddings` - Vector embeddings for RAG

## 🔑 Step 4: Get Your Supabase Credentials

You need these for your server to connect to Supabase:

1. Go to **Project Settings** → **API**
2. Copy these values:
   - **Project URL** (looks like: `https://xxxxx.supabase.co`)
   - **Project API Key** (use the `anon/public` key for now)
   - **Service Role Key** (for server-side operations)

3. Create a `.env` file in your `server/` directory:
   ```env
   # Supabase credentials
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   
   # Groq API for LLM
   GROQ_API_KEY=gsk_your_key_here
   ```

## 📦 Step 5: Install Python Dependencies

Update your `requirements.txt` to include Supabase client:

```bash
cd server
pip install supabase sentence-transformers
```

Add to `requirements.txt`:
```
supabase>=2.0.0
sentence-transformers>=2.2.0
```

## 🧪 Step 6: Test the Connection

Create a test script `server/test_supabase.py`:

```python
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Test 1: Insert a test contact
print("Testing contacts table...")
result = supabase.table("contacts").insert({
    "contact_id": "test_user_123",
    "contact_name": "Test User",
    "relationship_type": "friend"
}).execute()
print(f"✅ Contact inserted: {result.data}")

# Test 2: Insert a test message
print("\nTesting save_message function...")
result = supabase.rpc("save_message", {
    "p_contact_id": "test_user_123",
    "p_contact_name": "Test User",
    "p_role": "user",
    "p_message": "Hello, this is a test message!",
    "p_was_bot_reply": False
}).execute()
print(f"✅ Message saved with ID: {result.data}")

# Test 3: Fetch conversation history
print("\nTesting get_conversation_context function...")
result = supabase.rpc("get_conversation_context", {
    "p_contact_id": "test_user_123",
    "message_limit": 5
}).execute()
print(f"✅ Conversation history: {result.data}")

# Test 4: Get contact stats
print("\nTesting get_contact_stats function...")
result = supabase.rpc("get_contact_stats", {
    "p_contact_id": "test_user_123"
}).execute()
print(f"✅ Contact stats: {result.data}")

print("\n🎉 All tests passed! Supabase is configured correctly.")
```

Run the test:
```bash
python test_supabase.py
```

## 📊 Database Schema Overview

### **1. `contacts` Table**
Stores metadata about each person you chat with:
- `contact_id`: Unique identifier (phone number)
- `contact_name`: Display name
- `relationship_type`: "friend", "family", "work", etc.
- `conversation_style`: "casual", "formal", "playful"
- `bot_enabled`: Toggle bot on/off for this person
- `custom_instructions`: Special instructions for this contact

### **2. `conversation_history` Table**
Stores ALL messages (both incoming and bot replies):
- `contact_id`: Who sent/received the message
- `role`: "user" (them) or "assistant" (you/bot)
- `message`: The actual text
- `was_bot_reply`: TRUE if bot sent it
- `confidence_score`: How confident the bot was (0-1)
- `rag_sources`: Which past conversations influenced this reply

### **3. `chat_embeddings` Table**
Stores vector embeddings of your past replies for RAG:
- `contact_id`: Who this conversation style is for
- `trigger_text`: What they said
- `reply_text`: How YOU replied
- `embedding`: 384-dimensional vector for semantic search
- `relevance_score`: Weight for this example

## 🔧 Key Functions to Use in Your Server

### Save a New Message
```python
# When a new message arrives
supabase.rpc("save_message", {
    "p_contact_id": contact_id,
    "p_contact_name": contact_name,
    "p_role": "user",
    "p_message": incoming_message
}).execute()

# When bot replies
supabase.rpc("save_message", {
    "p_contact_id": contact_id,
    "p_contact_name": contact_name,
    "p_role": "assistant",
    "p_message": bot_reply,
    "p_was_bot_reply": True,
    "p_confidence_score": 0.85,
    "p_rag_sources": {"examples": [1, 2, 3]}
}).execute()
```

### Get Conversation Context
```python
# Get last 10 messages for context
history = supabase.rpc("get_conversation_context", {
    "p_contact_id": contact_id,
    "message_limit": 10
}).execute()

messages = history.data
```

### RAG: Find Similar Past Replies
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')
query_embedding = model.encode(incoming_message).tolist()

# Find 8 most similar past replies
similar = supabase.rpc("match_chat_embeddings", {
    "query_embedding": query_embedding,
    "match_contact_id": contact_id,
    "match_count": 8
}).execute()

examples = similar.data
```

## 📈 Dashboard Views

Go to **SQL Editor** and run these queries to monitor your bot:

### Most Active Conversations
```sql
SELECT * FROM active_conversations LIMIT 10;
```

### Bot Reply Stats
```sql
SELECT 
    contact_name,
    COUNT(*) FILTER (WHERE was_bot_reply = TRUE) as bot_replies,
    AVG(confidence_score) as avg_confidence
FROM conversation_history
GROUP BY contact_name
ORDER BY bot_replies DESC
LIMIT 10;
```

### Recent Messages
```sql
SELECT 
    contact_name,
    role,
    message,
    created_at
FROM conversation_history
ORDER BY created_at DESC
LIMIT 20;
```

## 🎯 Next Steps

1. ✅ Schema is set up in Supabase
2. ⏭️ **Next**: Ingest your WhatsApp chat history into `chat_embeddings` table
3. ⏭️ **Then**: Update your server code to use Supabase instead of local SQLite/ChromaDB
4. ⏭️ **Finally**: Test end-to-end with the Android app

## 🔒 Security Best Practices

1. **Never expose Service Role Key** in client apps (Android) - only use on server
2. Enable **Row Level Security (RLS)** if multiple users will use this
3. Use **environment variables** for all secrets
4. Enable **HTTPS** for production server
5. Consider enabling **Supabase Vault** for storing API keys

## 📞 Support

If you encounter errors:
1. Check Supabase logs: **Database** → **Logs**
2. Verify extension is enabled: Run `CREATE EXTENSION IF NOT EXISTS vector;`
3. Check table permissions in **Table Editor**
4. Review function definitions in **Database** → **Functions**

---

**Next**: [Ingestion Guide](../scripts/README.md) - Learn how to import your WhatsApp chats into Supabase
