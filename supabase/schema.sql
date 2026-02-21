-- ===========================================
-- WhatsApp RAG Bot - Supabase Database Schema
-- Enhanced Version with Full Context Tracking
-- ===========================================
-- Run this in: Supabase Dashboard → SQL Editor → New Query → Paste → Run
-- NOTE: This script is idempotent - safe to run multiple times

-- Step 1: Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Step 2: Create the contacts table
-- Stores metadata about each contact for personalized responses
CREATE TABLE IF NOT EXISTS contacts (
    id BIGSERIAL PRIMARY KEY,
    contact_id TEXT UNIQUE NOT NULL,          -- phone number or unique ID
    contact_name TEXT NOT NULL,               -- display name
    relationship_type TEXT,                   -- e.g., "friend", "family", "work", "romantic"
    conversation_style TEXT,                  -- e.g., "casual", "formal", "playful"
    first_message_at TIMESTAMPTZ DEFAULT NOW(),
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    total_messages INT DEFAULT 0,
    bot_enabled BOOLEAN DEFAULT TRUE,         -- toggle bot for this contact
    custom_instructions TEXT,                 -- optional: specific instructions for this contact
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 3: Create the conversation history table (replaces SQLite)
-- Stores ALL messages for full context in each conversation
CREATE TABLE IF NOT EXISTS conversation_history (
    id BIGSERIAL PRIMARY KEY,
    contact_id TEXT NOT NULL,                 -- references contacts.contact_id
    contact_name TEXT,                        -- display name (denormalized for speed)
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),  -- 'user' (them) or 'assistant' (you/bot)
    message TEXT NOT NULL,                    -- the message text
    message_type TEXT DEFAULT 'text',         -- 'text', 'image', 'video', etc.
    was_bot_reply BOOLEAN DEFAULT FALSE,      -- true if this was sent by bot
    confidence_score FLOAT,                   -- how confident the bot was (0-1)
    rag_sources JSONB,                        -- which past conversations influenced this reply
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    FOREIGN KEY (contact_id) REFERENCES contacts(contact_id) ON DELETE CASCADE
);

