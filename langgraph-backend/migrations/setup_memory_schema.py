#!/usr/bin/env python3
"""Setup PostgreSQL schema for memory management system"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent / "app"))

import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def setup_memory_schema():
    """Set up the PostgreSQL schema for memory management"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not found in environment")
        return False
    
    try:
        # Read schema file
        schema_file = Path(__file__).parent / "schema.sql"
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            return False
        
        schema_sql = schema_file.read_text()
        
        # Connect to database and execute schema
        conn = await asyncpg.connect(database_url)
        
        try:
            # Execute schema in a transaction
            async with conn.transaction():
                # Split and execute each statement
                statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
                
                for i, statement in enumerate(statements):
                    try:
                        logger.info(f"Executing statement {i+1}/{len(statements)}")
                        await conn.execute(statement)
                    except Exception as e:
                        logger.error(f"Failed to execute statement {i+1}: {e}")
                        logger.error(f"Statement: {statement[:100]}...")
                        raise
                
                logger.info("Schema setup completed successfully")
                
                # Verify tables were created
                tables = await conn.fetch("""
                    SELECT tablename FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename IN ('memories', 'prompt_fragments', 'memory_duplicates', 'memory_analytics')
                    ORDER BY tablename
                """)
                
                logger.info(f"Created tables: {[t['tablename'] for t in tables]}")
                
                # Check pgvector extension
                extensions = await conn.fetch("""
                    SELECT extname FROM pg_extension WHERE extname = 'vector'
                """)
                
                if extensions:
                    logger.info("pgvector extension is enabled")
                else:
                    logger.warning("pgvector extension not found - vector operations may not work")
                
        finally:
            await conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to setup memory schema: {e}")
        return False

async def insert_sample_prompt_fragments():
    """Insert sample prompt fragments for testing"""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return
    
    # Import embedding service
    from app.memory.embedding_service import get_embedding_service
    
    embedding_service = get_embedding_service()
    
    # Sample prompt fragments
    sample_fragments = [
        {
            "category": "general_guidelines",
            "priority": 10,
            "content": "Always be helpful, accurate, and concise in your responses.",
            "agent_type": "general",
            "context_tier": "core"
        },
        {
            "category": "sales_guidelines", 
            "priority": 9,
            "content": "Focus on understanding customer needs before making product recommendations.",
            "agent_type": "sales",
            "context_tier": "core"
        },
        {
            "category": "product_guidelines",
            "priority": 8,
            "content": "Always check current inventory levels before confirming product availability.",
            "agent_type": "products",
            "context_tier": "standard"
        },
        {
            "category": "pricing_guidelines",
            "priority": 8,
            "content": "Consider market conditions and competitor pricing when making pricing recommendations.",
            "agent_type": "pricing", 
            "context_tier": "standard"
        },
        {
            "category": "communication",
            "priority": 7,
            "content": "Use clear, professional language and avoid technical jargon unless specifically requested.",
            "agent_type": None,  # Apply to all agents
            "context_tier": "standard"
        }
    ]
    
    try:
        conn = await asyncpg.connect(database_url)
        
        try:
            for fragment in sample_fragments:
                # Generate embedding
                embedding_result = await embedding_service.get_embedding(fragment["content"])
                
                # Insert fragment
                await conn.execute("""
                    INSERT INTO prompt_fragments 
                    (category, priority, content, embedding, agent_type, context_tier, is_active)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT DO NOTHING
                """, 
                fragment["category"],
                fragment["priority"], 
                fragment["content"],
                embedding_result.embedding,
                fragment["agent_type"],
                fragment["context_tier"],
                True)
            
            logger.info(f"Inserted {len(sample_fragments)} sample prompt fragments")
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Failed to insert sample fragments: {e}")

async def verify_setup():
    """Verify the memory system setup"""
    
    try:
        from app.memory import PostgresMemoryManager, PromptAssembler, get_embedding_service
        
        # Test database connection
        memory_manager = PostgresMemoryManager()
        await memory_manager.initialize()
        
        # Test embedding service
        embedding_service = get_embedding_service()
        test_result = await embedding_service.get_embedding("Hello world")
        
        # Test prompt assembler
        prompt_assembler = PromptAssembler(memory_manager)
        
        logger.info("✓ Memory manager initialized successfully")
        logger.info(f"✓ Embedding service working (dim: {len(test_result.embedding)})")
        logger.info("✓ Prompt assembler initialized successfully")
        
        # Get stats
        stats = memory_manager.get_performance_stats()
        logger.info(f"✓ Performance stats: {stats}")
        
        await memory_manager.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Setup verification failed: {e}")
        return False

async def main():
    """Main setup function"""
    logger.info("Setting up PostgreSQL memory management schema...")
    
    # Step 1: Setup schema
    if not await setup_memory_schema():
        logger.error("Failed to setup schema")
        sys.exit(1)
    
    # Step 2: Insert sample data
    logger.info("Inserting sample prompt fragments...")
    await insert_sample_prompt_fragments()
    
    # Step 3: Verify setup
    logger.info("Verifying setup...")
    if await verify_setup():
        logger.info("✅ Memory management system setup completed successfully!")
    else:
        logger.error("❌ Setup verification failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())