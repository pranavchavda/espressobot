-- Create background_tasks table for async task tracking
CREATE TABLE IF NOT EXISTS background_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id TEXT UNIQUE NOT NULL,
    thread_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed, cancelled
    message TEXT NOT NULL DEFAULT '',
    response TEXT DEFAULT '',
    progress FLOAT DEFAULT 0.0, -- 0.0 to 1.0
    agent_results JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_background_tasks_task_id ON background_tasks(task_id);
CREATE INDEX IF NOT EXISTS idx_background_tasks_thread_id ON background_tasks(thread_id);
CREATE INDEX IF NOT EXISTS idx_background_tasks_user_id ON background_tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_background_tasks_status ON background_tasks(status);
CREATE INDEX IF NOT EXISTS idx_background_tasks_created_at ON background_tasks(created_at);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_background_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS trigger_update_background_tasks_updated_at ON background_tasks;
CREATE TRIGGER trigger_update_background_tasks_updated_at
    BEFORE UPDATE ON background_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_background_tasks_updated_at();

-- Create cleanup function for old completed tasks
CREATE OR REPLACE FUNCTION cleanup_old_background_tasks(days_to_keep INTEGER DEFAULT 7)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM background_tasks 
    WHERE status IN ('completed', 'failed', 'cancelled')
    AND created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;