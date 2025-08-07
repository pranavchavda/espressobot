"""SQLite-based checkpointer for LangGraph state persistence"""

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from typing import Optional
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class SqliteCheckpointer:
    """SQLite checkpointer for persistent conversation memory"""
    
    def __init__(self, db_path: Optional[str] = None):
        # Default to a local SQLite database
        if not db_path:
            db_dir = Path.home() / ".espressobot" / "memory"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(db_dir / "conversations.db")
            
        self.db_path = db_path
        self.checkpointer = None
        self.async_checkpointer = None
        logger.info(f"SQLite checkpointer using database: {self.db_path}")
        
    def get_sync_checkpointer(self) -> SqliteSaver:
        """Get synchronous SQLite checkpointer"""
        if not self.checkpointer:
            try:
                self.checkpointer = SqliteSaver.from_conn_string(self.db_path)
                logger.info("SQLite checkpointer initialized (sync)")
                
            except Exception as e:
                logger.error(f"Failed to initialize SQLite checkpointer: {e}")
                # Fallback to in-memory
                from langgraph.checkpoint.memory import MemorySaver
                logger.warning("Falling back to in-memory checkpointer")
                self.checkpointer = MemorySaver()
                
        return self.checkpointer
    
    async def get_async_checkpointer(self) -> AsyncSqliteSaver:
        """Get asynchronous SQLite checkpointer"""
        if not self.async_checkpointer:
            try:
                self.async_checkpointer = AsyncSqliteSaver.from_conn_string(self.db_path)
                logger.info("SQLite checkpointer initialized (async)")
                
            except Exception as e:
                logger.error(f"Failed to initialize async SQLite checkpointer: {e}")
                # Fallback to in-memory
                from langgraph.checkpoint.memory import MemorySaver
                logger.warning("Falling back to in-memory checkpointer")
                self.async_checkpointer = MemorySaver()
                
        return self.async_checkpointer