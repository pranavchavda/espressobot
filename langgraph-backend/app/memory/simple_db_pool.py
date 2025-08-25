"""
Simple, robust database connection handling for memory system
Uses individual connections instead of a pool to avoid connection conflicts
"""

import asyncio
import asyncpg
import os
import logging
from typing import Optional, Any
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class SimpleDBConnection:
    """Simple database connection manager that creates fresh connections"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            # Construct from individual components
            host = os.getenv("DB_HOST")
            port = os.getenv("DB_PORT", "5432")  # Safe default for PostgreSQL
            user = os.getenv("DB_USER")
            password = os.getenv("DB_PASSWORD")
            database = os.getenv("DB_NAME")
            
            # Require all essential database connection parameters
            if not all([host, user, password, database]):
                missing = [name for name, value in [("DB_HOST", host), ("DB_USER", user), ("DB_PASSWORD", password), ("DB_NAME", database)] if not value]
                raise ValueError(f"Missing required database environment variables: {', '.join(missing)}")
                
            self.database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a fresh database connection"""
        conn = None
        try:
            # Create a new connection for each operation
            conn = await asyncpg.connect(
                self.database_url,
                timeout=5,
                command_timeout=10,
                server_settings={
                    'application_name': 'espressobot_memory',
                    'statement_timeout': '10s',
                    'lock_timeout': '5s'
                }
            )
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                try:
                    await conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return results"""
        async with self.get_connection() as conn:
            return await conn.execute(query, *args)
    
    async def fetchval(self, query: str, *args) -> Any:
        """Fetch a single value"""
        async with self.get_connection() as conn:
            return await conn.fetchval(query, *args)
    
    async def fetchrow(self, query: str, *args) -> Optional[asyncpg.Record]:
        """Fetch a single row"""
        async with self.get_connection() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch(self, query: str, *args) -> list:
        """Fetch multiple rows"""
        async with self.get_connection() as conn:
            return await conn.fetch(query, *args)


# Global instance
_db_connection = None


def get_db_connection() -> SimpleDBConnection:
    """Get the global database connection manager"""
    global _db_connection
    if _db_connection is None:
        _db_connection = SimpleDBConnection()
    return _db_connection