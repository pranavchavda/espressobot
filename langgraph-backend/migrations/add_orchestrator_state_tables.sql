-- Database schema for optimized orchestrator state persistence
-- Run this migration to add the required tables

-- Workflow state persistence
CREATE TABLE IF NOT EXISTS orchestrator_workflow_states (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255) UNIQUE NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    current_state VARCHAR(50) NOT NULL,
    state_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Agent execution results cache
CREATE TABLE IF NOT EXISTS orchestrator_agent_results (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    node_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(100) NOT NULL,
    task_hash VARCHAR(64) NOT NULL, -- SHA256 of task + context for caching
    result_data JSONB NOT NULL,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '1 hour'
);

-- Conversation memory with compressed context
CREATE TABLE IF NOT EXISTS orchestrator_conversation_memory (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    messages JSONB NOT NULL,
    compressed_context JSONB,
    context_version INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Structured operation logs for observability
CREATE TABLE IF NOT EXISTS orchestrator_operation_logs (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255),
    operation_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL,
    log_level VARCHAR(20) DEFAULT 'INFO',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Error tracking and analysis
CREATE TABLE IF NOT EXISTS orchestrator_error_logs (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255),
    error_type VARCHAR(100) NOT NULL,
    error_message TEXT NOT NULL,
    error_context JSONB,
    retry_count INTEGER DEFAULT 0,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance metrics
CREATE TABLE IF NOT EXISTS orchestrator_performance_metrics (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255),
    operation_name VARCHAR(100) NOT NULL,
    duration_ms INTEGER NOT NULL,
    agent_calls INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_workflow_states_thread_id ON orchestrator_workflow_states(thread_id);
CREATE INDEX IF NOT EXISTS idx_workflow_states_user_id ON orchestrator_workflow_states(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_states_updated_at ON orchestrator_workflow_states(updated_at);

CREATE INDEX IF NOT EXISTS idx_agent_results_thread_id ON orchestrator_agent_results(thread_id);
CREATE INDEX IF NOT EXISTS idx_agent_results_task_hash ON orchestrator_agent_results(task_hash);
CREATE INDEX IF NOT EXISTS idx_agent_results_expires_at ON orchestrator_agent_results(expires_at);

CREATE INDEX IF NOT EXISTS idx_conversation_memory_thread_id ON orchestrator_conversation_memory(thread_id);
CREATE INDEX IF NOT EXISTS idx_conversation_memory_user_id ON orchestrator_conversation_memory(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_memory_updated_at ON orchestrator_conversation_memory(updated_at);

CREATE INDEX IF NOT EXISTS idx_operation_logs_thread_id ON orchestrator_operation_logs(thread_id);
CREATE INDEX IF NOT EXISTS idx_operation_logs_type ON orchestrator_operation_logs(operation_type);
CREATE INDEX IF NOT EXISTS idx_operation_logs_created_at ON orchestrator_operation_logs(created_at);

CREATE INDEX IF NOT EXISTS idx_error_logs_thread_id ON orchestrator_error_logs(thread_id);
CREATE INDEX IF NOT EXISTS idx_error_logs_error_type ON orchestrator_error_logs(error_type);
CREATE INDEX IF NOT EXISTS idx_error_logs_resolved ON orchestrator_error_logs(resolved);

CREATE INDEX IF NOT EXISTS idx_performance_metrics_thread_id ON orchestrator_performance_metrics(thread_id);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_operation ON orchestrator_performance_metrics(operation_name);
CREATE INDEX IF NOT EXISTS idx_performance_metrics_created_at ON orchestrator_performance_metrics(created_at);

-- Cleanup procedures for maintenance
CREATE OR REPLACE FUNCTION cleanup_expired_agent_results()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM orchestrator_agent_results 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    INSERT INTO orchestrator_operation_logs (operation_type, event_data)
    VALUES ('cleanup', json_build_object('deleted_agent_results', deleted_count));
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION cleanup_old_logs(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM orchestrator_operation_logs 
    WHERE created_at < NOW() - INTERVAL '1 day' * days_to_keep;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    INSERT INTO orchestrator_operation_logs (operation_type, event_data)
    VALUES ('cleanup', json_build_object('deleted_old_logs', deleted_count, 'days_kept', days_to_keep));
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Performance monitoring view
CREATE OR REPLACE VIEW orchestrator_performance_summary AS
SELECT 
    operation_name,
    COUNT(*) as total_operations,
    AVG(duration_ms) as avg_duration_ms,
    MIN(duration_ms) as min_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY duration_ms) as median_duration_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration_ms,
    AVG(agent_calls) as avg_agent_calls,
    AVG(tokens_used) as avg_tokens_used,
    COUNT(*) FILTER (WHERE success = true) * 100.0 / COUNT(*) as success_rate_percent,
    DATE_TRUNC('hour', created_at) as hour_bucket
FROM orchestrator_performance_metrics 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY operation_name, DATE_TRUNC('hour', created_at)
ORDER BY hour_bucket DESC, operation_name;

-- Error analysis view
CREATE OR REPLACE VIEW orchestrator_error_summary AS
SELECT 
    error_type,
    COUNT(*) as error_count,
    COUNT(*) FILTER (WHERE resolved = true) as resolved_count,
    COUNT(*) FILTER (WHERE retry_count > 0) as retried_count,
    AVG(retry_count) as avg_retry_count,
    DATE_TRUNC('hour', created_at) as hour_bucket
FROM orchestrator_error_logs 
WHERE created_at >= NOW() - INTERVAL '24 hours'
GROUP BY error_type, DATE_TRUNC('hour', created_at)
ORDER BY hour_bucket DESC, error_count DESC;