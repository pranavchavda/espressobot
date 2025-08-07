-- PostgreSQL schema for memory management with pgvector

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Memories table for user-specific memories with embeddings
CREATE TABLE IF NOT EXISTS memories (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(3072),  -- text-embedding-3-large dimensions
    metadata JSONB DEFAULT '{}',
    category VARCHAR(100),
    importance_score FLOAT DEFAULT 1.0,
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS memories_embedding_idx ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS memories_user_idx ON memories(user_id);
CREATE INDEX IF NOT EXISTS memories_category_idx ON memories(category);
CREATE INDEX IF NOT EXISTS memories_importance_idx ON memories(importance_score DESC);
CREATE INDEX IF NOT EXISTS memories_access_idx ON memories(last_accessed_at DESC);

-- Prompt fragments for agent-specific context
CREATE TABLE IF NOT EXISTS prompt_fragments (
    id SERIAL PRIMARY KEY,
    category VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 0,
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    embedding vector(3072),
    agent_type VARCHAR(100),
    context_tier VARCHAR(20) DEFAULT 'standard' CHECK (context_tier IN ('core', 'standard', 'full')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for prompt fragments
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