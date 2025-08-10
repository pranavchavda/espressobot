-- Migration: Add memory tracking and decay columns
-- Date: 2025-08-09
-- Purpose: Support memory relevance decay and usage tracking

-- Add tracking columns to memories table
ALTER TABLE memories ADD COLUMN IF NOT EXISTS access_count INTEGER DEFAULT 0;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS last_accessed_at TIMESTAMP;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS usefulness_score FLOAT DEFAULT 0.5;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS decay_rate FLOAT DEFAULT 0.01;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS is_ephemeral BOOLEAN DEFAULT FALSE;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 0.5;
ALTER TABLE memories ADD COLUMN IF NOT EXISTS verification_status VARCHAR(20) DEFAULT 'unverified';
ALTER TABLE memories ADD COLUMN IF NOT EXISTS source_conversation_id VARCHAR(255);
ALTER TABLE memories ADD COLUMN IF NOT EXISTS used_in_conversations TEXT; -- JSON array
ALTER TABLE memories ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active'; -- active, archived, deleted

-- Add category and importance columns if they don't exist (stored in meta_data currently)
ALTER TABLE memories ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE memories ADD COLUMN IF NOT EXISTS importance_score FLOAT DEFAULT 0.5;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_memories_user_last_accessed 
    ON memories (user_id, last_accessed_at DESC) 
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_memories_user_importance 
    ON memories (user_id, importance_score DESC) 
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_memories_user_category 
    ON memories (user_id, category) 
    WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_memories_user_access_count 
    ON memories (user_id, access_count DESC) 
    WHERE status = 'active';

-- Create a function to calculate effective importance
CREATE OR REPLACE FUNCTION calculate_effective_importance(
    p_importance_score FLOAT,
    p_created_at TIMESTAMP,
    p_decay_rate FLOAT,
    p_access_count INTEGER,
    p_usefulness_score FLOAT
) RETURNS FLOAT AS $$
DECLARE
    days_old INTEGER;
    time_decay FLOAT;
    usage_boost FLOAT;
    usefulness_mult FLOAT;
BEGIN
    -- Calculate days old
    days_old := EXTRACT(EPOCH FROM (NOW() - p_created_at)) / 86400;
    
    -- Time decay factor
    time_decay := EXP(-p_decay_rate * days_old);
    
    -- Usage boost factor (cap at 10 accesses)
    usage_boost := 1 + (0.1 * LEAST(p_access_count, 10));
    
    -- Usefulness multiplier
    usefulness_mult := 0.5 + p_usefulness_score;
    
    -- Return combined score
    RETURN p_importance_score * time_decay * usage_boost * usefulness_mult;
END;
$$ LANGUAGE plpgsql;

-- Create a view for active memories with effective importance
CREATE OR REPLACE VIEW active_memories_with_importance AS
SELECT 
    *,
    calculate_effective_importance(
        importance_score,
        created_at,
        decay_rate,
        access_count,
        usefulness_score
    ) AS effective_importance
FROM memories
WHERE status = 'active';

-- Update function to increment access count
CREATE OR REPLACE FUNCTION increment_memory_access(
    p_memory_id VARCHAR,
    p_conversation_id VARCHAR DEFAULT NULL
) RETURNS void AS $$
BEGIN
    UPDATE memories 
    SET 
        access_count = access_count + 1,
        last_accessed_at = NOW(),
        used_in_conversations = CASE 
            WHEN p_conversation_id IS NOT NULL AND used_in_conversations IS NULL THEN 
                json_build_array(p_conversation_id)::text
            WHEN p_conversation_id IS NOT NULL THEN 
                (used_in_conversations::jsonb || to_jsonb(p_conversation_id))::text
            ELSE 
                used_in_conversations
        END
    WHERE id = p_memory_id;
END;
$$ LANGUAGE plpgsql;

-- Create a scheduled function to archive old memories (to be called by cron job)
CREATE OR REPLACE FUNCTION archive_old_memories() RETURNS INTEGER AS $$
DECLARE
    archived_count INTEGER;
BEGIN
    -- Archive memories with very low effective importance
    WITH to_archive AS (
        SELECT id 
        FROM active_memories_with_importance
        WHERE effective_importance < 0.1
           OR (last_accessed_at IS NULL AND created_at < NOW() - INTERVAL '30 days')
           OR (last_accessed_at < NOW() - INTERVAL '60 days')
    )
    UPDATE memories 
    SET status = 'archived'
    WHERE id IN (SELECT id FROM to_archive)
    AND status = 'active';
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON COLUMN memories.access_count IS 'Number of times this memory has been accessed';
COMMENT ON COLUMN memories.last_accessed_at IS 'Timestamp of last access';
COMMENT ON COLUMN memories.usefulness_score IS 'Score indicating how useful this memory has been (0-1)';
COMMENT ON COLUMN memories.decay_rate IS 'Rate at which importance decays over time';
COMMENT ON COLUMN memories.is_ephemeral IS 'Whether this is a short-term/task-specific memory';
COMMENT ON COLUMN memories.confidence_score IS 'Extraction confidence (0-1)';
COMMENT ON COLUMN memories.verification_status IS 'Whether memory has been verified: unverified, verified, rejected';
COMMENT ON COLUMN memories.source_conversation_id IS 'ID of conversation where memory was extracted';
COMMENT ON COLUMN memories.used_in_conversations IS 'JSON array of conversation IDs where memory was used';
COMMENT ON COLUMN memories.status IS 'Memory status: active, archived, deleted';

-- Migration complete message
DO $$
BEGIN
    RAISE NOTICE 'Memory tracking columns migration completed successfully';
END $$;