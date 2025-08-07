"""PostgreSQL-based checkpointer for LangGraph state persistence"""

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

class PostgresCheckpointer:
    """PostgreSQL checkpointer for persistent conversation memory"""
    
    def __init__(self, connection_string: Optional[str] = None):
        self.connection_string = connection_string or os.getenv(
            "DATABASE_URL",
            "postgresql://localhost/espressobot"
        )
        self._context_manager = None
        self.checkpointer = None
        self.async_checkpointer = None
        
    def get_sync_checkpointer(self) -> PostgresSaver:
        """Get synchronous PostgreSQL checkpointer"""
        if not self.checkpointer:
            try:
                # Create context manager and enter it to get the actual checkpointer
                self._context_manager = PostgresSaver.from_conn_string(self.connection_string)
                self.checkpointer = self._context_manager.__enter__()
                
                # Setup the schema if it doesn't exist
                self.checkpointer.setup()
                logger.info("PostgreSQL checkpointer initialized (sync)")
                
            except Exception as e:
                logger.error(f"Failed to initialize PostgreSQL checkpointer: {e}")
                # Fallback to in-memory
                from langgraph.checkpoint.memory import MemorySaver
                logger.warning("Falling back to in-memory checkpointer")
                self.checkpointer = MemorySaver()
                
        return self.checkpointer
    
    async def get_async_checkpointer(self) -> AsyncPostgresSaver:
        """Get asynchronous PostgreSQL checkpointer"""
        if not self.async_checkpointer:
            try:
                # For async, we use AsyncPostgresSaver directly
                self.async_checkpointer = await AsyncPostgresSaver.from_conn_string(self.connection_string).__aenter__()
                
                # Setup the schema if it doesn't exist
                await self.async_checkpointer.setup()
                logger.info("PostgreSQL checkpointer initialized (async)")
                
            except Exception as e:
                logger.error(f"Failed to initialize async PostgreSQL checkpointer: {e}")
                # Fallback to in-memory
                from langgraph.checkpoint.memory import MemorySaver
                logger.warning("Falling back to in-memory checkpointer")
                self.async_checkpointer = MemorySaver()
                
        return self.async_checkpointer
    
    def __del__(self):
        """Clean up connections on deletion"""
        if self._context_manager:
            try:
                self._context_manager.__exit__(None, None, None)
            except:
                pass