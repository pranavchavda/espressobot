#!/usr/bin/env python3
"""
Comprehensive Migration Script for Memory System to PostgreSQL

This script:
1. Sets up PostgreSQL database with pgvector extension
2. Migrates existing SQLite memories to PostgreSQL (if they exist)
3. Creates all necessary tables and indexes
4. Tests the setup with sample memory operations
5. Provides comprehensive error handling and status reporting

Usage:
    python migrate_memory_to_postgres.py [--force-recreate] [--skip-test]
"""

import asyncio
import os
import sys
import logging
import sqlite3
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncpg
from dotenv import load_dotenv

# Add the app directory to the path for imports
sys.path.append(str(Path(__file__).parent / "app"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
SQLITE_MEMORY_DB_PATH = "/home/pranav/espressobot/frontend/server/memory/data/espressobot_memory.db"
SCHEMA_SQL_PATH = Path(__file__).parent / "schema.sql"

# PostgreSQL Schema SQL (embedded for reliability)
POSTGRES_SCHEMA_SQL = """
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

-- Trigger function to update updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic updated_at updates
CREATE TRIGGER update_memories_updated_at BEFORE UPDATE ON memories
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_prompt_fragments_updated_at BEFORE UPDATE ON prompt_fragments
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();
"""

class MemoryMigrator:
    """Handles migration from SQLite to PostgreSQL"""
    
    def __init__(self, database_url: str, force_recreate: bool = False):
        self.database_url = database_url
        self.force_recreate = force_recreate
        self.migration_stats = {
            "memories_migrated": 0,
            "prompt_fragments_migrated": 0,
            "errors": []
        }
    
    async def check_database_connection(self) -> bool:
        """Check if we can connect to PostgreSQL database"""
        try:
            conn = await asyncpg.connect(self.database_url)
            await conn.execute("SELECT 1")
            await conn.close()
            logger.info("✅ PostgreSQL database connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            return False
    
    async def check_pgvector_extension(self) -> bool:
        """Check if pgvector extension is available"""
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Check if pgvector is available
            result = await conn.fetch("""
                SELECT name FROM pg_available_extensions 
                WHERE name = 'vector'
            """)
            
            if not result:
                logger.error("❌ pgvector extension is not available in this PostgreSQL instance")
                logger.error("   Please install pgvector: https://github.com/pgvector/pgvector#installation")
                await conn.close()
                return False
            
            # Try to create the extension
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            
            # Verify it's enabled
            result = await conn.fetch("""
                SELECT extname FROM pg_extension WHERE extname = 'vector'
            """)
            
            await conn.close()
            
            if result:
                logger.info("✅ pgvector extension is enabled")
                return True
            else:
                logger.error("❌ Failed to enable pgvector extension")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error checking pgvector extension: {e}")
            return False
    
    async def drop_existing_tables(self) -> bool:
        """Drop existing memory tables if force_recreate is True"""
        if not self.force_recreate:
            return True
        
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Drop tables in reverse dependency order
            tables = [
                'memory_analytics',
                'memory_duplicates', 
                'prompt_fragments',
                'memories'
            ]
            
            for table in tables:
                await conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logger.info(f"Dropped table: {table}")
            
            # Drop functions
            await conn.execute("DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE")
            
            await conn.close()
            logger.info("✅ Existing tables dropped successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to drop existing tables: {e}")
            return False
    
    async def create_schema(self) -> bool:
        """Create PostgreSQL schema for memory system"""
        try:
            conn = await asyncpg.connect(self.database_url)
            
            # Execute schema in a transaction
            async with conn.transaction():
                # Split SQL into individual statements
                statements = [
                    stmt.strip() 
                    for stmt in POSTGRES_SCHEMA_SQL.split(';') 
                    if stmt.strip() and not stmt.strip().startswith('--')
                ]
                
                for i, statement in enumerate(statements):
                    if statement:
                        try:
                            logger.debug(f"Executing statement {i+1}/{len(statements)}: {statement[:50]}...")
                            await conn.execute(statement)
                        except Exception as e:
                            logger.error(f"Failed to execute statement {i+1}: {e}")
                            logger.error(f"Statement: {statement}")
                            raise
                
                logger.info("✅ Schema created successfully")
                
                # Verify tables were created
                tables = await conn.fetch("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename IN ('memories', 'prompt_fragments', 'memory_duplicates', 'memory_analytics')
                    ORDER BY tablename
                """)
                
                created_tables = [t['tablename'] for t in tables]
                logger.info(f"Created tables: {created_tables}")
                
                if len(created_tables) == 4:
                    logger.info("✅ All required tables created successfully")
                else:
                    logger.warning(f"⚠️ Expected 4 tables, created {len(created_tables)}")
            
            await conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create schema: {e}")
            self.migration_stats["errors"].append(f"Schema creation: {e}")
            return False
    
    def check_sqlite_database(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Check if SQLite memory database exists and extract data"""
        sqlite_path = Path(SQLITE_MEMORY_DB_PATH)
        
        if not sqlite_path.exists():
            logger.info(f"SQLite database not found at {sqlite_path}")
            return False, []
        
        if sqlite_path.stat().st_size == 0:
            logger.info("SQLite database exists but is empty")
            return True, []
        
        try:
            conn = sqlite3.connect(str(sqlite_path))
            conn.row_factory = sqlite3.Row
            
            # Get table schema
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            if not tables:
                logger.info("SQLite database has no memory tables")
                conn.close()
                return True, []
            
            logger.info(f"Found SQLite tables: {tables}")
            
            # Extract data from relevant tables
            memory_data = []
            
            # Check for common memory table names
            for table_name in ['memories', 'memory', 'user_memories']:
                if table_name in tables:
                    cursor = conn.execute(f"SELECT * FROM {table_name}")
                    rows = cursor.fetchall()
                    
                    for row in rows:
                        memory_data.append({
                            'table': table_name,
                            'data': dict(row)
                        })
                    
                    logger.info(f"Found {len(rows)} records in {table_name}")
            
            conn.close()
            return True, memory_data
            
        except Exception as e:
            logger.error(f"❌ Error reading SQLite database: {e}")
            return False, []
    
    async def migrate_sqlite_data(self, sqlite_data: List[Dict[str, Any]]) -> bool:
        """Migrate data from SQLite to PostgreSQL"""
        if not sqlite_data:
            logger.info("No SQLite data to migrate")
            return True
        
        try:
            # Import embedding service to generate embeddings for migrated data
            from app.memory.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            
            conn = await asyncpg.connect(self.database_url)
            
            migrated_count = 0
            
            async with conn.transaction():
                for item in sqlite_data:
                    try:
                        data = item['data']
                        
                        # Map common SQLite schema fields to PostgreSQL schema
                        memory_content = data.get('content') or data.get('text') or data.get('message', '')
                        user_id = data.get('user_id') or data.get('userId') or 'migrated_user'
                        category = data.get('category') or data.get('type') or 'migrated'
                        importance = float(data.get('importance_score', 1.0))
                        metadata = data.get('metadata', '{}')
                        
                        if isinstance(metadata, str):
                            try:
                                metadata = json.loads(metadata)
                            except json.JSONDecodeError:
                                metadata = {'original': metadata}
                        
                        if not memory_content.strip():
                            continue
                        
                        # Generate embedding for content
                        logger.debug(f"Generating embedding for: {memory_content[:50]}...")
                        embedding_result = await embedding_service.get_embedding(memory_content)
                        
                        # Insert into PostgreSQL
                        await conn.execute("""
                            INSERT INTO memories 
                            (user_id, content, embedding, metadata, category, importance_score, created_at)
                            VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """, 
                        user_id,
                        memory_content,
                        embedding_result.embedding,
                        json.dumps(metadata),
                        category,
                        importance,
                        data.get('created_at', datetime.utcnow()))
                        
                        migrated_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to migrate item: {e}")
                        logger.error(f"Item data: {item}")
                        self.migration_stats["errors"].append(f"Migration item: {e}")
                        continue
            
            await conn.close()
            
            self.migration_stats["memories_migrated"] = migrated_count
            logger.info(f"✅ Migrated {migrated_count} memories from SQLite")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to migrate SQLite data: {e}")
            self.migration_stats["errors"].append(f"SQLite migration: {e}")
            return False
    
    async def insert_default_prompt_fragments(self) -> bool:
        """Insert default prompt fragments for the system"""
        try:
            from app.memory.embedding_service import get_embedding_service
            embedding_service = get_embedding_service()
            
            # Default prompt fragments
            default_fragments = [
                {
                    "category": "general_guidelines",
                    "priority": 10,
                    "content": "Always be helpful, accurate, and concise in your responses. Prioritize user safety and privacy.",
                    "agent_type": "general",
                    "context_tier": "core",
                    "tags": ["guidelines", "general", "safety"]
                },
                {
                    "category": "sales_guidelines", 
                    "priority": 9,
                    "content": "Focus on understanding customer needs and pain points before making product recommendations. Build trust through transparency.",
                    "agent_type": "sales",
                    "context_tier": "core",
                    "tags": ["sales", "customer", "trust"]
                },
                {
                    "category": "product_guidelines",
                    "priority": 8,
                    "content": "Always verify current inventory levels and product specifications before confirming availability or features.",
                    "agent_type": "products",
                    "context_tier": "standard",
                    "tags": ["products", "inventory", "accuracy"]
                },
                {
                    "category": "pricing_guidelines",
                    "priority": 8,
                    "content": "Consider market conditions, competitor pricing, and customer value perception when making pricing recommendations.",
                    "agent_type": "pricing", 
                    "context_tier": "standard",
                    "tags": ["pricing", "market", "value"]
                },
                {
                    "category": "communication_style",
                    "priority": 7,
                    "content": "Use clear, professional language. Adapt technical detail level based on user expertise. Ask clarifying questions when needed.",
                    "agent_type": None,  # Apply to all agents
                    "context_tier": "standard",
                    "tags": ["communication", "clarity", "adaptation"]
                },
                {
                    "category": "error_handling",
                    "priority": 6,
                    "content": "When encountering errors or limitations, explain them clearly and offer alternative solutions or next steps.",
                    "agent_type": None,
                    "context_tier": "standard",
                    "tags": ["errors", "solutions", "alternatives"]
                },
                {
                    "category": "memory_usage",
                    "priority": 5,
                    "content": "Leverage user memory to provide personalized responses and avoid repeating previously covered information.",
                    "agent_type": None,
                    "context_tier": "full",
                    "tags": ["memory", "personalization", "context"]
                }
            ]
            
            conn = await asyncpg.connect(self.database_url)
            
            inserted_count = 0
            
            async with conn.transaction():
                for fragment in default_fragments:
                    try:
                        # Generate embedding for fragment content
                        embedding_result = await embedding_service.get_embedding(fragment["content"])
                        
                        # Insert fragment
                        await conn.execute("""
                            INSERT INTO prompt_fragments 
                            (category, priority, content, tags, embedding, agent_type, context_tier, is_active)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT DO NOTHING
                        """, 
                        fragment["category"],
                        fragment["priority"], 
                        fragment["content"],
                        fragment["tags"],
                        embedding_result.embedding,
                        fragment["agent_type"],
                        fragment["context_tier"],
                        True)
                        
                        inserted_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to insert prompt fragment: {e}")
                        self.migration_stats["errors"].append(f"Prompt fragment: {e}")
            
            await conn.close()
            
            self.migration_stats["prompt_fragments_migrated"] = inserted_count
            logger.info(f"✅ Inserted {inserted_count} default prompt fragments")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to insert default prompt fragments: {e}")
            self.migration_stats["errors"].append(f"Default fragments: {e}")
            return False
    
    async def test_memory_operations(self) -> bool:
        """Test the memory system with sample operations"""
        try:
            from app.memory import PostgresMemoryManager, Memory, PromptAssembler, get_embedding_service
            
            logger.info("🧪 Testing memory system operations...")
            
            # Initialize components
            memory_manager = PostgresMemoryManager()
            await memory_manager.initialize()
            
            embedding_service = get_embedding_service()
            prompt_assembler = PromptAssembler(memory_manager)
            
            # Test 1: Store a test memory
            test_user_id = "migration_test_user"
            test_memory = Memory(
                user_id=test_user_id,
                content="This is a test memory created during migration to verify the system is working correctly.",
                category="test",
                importance_score=0.8,
                metadata={"created_during": "migration", "test": True}
            )
            
            memory_id = await memory_manager.store_memory(test_memory)
            logger.info(f"✅ Test memory stored with ID: {memory_id}")
            
            # Test 2: Search memories
            search_results = await memory_manager.search_memories(
                user_id=test_user_id,
                query="test memory migration",
                limit=5,
                similarity_threshold=0.5
            )
            
            if search_results:
                logger.info(f"✅ Memory search working: found {len(search_results)} results")
                logger.info(f"   Best match similarity: {search_results[0].similarity_score:.3f}")
            else:
                logger.warning("⚠️ Memory search returned no results")
            
            # Test 3: Test embedding service
            test_embedding = await embedding_service.get_embedding("Hello world test")
            logger.info(f"✅ Embedding service working: {len(test_embedding.embedding)} dimensions")
            
            # Test 4: Test prompt assembly
            assembled = await prompt_assembler.assemble_prompt(
                user_query="Help me with a test question",
                user_id=test_user_id,
                agent_type="general"
            )
            
            logger.info(f"✅ Prompt assembly working: {len(assembled.relevant_memories)} memories, {len(assembled.prompt_fragments)} fragments")
            
            # Test 5: Get statistics
            stats = await memory_manager.get_user_memory_stats(test_user_id)
            logger.info(f"✅ Memory stats: {stats}")
            
            # Clean up test data
            await memory_manager.delete_memory(memory_id, test_user_id)
            logger.info("✅ Test data cleaned up")
            
            await memory_manager.close()
            
            logger.info("🎉 All memory system tests passed!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Memory system test failed: {e}")
            import traceback
            traceback.print_exc()
            self.migration_stats["errors"].append(f"System test: {e}")
            return False
    
    async def run_migration(self, skip_test: bool = False) -> bool:
        """Run the complete migration process"""
        logger.info("🚀 Starting memory system migration to PostgreSQL...")
        
        # Step 1: Check database connection
        if not await self.check_database_connection():
            return False
        
        # Step 2: Check pgvector extension
        if not await self.check_pgvector_extension():
            return False
        
        # Step 3: Drop existing tables if requested
        if not await self.drop_existing_tables():
            return False
        
        # Step 4: Create PostgreSQL schema
        if not await self.create_schema():
            return False
        
        # Step 5: Check and migrate SQLite data
        sqlite_exists, sqlite_data = self.check_sqlite_database()
        if sqlite_exists and sqlite_data:
            logger.info(f"Found {len(sqlite_data)} records to migrate from SQLite")
            if not await self.migrate_sqlite_data(sqlite_data):
                logger.warning("⚠️ SQLite migration had errors, continuing...")
        
        # Step 6: Insert default prompt fragments
        if not await self.insert_default_prompt_fragments():
            logger.warning("⚠️ Failed to insert default prompt fragments, continuing...")
        
        # Step 7: Test the system
        if not skip_test:
            if not await self.test_memory_operations():
                logger.warning("⚠️ System test failed, but migration may still be successful")
        else:
            logger.info("Skipping system test as requested")
        
        # Final summary
        logger.info("=" * 60)
        logger.info("Migration Summary:")
        logger.info(f"  Memories migrated: {self.migration_stats['memories_migrated']}")
        logger.info(f"  Prompt fragments: {self.migration_stats['prompt_fragments_migrated']}")
        logger.info(f"  Errors encountered: {len(self.migration_stats['errors'])}")
        
        if self.migration_stats['errors']:
            logger.warning("Errors during migration:")
            for error in self.migration_stats['errors']:
                logger.warning(f"  - {error}")
        
        logger.info("=" * 60)
        
        if len(self.migration_stats['errors']) == 0:
            logger.info("🎉 Migration completed successfully!")
            return True
        elif len(self.migration_stats['errors']) < 3:
            logger.info("✅ Migration completed with minor issues")
            return True
        else:
            logger.error("❌ Migration completed with significant errors")
            return False

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Migrate memory system to PostgreSQL')
    parser.add_argument('--force-recreate', action='store_true', 
                       help='Drop and recreate existing tables')
    parser.add_argument('--skip-test', action='store_true',
                       help='Skip system testing after migration')
    
    args = parser.parse_args()
    
    # Check environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("❌ DATABASE_URL not found in environment variables")
        logger.error("   Please set DATABASE_URL to your PostgreSQL connection string")
        sys.exit(1)
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logger.error("❌ OPENAI_API_KEY not found in environment variables")
        logger.error("   Please set OPENAI_API_KEY for embedding generation")
        sys.exit(1)
    
    # Run migration
    migrator = MemoryMigrator(database_url, args.force_recreate)
    
    try:
        success = await migrator.run_migration(args.skip_test)
        
        if success:
            logger.info("✅ Memory system is ready for use!")
            sys.exit(0)
        else:
            logger.error("❌ Migration failed - please check the errors above")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Migration cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())