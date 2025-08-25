#!/usr/bin/env python3
"""
Database migration script for optimized orchestrator
Safely applies the database schema changes needed for the optimized orchestrator
"""
import asyncio
import asyncpg
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection parameters
def get_db_config():
    """Get database configuration, ensuring all required env vars are present"""
    host = os.getenv('DB_HOST')
    port = int(os.getenv('DB_PORT', '5432'))  # Safe default for PostgreSQL
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')
    database = os.getenv('DB_NAME')
    
    # Check for DATABASE_URL first
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # Parse DATABASE_URL if provided
        import urllib.parse
        parsed = urllib.parse.urlparse(database_url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'user': parsed.username,
            'password': parsed.password,
            'database': parsed.path[1:]  # Remove leading '/'
        }
    
    # Require all essential database connection parameters
    if not all([host, user, password, database]):
        missing = [name for name, value in [("DB_HOST", host), ("DB_USER", user), ("DB_PASSWORD", password), ("DB_NAME", database)] if not value]
        raise ValueError(f"Missing required database environment variables: {', '.join(missing)}")
    
    return {
        'host': host,
        'port': port,
        'user': user,
        'password': password,
        'database': database
    }

MIGRATION_SQL = """
-- Database schema for optimized orchestrator state persistence
-- This migration is idempotent - safe to run multiple times

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

-- Indexes for performance (only create if they don't exist)
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
"""

CLEANUP_FUNCTIONS_SQL = """
-- Cleanup functions for maintenance
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
"""

VIEWS_SQL = """
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
"""

async def check_database_connection():
    """Test database connection"""
    try:
        db_config = get_db_config()
        conn = await asyncpg.connect(**db_config)
        await conn.fetchval("SELECT 1")
        await conn.close()
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

async def run_migration():
    """Run the database migration"""
    logger.info("🚀 Starting orchestrator database migration...")
    
    # Check connection first
    if not await check_database_connection():
        logger.error("Cannot connect to database. Please check your configuration.")
        return False
    
    try:
        db_config = get_db_config()
        conn = await asyncpg.connect(**db_config)
        
        # Start transaction
        async with conn.transaction():
            logger.info("📊 Creating tables and indexes...")
            await conn.execute(MIGRATION_SQL)
            
            logger.info("🔧 Creating maintenance functions...")
            await conn.execute(CLEANUP_FUNCTIONS_SQL)
            
            logger.info("📈 Creating monitoring views...")
            await conn.execute(VIEWS_SQL)
            
            # Log the migration
            await conn.execute("""
                INSERT INTO orchestrator_operation_logs (operation_type, event_data)
                VALUES ('migration', json_build_object(
                    'migration_name', 'optimized_orchestrator_schema',
                    'version', '1.0.0',
                    'description', 'Initial schema for optimized orchestrator'
                ))
            """)
        
        await conn.close()
        logger.info("✅ Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

async def verify_migration():
    """Verify that the migration was successful"""
    logger.info("🔍 Verifying migration...")
    
    try:
        db_config = get_db_config()
        conn = await asyncpg.connect(**db_config)
        
        # Check that all tables exist
        tables_to_check = [
            'orchestrator_workflow_states',
            'orchestrator_agent_results', 
            'orchestrator_conversation_memory',
            'orchestrator_operation_logs',
            'orchestrator_error_logs',
            'orchestrator_performance_metrics'
        ]
        
        for table in tables_to_check:
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = $1
                )
            """, table)
            
            if exists:
                logger.info(f"✅ Table {table} exists")
            else:
                logger.error(f"❌ Table {table} missing")
                return False
        
        # Check that views exist
        views_to_check = ['orchestrator_performance_summary', 'orchestrator_error_summary']
        for view in views_to_check:
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.views 
                    WHERE table_name = $1
                )
            """, view)
            
            if exists:
                logger.info(f"✅ View {view} exists")
            else:
                logger.error(f"❌ View {view} missing")
                return False
        
        # Test insert into operation logs
        await conn.execute("""
            INSERT INTO orchestrator_operation_logs (operation_type, event_data)
            VALUES ('migration_verification', json_build_object('status', 'success'))
        """)
        
        await conn.close()
        logger.info("✅ Migration verification successful!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration verification failed: {e}")
        return False

async def show_migration_summary():
    """Show summary of what was created"""
    logger.info("📋 Migration Summary:")
    logger.info("   Tables created:")
    logger.info("   • orchestrator_workflow_states - Persistent state management")
    logger.info("   • orchestrator_agent_results - Intelligent result caching") 
    logger.info("   • orchestrator_conversation_memory - Enhanced memory storage")
    logger.info("   • orchestrator_operation_logs - Structured observability")
    logger.info("   • orchestrator_error_logs - Error pattern analysis")
    logger.info("   • orchestrator_performance_metrics - Performance monitoring")
    logger.info("")
    logger.info("   Views created:")
    logger.info("   • orchestrator_performance_summary - Performance analytics")
    logger.info("   • orchestrator_error_summary - Error analysis")
    logger.info("")
    logger.info("   Functions created:")
    logger.info("   • cleanup_expired_agent_results() - Automatic cleanup")
    logger.info("   • cleanup_old_logs(days) - Log retention management")

async def main():
    """Main migration function"""
    logger.info("🎯 Optimized Orchestrator Database Migration")
    logger.info("=" * 50)
    
    # Show configuration
    db_config = get_db_config()
    logger.info(f"Database: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    logger.info(f"User: {db_config['user']}")
    logger.info("")
    
    # Run migration
    success = await run_migration()
    
    if success:
        # Verify migration
        verified = await verify_migration()
        
        if verified:
            await show_migration_summary()
            logger.info("")
            logger.info("🎉 Migration completed successfully!")
            logger.info("   You can now use the optimized orchestrator.")
            logger.info("")
            logger.info("Next steps:")
            logger.info("1. Set environment variables (see config/orchestrator.env)")
            logger.info("2. Test with: python test_optimized_orchestrator.py")
            logger.info("3. Update API routes to use chat_optimized.py")
            return 0
        else:
            logger.error("Migration verification failed")
            return 1
    else:
        logger.error("Migration failed")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\\nMigration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)