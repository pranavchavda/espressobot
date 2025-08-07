"""PostgreSQL-based checkpointer for LangGraph state persistence - Fixed version"""

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from typing import Optional
import os
import logging
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)

class PostgresCheckpointerFixed:
    """PostgreSQL checkpointer for persistent conversation memory"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            "postgresql://localhost/espressobot"
        )
        self.conn = None
        self.checkpointer = None
        
    def get_sync_checkpointer(self) -> PostgresSaver:
        """Get synchronous PostgreSQL checkpointer"""
        if not self.checkpointer:
            try:
                # Create a connection pool for the checkpointer
                from psycopg_pool import ConnectionPool
                
                # Create a connection pool
                pool = ConnectionPool(
                    self.connection_string,
                    min_size=1,
                    max_size=10,
                    kwargs={
                        "autocommit": True,
                        "row_factory": dict_row
                    }
                )
                
                # Create checkpointer with the pool
                self.checkpointer = PostgresSaver(pool)
                
                # Setup the schema if it doesn't exist
                try:
                    self.checkpointer.setup()
                except Exception as setup_error:
                    # Schema might already exist, which is fine
                    logger.debug(f"Schema setup note: {setup_error}")
                    
                logger.info("PostgreSQL checkpointer initialized (sync) with connection pool")
                
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL checkpointer: {e}")
                # Fallback to in-memory
                from langgraph.checkpoint.memory import MemorySaver
                logger.warning("Falling back to in-memory checkpointer")
                self.checkpointer = MemorySaver()
                
        return self.checkpointer
    
    def __del__(self):
        """Clean up connection on deletion"""
        if self.conn:
            try:
                self.conn.close()
            except:
                pass