#!/usr/bin/env python3
"""
Database migration script to add ga4_property_id column to users table.
Run this once to add the new column for user-specific GA4 property IDs.
"""
import asyncio
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.session import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_ga4_column():
    """Add ga4_property_id column to users table if it doesn't exist"""
    try:
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./espressobot.db")
        logger.info(f"Using database: {DATABASE_URL[:20]}...")
        async with engine.begin() as conn:
            # Check if column exists
            if DATABASE_URL.startswith("postgresql+asyncpg://"):
                # PostgreSQL
                result = await conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='users' AND column_name='ga4_property_id'
                """))
            else:
                # SQLite
                result = await conn.execute(text("PRAGMA table_info(users)"))
                columns = await result.fetchall()
                column_exists = any(col[1] == 'ga4_property_id' for col in columns)
                
                if not column_exists:
                    logger.info("Adding ga4_property_id column to users table...")
                    await conn.execute(text("""
                        ALTER TABLE users ADD COLUMN ga4_property_id VARCHAR(255)
                    """))
                    logger.info("Successfully added ga4_property_id column")
                else:
                    logger.info("ga4_property_id column already exists")
                return
            
            # For PostgreSQL, check if column exists
            if await result.fetchone():
                logger.info("ga4_property_id column already exists")
            else:
                logger.info("Adding ga4_property_id column to users table...")
                await conn.execute(text("""
                    ALTER TABLE users ADD COLUMN ga4_property_id VARCHAR(255)
                """))
                logger.info("Successfully added ga4_property_id column")
        
        await engine.dispose()
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate_ga4_column())