"""
Database Connection Pool Manager for EspressoBot
Provides proper asyncpg connection pooling with FastAPI dependency injection
Eliminates connection contention and allows concurrent database access
"""

import asyncio
import asyncpg
import os
import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import Depends

logger = logging.getLogger(__name__)

class DatabasePool:
    """Singleton database connection pool manager"""
    
    _instance: Optional['DatabasePool'] = None
    _pool: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()
    
    def __new__(cls) -> 'DatabasePool':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.database_url = self._get_database_url()
        
    def _get_database_url(self) -> str:
        """Get database URL from environment variables"""
        database_url = os.getenv("DATABASE_URL")
        if database_url:
            return database_url
            
        # Construct from individual components if DATABASE_URL not set
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT", "5432")  # Port 5432 is safe default for PostgreSQL
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        database = os.getenv("DB_NAME")
        
        # Require all essential database connection parameters
        if not all([host, user, password, database]):
            missing = [name for name, value in [("DB_HOST", host), ("DB_USER", user), ("DB_PASSWORD", password), ("DB_NAME", database)] if not value]
            raise ValueError(f"Missing required database environment variables: {', '.join(missing)}")
            
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    async def initialize(self) -> None:
        """Initialize the connection pool"""
        async with self._lock:
            if self._pool is not None:
                return
                
            try:
                logger.info("Initializing database connection pool...")
                
                # Pool configuration optimized for concurrent access
                self._pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=5,              # Minimum connections to maintain
                    max_size=20,             # Maximum connections (well under PostgreSQL limit)
                    max_queries=50000,       # Max queries per connection before recycling
                    max_inactive_connection_lifetime=300,  # 5 minutes idle timeout
                    timeout=10,              # Connection acquisition timeout
                    command_timeout=30,      # Command execution timeout
                    server_settings={
                        'application_name': 'espressobot_pool',
                        'statement_timeout': '30s',
                        'lock_timeout': '10s',
                        'idle_in_transaction_session_timeout': '60s'
                    }
                )
                
                # Test the pool
                async with self._pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                    
                logger.info(f"Database pool initialized successfully (min: 5, max: 20 connections)")
                
            except Exception as e:
                logger.error(f"Failed to initialize database pool: {e}")
                raise
    
    async def close(self) -> None:
        """Close the connection pool"""
        async with self._lock:
            if self._pool is not None:
                logger.info("Closing database connection pool...")
                await self._pool.close()
                self._pool = None
                logger.info("Database pool closed")
    
    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection from the pool"""
        if self._pool is None:
            await self.initialize()
            
        if self._pool is None:
            raise RuntimeError("Database pool not initialized")
            
        async with self._pool.acquire() as connection:
            try:
                yield connection
            except Exception as e:
                logger.error(f"Database operation error: {e}")
                # Let the pool handle connection recovery
                raise
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query that doesn't return results"""
        async with self.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetchval(self, query: str, *args):
        """Fetch a single value"""
        async with self.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def fetchrow(self, query: str, *args):
        """Fetch a single row"""
        async with self.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch(self, query: str, *args):
        """Fetch multiple rows"""
        async with self.acquire() as conn:
            return await conn.fetch(query, *args)
    
    async def executemany(self, query: str, args_list):
        """Execute a query multiple times with different parameters"""
        async with self.acquire() as conn:
            return await conn.executemany(query, args_list)
    
    async def copy_from_table(self, table_name: str, **kwargs):
        """Copy data from a table"""
        async with self.acquire() as conn:
            return await conn.copy_from_table(table_name, **kwargs)
    
    async def copy_to_table(self, table_name: str, **kwargs):
        """Copy data to a table"""
        async with self.acquire() as conn:
            return await conn.copy_to_table(table_name, **kwargs)

# Global pool instance
_db_pool = DatabasePool()

# FastAPI dependency
async def get_database_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    """FastAPI dependency to get a database connection from the pool"""
    async with _db_pool.acquire() as conn:
        yield conn

# Convenience function for direct pool access
def get_database_pool() -> DatabasePool:
    """Get the global database pool instance"""
    return _db_pool

# Legacy compatibility - provides the same interface as simple_db_pool.py
async def get_db_connection_legacy():
    """Legacy function for backward compatibility - returns the pool"""
    return _db_pool