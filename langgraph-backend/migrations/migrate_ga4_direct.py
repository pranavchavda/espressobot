#!/usr/bin/env python3
"""
Direct migration script to add ga4_property_id column to users table
Uses asyncpg directly to connect to PostgreSQL
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_ga4_column():
    """Add ga4_property_id column to users table if it doesn't exist"""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not found in environment variables")
        return False
    
    logger.info(f"Connecting to database...")
    
    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(database_url)
        
        try:
            # Check if users table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                )
            """)
            
            if not table_exists:
                logger.error("Users table does not exist in the database")
                return False
            
            # Check if ga4_property_id column already exists
            column_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND column_name = 'ga4_property_id'
                )
            """)
            
            if column_exists:
                logger.info("✅ ga4_property_id column already exists in users table")
                return True
            
            # Add the column
            logger.info("Adding ga4_property_id column to users table...")
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN ga4_property_id VARCHAR(255)
            """)
            
            logger.info("✅ Successfully added ga4_property_id column to users table")
            
            # Verify the column was added
            columns = await conn.fetch("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'users' 
                AND column_name LIKE '%google%' OR column_name LIKE '%ga4%'
                ORDER BY column_name
            """)
            
            logger.info("\nGoogle-related columns in users table:")
            for col in columns:
                logger.info(f"  - {col['column_name']}: {col['data_type']}")
            
            return True
            
        finally:
            await conn.close()
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_connection():
    """Test the database connection and show user table structure"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not found")
        return
    
    try:
        conn = await asyncpg.connect(database_url)
        
        # Get all columns from users table
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """)
        
        logger.info("\nCurrent users table structure:")
        logger.info("-" * 50)
        for col in columns:
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            logger.info(f"{col['column_name']:30} {col['data_type']:20} {nullable}")
        
        # Count users
        user_count = await conn.fetchval("SELECT COUNT(*) FROM users")
        logger.info(f"\nTotal users in database: {user_count}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Connection test failed: {e}")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("GA4 Property ID Column Migration")
    logger.info("=" * 60)
    
    # Run the migration
    success = asyncio.run(migrate_ga4_column())
    
    if success:
        logger.info("\n" + "=" * 60)
        logger.info("Migration completed successfully!")
        logger.info("=" * 60)
        
        # Show the updated table structure
        asyncio.run(test_connection())
    else:
        logger.error("\n" + "=" * 60)
        logger.error("Migration failed - please check the logs")
        logger.error("=" * 60)