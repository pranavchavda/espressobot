-- PostgreSQL schema for memory management with pgvector
-- Modified for langgraph-backend (fixed vector dimensions)

-- Memories table for user-specific memories with embeddings
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1536),  -- Reduced to supported dimensions
    metadata JSONB DEFAULT '{}',
    category VARCHAR(100),
    importance_score FLOAT DEFAULT 1.0,
    confidence_score FLOAT DEFAULT 1.0,
    usefulness_score FLOAT DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_ephemeral BOOLEAN DEFAULT false,
    status VARCHAR(20) DEFAULT 'active',
    extraction_method VARCHAR(50) DEFAULT 'gpt',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries (fixed vector dimensions)
CREATE INDEX IF NOT EXISTS memories_embedding_idx ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS memories_user_idx ON memories(user_id);
CREATE INDEX IF NOT EXISTS memories_category_idx ON memories(category);
CREATE INDEX IF NOT EXISTS memories_importance_idx ON memories(importance_score DESC);
CREATE INDEX IF NOT EXISTS memories_access_idx ON memories(last_accessed_at DESC);
CREATE INDEX IF NOT EXISTS memories_status_idx ON memories(status);

-- Prompt fragments for agent-specific context
CREATE TABLE IF NOT EXISTS prompt_fragments (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 0,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    embedding vector(1536),  -- Reduced to supported dimensions
    agent_type VARCHAR(100),
    context_tier VARCHAR(20) DEFAULT 'standard' CHECK (context_tier IN ('core', 'standard', 'full')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for prompt fragments (fixed vector dimensions)
CREATE INDEX IF NOT EXISTS prompt_fragments_embedding_idx ON prompt_fragments USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX IF NOT EXISTS prompt_fragments_category_idx ON prompt_fragments(category);
CREATE INDEX IF NOT EXISTS prompt_fragments_agent_idx ON prompt_fragments(agent_type);
CREATE INDEX IF NOT EXISTS prompt_fragments_tier_idx ON prompt_fragments(context_tier);
CREATE INDEX IF NOT EXISTS prompt_fragments_priority_idx ON prompt_fragments(priority DESC);

-- Memory deduplication tracking
CREATE TABLE IF NOT EXISTS memory_duplicates (
    id SERIAL PRIMARY KEY,
    original_id INTEGER REFERENCES memories(id) ON DELETE CASCADE,
    duplicate_hash VARCHAR(64) NOT NULL,
    similarity_score FLOAT,
    dedup_type VARCHAR(20) CHECK (dedup_type IN ('exact', 'fuzzy', 'key_phrase', 'semantic')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS memory_duplicates_hash_idx ON memory_duplicates(duplicate_hash);
CREATE INDEX IF NOT EXISTS memory_duplicates_original_idx ON memory_duplicates(original_id);

-- Memory usage analytics
CREATE TABLE IF NOT EXISTS memory_analytics (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    query_text TEXT,
    results_count INTEGER,
    response_time_ms INTEGER,
    context_tier VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS memory_analytics_user_idx ON memory_analytics(user_id);
CREATE INDEX IF NOT EXISTS memory_analytics_time_idx ON memory_analytics(created_at DESC);

-- Agent configurations (if not exists)
CREATE TABLE IF NOT EXISTS agents (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200),
    description TEXT,
    system_prompt TEXT,
    model_provider VARCHAR(50) DEFAULT 'openai',
    model_name VARCHAR(100) DEFAULT 'gpt-4',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table for chat history
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    title VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT false
);

-- Messages table for conversation messages
CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS messages_conversation_idx ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS messages_created_idx ON messages(created_at DESC);
CREATE INDEX IF NOT EXISTS conversations_user_idx ON conversations(user_id);
CREATE INDEX IF NOT EXISTS conversations_updated_idx ON conversations(updated_at DESC);

-- Trigger to update updated_at on memories
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_prompt_fragments_updated_at BEFORE UPDATE ON prompt_fragments
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Memory decay and archival functions
CREATE OR REPLACE FUNCTION calculate_effective_importance(
    base_importance FLOAT,
    confidence_score FLOAT,
    usefulness_score FLOAT,
    access_count INTEGER,
    days_since_created INTEGER,
    days_since_accessed INTEGER
) RETURNS FLOAT AS $$
BEGIN
    -- Base importance weighted by confidence and usefulness
    RETURN (base_importance * 0.4) + 
           (confidence_score * 0.3) + 
           (usefulness_score * 0.2) + 
           (LEAST(access_count::FLOAT / 10.0, 1.0) * 0.1) -
           (days_since_accessed::FLOAT / 365.0 * 0.1);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION archive_old_memories() RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER := 0;
BEGIN
    UPDATE memories 
    SET status = 'archived'
    WHERE status = 'active'
    AND (
        -- Very old memories with low importance
        (created_at < NOW() - INTERVAL '1 year' AND importance_score < 0.5)
        OR
        -- Ephemeral memories older than 30 days
        (is_ephemeral = true AND created_at < NOW() - INTERVAL '30 days')
        OR
        -- Unused memories older than 6 months
        (access_count = 0 AND created_at < NOW() - INTERVAL '6 months')
    );
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;