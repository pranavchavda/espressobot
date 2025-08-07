"""Memory configuration for LangGraph"""

import os
from typing import Optional, Dict, Any, List
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
import logging

logger = logging.getLogger(__name__)

class MemoryConfig:
    """Configuration for memory management in LangGraph"""
    
    def __init__(self):
        self.memory_type = os.getenv("MEMORY_TYPE", "sqlite").lower()
        self.max_history_length = int(os.getenv("MAX_HISTORY_LENGTH", "50"))
        self.summarize_after = int(os.getenv("SUMMARIZE_AFTER", "20"))
        self.checkpointer = None
        
    def get_checkpointer(self) -> BaseCheckpointSaver:
        """Get the appropriate checkpointer based on configuration"""
        if self.checkpointer:
            return self.checkpointer
            
        if self.memory_type == "postgres":
            from app.memory.postgres_checkpointer_fixed import PostgresCheckpointerFixed
            postgres = PostgresCheckpointerFixed()
            self.checkpointer = postgres.get_sync_checkpointer()
            
        elif self.memory_type == "sqlite":
            from app.memory.sqlite_checkpointer import SqliteCheckpointer
            sqlite = SqliteCheckpointer()
            self.checkpointer = sqlite.get_sync_checkpointer()
            
        else:  # Default to in-memory
            from langgraph.checkpoint.memory import MemorySaver
            self.checkpointer = MemorySaver()
            logger.info("Using in-memory checkpointer")
            
        return self.checkpointer
    
    def trim_messages(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """Trim message history to manage token usage"""
        if len(messages) <= self.max_history_length:
            return messages
            
        # Keep the first message (usually system) and the most recent messages
        trimmed = []
        if messages and messages[0].type == "system":
            trimmed.append(messages[0])
            recent_messages = messages[-(self.max_history_length - 1):]
        else:
            recent_messages = messages[-self.max_history_length:]
            
        # Add a summary message if we're trimming a lot
        if len(messages) - len(recent_messages) > self.summarize_after:
            summary_msg = AIMessage(
                content=f"[Previous {len(messages) - len(recent_messages)} messages have been summarized for context management]"
            )
            trimmed.append(summary_msg)
            
        trimmed.extend(recent_messages)
        return trimmed
    
    def get_conversation_summary(self, messages: List[BaseMessage]) -> Optional[str]:
        """Generate a summary of the conversation (for long-term memory)"""
        if len(messages) < self.summarize_after:
            return None
            
        # Extract key points from the conversation
        key_points = []
        for msg in messages:
            if msg.type == "human":
                # Track user requests
                content = msg.content[:100] if len(msg.content) > 100 else msg.content
                key_points.append(f"User asked: {content}")
            elif msg.type == "ai" and "tool_calls" in msg.additional_kwargs:
                # Track tool usage
                for tool_call in msg.additional_kwargs["tool_calls"]:
                    key_points.append(f"Used tool: {tool_call.get('name', 'unknown')}")
                    
        if key_points:
            return "Conversation summary:\n" + "\n".join(key_points[-10:])  # Last 10 key points
        return None

class ConversationMemory:
    """Manage conversation memory with both short and long-term storage"""
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.checkpointer = self.config.get_checkpointer()
        
    def save_turn(self, thread_id: str, user_msg: str, ai_response: str, metadata: Optional[Dict[str, Any]] = None):
        """Save a conversation turn"""
        # This is handled automatically by LangGraph through checkpointing
        # But we can add additional processing here if needed
        pass
        
    def get_thread_history(self, thread_id: str, limit: Optional[int] = None) -> List[BaseMessage]:
        """Get conversation history for a thread"""
        # LangGraph handles this through the checkpointer
        # We can add filtering/processing here
        pass
        
    def search_memories(self, query: str, thread_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search through conversation memories (semantic search)"""
        # This would integrate with a vector database for semantic search
        # For now, return empty list
        return []