-- Step 4: Create the embeddings table (replaces ChromaDB)
-- Stores your chat reply examples as vectors for semantic search
CREATE TABLE IF NOT EXISTS chat_embeddings (
    id BIGSERIAL PRIMARY KEY,
    contact_id TEXT NOT NULL,                 -- e.g., "harshit", "priya", or "global"
    trigger_text TEXT NOT NULL,               -- what the other person said
    reply_text TEXT NOT NULL,                 -- how YOU replied
    embedding VECTOR(384),                    -- 384-dim vector from all-MiniLM-L6-v2
    conversation_context TEXT,                -- optional: context around this exchange
    message_timestamp TIMESTAMPTZ,            -- when this original exchange happened
    relevance_score FLOAT DEFAULT 1.0,        -- weight for this example (can decay over time)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Step 5: Create indexes for fast lookups
-- Index for vector similarity search (cosine distance)
CREATE INDEX IF NOT EXISTS idx_chat_embeddings_vector 
    ON chat_embeddings 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Index for filtering embeddings by contact
CREATE INDEX IF NOT EXISTS idx_chat_embeddings_contact 
    ON chat_embeddings (contact_id);

-- Index for fetching recent conversation history
CREATE INDEX IF NOT EXISTS idx_conversation_history_lookup 
    ON conversation_history (contact_id, created_at DESC);

-- Index for contact lookups
CREATE INDEX IF NOT EXISTS idx_contacts_contact_id 
    ON contacts (contact_id);

-- Index for finding active contacts
CREATE INDEX IF NOT EXISTS idx_contacts_last_message 
    ON contacts (last_message_at DESC) WHERE bot_enabled = TRUE;

-- Step 6: Drop existing functions if they exist (to avoid conflicts)
DROP FUNCTION IF EXISTS match_chat_embeddings(vector, text, integer);
DROP FUNCTION IF EXISTS get_conversation_context(text, integer);
DROP FUNCTION IF EXISTS save_message(text, text, text, text, boolean, float, jsonb);
DROP FUNCTION IF EXISTS get_contact_stats(text);
DROP FUNCTION IF EXISTS update_contact_timestamp();

-- Step 7: Create the similarity search function
-- This is called by the server to find your most relevant past replies
CREATE OR REPLACE FUNCTION match_chat_embeddings(
    query_embedding VECTOR(384),
    match_contact_id TEXT,
    match_count INT DEFAULT 8
)
RETURNS TABLE (
    trigger_text TEXT, 
    reply_text TEXT,
    conversation_context TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ce.trigger_text, 
        ce.reply_text,
        ce.conversation_context,
        1 - (ce.embedding <=> query_embedding) AS similarity
    FROM chat_embeddings ce
    WHERE (ce.contact_id = match_contact_id OR ce.contact_id = 'global')
      AND ce.relevance_score > 0.3  -- filter out low-quality examples
    ORDER BY ce.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Step 8: Create function to get conversation context
-- Returns recent messages for a contact to maintain conversation flow
CREATE OR REPLACE FUNCTION get_conversation_context(
    p_contact_id TEXT,
    message_limit INT DEFAULT 10
)
RETURNS TABLE (
    role TEXT,
    message TEXT,
    created_at TIMESTAMPTZ
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ch.role,
        ch.message,
        ch.created_at
    FROM conversation_history ch
    WHERE ch.contact_id = p_contact_id
    ORDER BY ch.created_at DESC
    LIMIT message_limit;
END;
$$;

-- Step 9: Create function to save a new message
-- This automatically updates contact metadata and stores the message
CREATE OR REPLACE FUNCTION save_message(
    p_contact_id TEXT,
    p_contact_name TEXT,
    p_role TEXT,
    p_message TEXT,
    p_was_bot_reply BOOLEAN DEFAULT FALSE,
    p_confidence_score FLOAT DEFAULT NULL,
    p_rag_sources JSONB DEFAULT NULL
)
RETURNS BIGINT
LANGUAGE plpgsql AS $$
DECLARE
    message_id BIGINT;
BEGIN
    -- Insert or update contact
    INSERT INTO contacts (contact_id, contact_name, first_message_at, last_message_at, total_messages)
    VALUES (p_contact_id, p_contact_name, NOW(), NOW(), 1)
    ON CONFLICT (contact_id) 
    DO UPDATE SET
        contact_name = p_contact_name,
        last_message_at = NOW(),
        total_messages = contacts.total_messages + 1,
        updated_at = NOW();
    
    -- Insert message
    INSERT INTO conversation_history (
        contact_id, 
        contact_name, 
        role, 
        message, 
        was_bot_reply, 
        confidence_score,
        rag_sources
    )
    VALUES (
        p_contact_id, 
        p_contact_name, 
        p_role, 
        p_message, 
        p_was_bot_reply,
        p_confidence_score,
        p_rag_sources
    )
    RETURNING id INTO message_id;
    
    RETURN message_id;
END;
$$;

-- Step 10: Create function to get contact statistics
CREATE OR REPLACE FUNCTION get_contact_stats(p_contact_id TEXT)
RETURNS TABLE (
    total_messages BIGINT,
    user_messages BIGINT,
    bot_messages BIGINT,
    embedding_examples INT,
    avg_confidence FLOAT,
    last_interaction TIMESTAMPTZ
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_messages,
        COUNT(*) FILTER (WHERE role = 'user')::BIGINT as user_messages,
        COUNT(*) FILTER (WHERE role = 'assistant')::BIGINT as bot_messages,
        (SELECT COUNT(*)::INT FROM chat_embeddings WHERE contact_id = p_contact_id) as embedding_examples,
        AVG(confidence_score) FILTER (WHERE was_bot_reply = TRUE) as avg_confidence,
        MAX(created_at) as last_interaction
    FROM conversation_history
    WHERE contact_id = p_contact_id;
END;
$$;

-- Step 11: Create trigger to update contact's updated_at timestamp
DROP TRIGGER IF EXISTS trigger_update_contact_timestamp ON conversation_history;

CREATE OR REPLACE FUNCTION update_contact_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE contacts 
    SET updated_at = NOW() 
    WHERE contact_id = NEW.contact_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_contact_timestamp
    AFTER INSERT ON conversation_history
    FOR EACH ROW
    EXECUTE FUNCTION update_contact_timestamp();

-- Step 12: Create Row Level Security (RLS) policies (optional, for multi-user)
-- Uncomment these if you want to restrict access per user
-- ALTER TABLE contacts ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE chat_embeddings ENABLE ROW LEVEL SECURITY;

-- Step 13: Create helpful views
DROP VIEW IF EXISTS active_conversations;

CREATE OR REPLACE VIEW active_conversations AS
SELECT 
    c.contact_id,
    c.contact_name,
    c.relationship_type,
    c.last_message_at,
    c.total_messages,
    (SELECT COUNT(*) FROM chat_embeddings WHERE contact_id = c.contact_id) as embedding_count,
    (SELECT message FROM conversation_history 
     WHERE contact_id = c.contact_id 
     ORDER BY created_at DESC LIMIT 1) as last_message
FROM contacts c
WHERE c.bot_enabled = TRUE
ORDER BY c.last_message_at DESC;

-- Step 14: Verify everything was created successfully
-- You should see the tables in Table Editor after running this
SELECT 'Schema created successfully! ✅' AS status;
SELECT 'Tables created:' AS info;
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('contacts', 'conversation_history', 'chat_embeddings');

SELECT 'Functions created:' AS info;
SELECT routine_name FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name LIKE '%chat%' OR routine_name LIKE '%contact%' OR routine_name LIKE '%message%';
