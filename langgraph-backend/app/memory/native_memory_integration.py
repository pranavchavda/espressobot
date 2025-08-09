"""Native LangChain/LangGraph Memory Integration

This module provides a comprehensive implementation using LangChain's native memory classes
and LangGraph's built-in checkpointing capabilities, replacing custom implementations with
standardized, maintained solutions.

Features:
- LangGraph PostgresSaver for persistent checkpointing
- LangChain memory classes for conversation history
- Native pgvector integration for semantic search
- Built-in embedding management with OpenAI
- Standardized memory interfaces
"""

import os
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

# LangGraph native imports
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph

# LangChain native memory imports
from langchain.memory import (
    ConversationBufferMemory,
    ConversationSummaryMemory,
    VectorStoreRetrieverMemory,
    ConversationBufferWindowMemory
)
from langchain_core.memory import BaseMemory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.vectorstores import VectorStore
from langchain_core.retrievers import BaseRetriever
from langchain_core.embeddings import Embeddings

# Import native components with proper error handling
try:
    from langchain_openai import OpenAIEmbeddings
    OPENAI_AVAILABLE = True
except ImportError as e:
    logging.warning(f"langchain-openai not available: {e}")
    OPENAI_AVAILABLE = False
    OpenAIEmbeddings = None

try:
    from langchain_postgres import PGVector
    POSTGRES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"langchain-postgres not available: {e}")
    POSTGRES_AVAILABLE = False
    PGVector = None

try:
    from langchain_community.vectorstores import Chroma, FAISS
    FALLBACK_VECTORSTORES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Fallback vector stores not available: {e}")
    FALLBACK_VECTORSTORES_AVAILABLE = False
    Chroma = None
    FAISS = None

import json
import asyncpg
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class MemoryType(Enum):
    """Types of memory systems available"""
    BUFFER = "buffer"  # Keep last N messages
    SUMMARY = "summary"  # Summarize old messages
    VECTOR = "vector"  # Semantic search on embeddings
    COMBINED = "combined"  # Combination of approaches

class ContextTier(Enum):
    """Context tiers for different memory needs"""
    MINIMAL = "minimal"  # 2K tokens
    STANDARD = "standard"  # 4K tokens  
    FULL = "full"  # 8K tokens

@dataclass
class MemoryConfig:
    """Configuration for native memory integration"""
    memory_type: MemoryType = MemoryType.COMBINED
    context_tier: ContextTier = ContextTier.STANDARD
    buffer_size: int = 10  # Number of messages to keep in buffer
    summary_max_tokens: int = 500  # Max tokens for summaries
    vector_similarity_threshold: float = 0.7
    vector_top_k: int = 5
    embedding_model: str = "text-embedding-3-large"
    llm_model: str = "gpt-4.1-nano"
    database_url: Optional[str] = None
    table_name: str = "langchain_pg_embedding"
    collection_name: str = "espressobot_memories"

@dataclass 
class MemoryResult:
    """Result from memory retrieval"""
    content: str
    metadata: Dict[str, Any]
    similarity_score: Optional[float] = None
    timestamp: Optional[datetime] = None

class NativeMemoryManager:
    """Native LangChain/LangGraph memory management system
    
    Uses standard LangChain memory classes and LangGraph checkpointing
    instead of custom implementations.
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self.config.database_url = self.config.database_url or os.getenv("DATABASE_URL")
        
        # Initialize native components
        self.embeddings: Embeddings = self._setup_embeddings()
        self.checkpointer: BaseCheckpointSaver = self._setup_checkpointer()
        self.vector_store: Optional[VectorStore] = None
        self.retriever: Optional[BaseRetriever] = None
        
        # Memory instances per user
        self.user_memories: Dict[str, BaseMemory] = {}
        self.user_vectors: Dict[str, VectorStoreRetrieverMemory] = {}
        
        # Performance tracking
        self.query_count = 0
        self.cache_hits = 0
        
    def _setup_embeddings(self) -> Optional[Embeddings]:
        """Setup OpenAI embeddings with native LangChain integration"""
        if not OPENAI_AVAILABLE or not OpenAIEmbeddings:
            logger.warning("OpenAI embeddings not available")
            return None
            
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, embeddings unavailable")
            return None
            
        try:
            return OpenAIEmbeddings(
                model=self.config.embedding_model,
                openai_api_key=api_key
            )
        except Exception as e:
            logger.error(f"Failed to setup OpenAI embeddings: {e}")
            return None
    
    def _setup_checkpointer(self) -> BaseCheckpointSaver:
        """Setup native LangGraph checkpointer"""
        if self.config.database_url and "postgresql" in self.config.database_url:
            try:
                return PostgresSaver.from_conn_string(
                    self.config.database_url,
                    sync_connection=False
                )
            except Exception as e:
                logger.warning(f"Failed to setup PostgresSaver: {e}, falling back to MemorySaver")
                return MemorySaver()
        else:
            return MemorySaver()
    
    async def _setup_vector_store(self, user_id: str) -> Optional[VectorStore]:
        """Setup vector store for semantic search with fallbacks"""
        if not self.embeddings:
            logger.warning("No embeddings available, vector store disabled")
            return None
            
        # Try PGVector first (preferred)
        if POSTGRES_AVAILABLE and PGVector and self.config.database_url:
            try:
                vector_store = PGVector(
                    embeddings=self.embeddings,
                    connection_string=self.config.database_url,
                    collection_name=f"{self.config.collection_name}_{user_id}",
                    use_jsonb=True,
                )
                logger.info(f"Using PGVector for user {user_id}")
                return vector_store
            except Exception as e:
                logger.warning(f"PGVector setup failed for {user_id}: {e}, trying fallbacks")
        
        # Fallback to in-memory vector stores
        if FALLBACK_VECTORSTORES_AVAILABLE:
            try:
                if FAISS:
                    # Use FAISS for in-memory vector search
                    import numpy as np
                    # Create empty FAISS index
                    vector_store = FAISS.from_texts(
                        texts=["initialization"],
                        embedding=self.embeddings,
                        metadatas=[{"init": True}]
                    )
                    logger.info(f"Using FAISS fallback for user {user_id}")
                    return vector_store
                elif Chroma:
                    # Use Chroma for persistent vector search
                    vector_store = Chroma(
                        embedding_function=self.embeddings,
                        persist_directory=f"./chroma_db_{user_id}"
                    )
                    logger.info(f"Using Chroma fallback for user {user_id}")
                    return vector_store
            except Exception as e:
                logger.error(f"Fallback vector store setup failed: {e}")
        
        logger.warning(f"No vector store available for user {user_id}")
        return None
    
    async def initialize(self):
        """Initialize the memory system"""
        logger.info("Initializing native memory integration")
        
        # Initialize checkpointer if it's PostgresSaver
        if isinstance(self.checkpointer, PostgresSaver):
            await self.checkpointer.setup()
            
        logger.info(f"Memory system initialized with {type(self.checkpointer).__name__}")
    
    async def get_or_create_memory(self, user_id: str) -> BaseMemory:
        """Get or create memory instance for user using native LangChain classes"""
        if user_id not in self.user_memories:
            if self.config.memory_type == MemoryType.BUFFER:
                memory = ConversationBufferWindowMemory(
                    k=self.config.buffer_size,
                    return_messages=True,
                    memory_key="chat_history"
                )
            elif self.config.memory_type == MemoryType.SUMMARY:
                # Note: ConversationSummaryMemory requires an LLM
                try:
                    if OPENAI_AVAILABLE:
                        from langchain_openai import ChatOpenAI
                        llm = ChatOpenAI(
                            model=self.config.llm_model,
                            openai_api_key=os.getenv("OPENAI_API_KEY")
                        )
                        memory = ConversationSummaryMemory(
                            llm=llm,
                            return_messages=True,
                            memory_key="chat_history"
                        )
                    else:
                        logger.warning("OpenAI not available, falling back to buffer memory")
                        memory = ConversationBufferWindowMemory(
                            k=self.config.buffer_size,
                            return_messages=True,
                            memory_key="chat_history"
                        )
                except Exception as e:
                    logger.error(f"Failed to setup summary memory: {e}, falling back to buffer")
                    memory = ConversationBufferWindowMemory(
                        k=self.config.buffer_size,
                        return_messages=True,
                        memory_key="chat_history"
                    )
            elif self.config.memory_type == MemoryType.VECTOR:
                # Setup vector-based memory
                vector_store = await self._setup_vector_store(user_id)
                if vector_store:
                    retriever = vector_store.as_retriever(
                        search_kwargs={"k": self.config.vector_top_k}
                    )
                    memory = VectorStoreRetrieverMemory(
                        retriever=retriever,
                        memory_key="chat_history",
                        return_messages=True
                    )
                else:
                    # Fallback to buffer memory
                    memory = ConversationBufferWindowMemory(
                        k=self.config.buffer_size,
                        return_messages=True,
                        memory_key="chat_history"
                    )
            else:  # COMBINED
                # Use buffer memory as primary, will add vector search separately
                memory = ConversationBufferWindowMemory(
                    k=self.config.buffer_size,
                    return_messages=True,
                    memory_key="chat_history"
                )
                
                # Setup vector memory for semantic search
                vector_store = await self._setup_vector_store(user_id)
                if vector_store:
                    retriever = vector_store.as_retriever(
                        search_kwargs={"k": self.config.vector_top_k}
                    )
                    vector_memory = VectorStoreRetrieverMemory(
                        retriever=retriever,
                        memory_key="semantic_context",
                        return_messages=True
                    )
                    self.user_vectors[user_id] = vector_memory
            
            self.user_memories[user_id] = memory
            logger.info(f"Created {type(memory).__name__} for user {user_id}")
        
        return self.user_memories[user_id]
    
    async def save_conversation_checkpoint(self, 
                                         user_id: str, 
                                         thread_id: str,
                                         state: Dict[str, Any]) -> str:
        """Save conversation state using native LangGraph checkpointing"""
        config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
        
        # Use native checkpointer
        checkpoint_id = await self.checkpointer.aput(
            config=config,
            checkpoint={
                "ts": datetime.utcnow().isoformat(),
                **state
            },
            metadata={"user_id": user_id, "thread_id": thread_id}
        )
        
        logger.debug(f"Saved checkpoint {checkpoint_id} for user {user_id}")
        return checkpoint_id
    
    async def load_conversation_checkpoint(self, 
                                         user_id: str,
                                         thread_id: str) -> Optional[Dict[str, Any]]:
        """Load conversation state using native checkpointing"""
        config = {"configurable": {"thread_id": thread_id, "user_id": user_id}}
        
        try:
            checkpoint = await self.checkpointer.aget(config)
            if checkpoint:
                logger.debug(f"Loaded checkpoint for user {user_id}, thread {thread_id}")
                return checkpoint.get("checkpoint", {})
            return None
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    async def add_message(self, user_id: str, message: BaseMessage) -> None:
        """Add message to user's memory using native LangChain interfaces"""
        memory = await self.get_or_create_memory(user_id)
        
        # Save to conversation memory
        if isinstance(message, HumanMessage):
            memory.chat_memory.add_user_message(message.content)
        elif isinstance(message, AIMessage):
            memory.chat_memory.add_ai_message(message.content)
        
        # Also save to vector memory if available (for semantic search)
        if user_id in self.user_vectors:
            vector_memory = self.user_vectors[user_id]
            if isinstance(message, HumanMessage):
                vector_memory.save_context(
                    {"input": message.content},
                    {"output": ""}
                )
            elif isinstance(message, AIMessage):
                vector_memory.save_context(
                    {"input": ""},
                    {"output": message.content}
                )
    
    async def get_conversation_context(self, 
                                     user_id: str,
                                     query: Optional[str] = None) -> Dict[str, Any]:
        """Get conversation context using native memory classes"""
        memory = await self.get_or_create_memory(user_id)
        context = {}
        
        # Get buffer/summary context
        try:
            memory_vars = memory.load_memory_variables({})
            context.update(memory_vars)
        except Exception as e:
            logger.error(f"Failed to load memory variables: {e}")
        
        # Get semantic context if available and query provided
        if query and user_id in self.user_vectors:
            try:
                vector_memory = self.user_vectors[user_id]
                vector_context = vector_memory.load_memory_variables({"query": query})
                context["semantic_context"] = vector_context.get("semantic_context", [])
            except Exception as e:
                logger.error(f"Failed to load vector context: {e}")
        
        self.query_count += 1
        return context
    
    async def search_memories(self, 
                            user_id: str,
                            query: str,
                            limit: int = 5) -> List[MemoryResult]:
        """Search memories using native vector store retriever"""
        if user_id not in self.user_vectors:
            logger.warning(f"No vector memory available for user {user_id}")
            return []
        
        try:
            vector_memory = self.user_vectors[user_id]
            retriever = vector_memory.retriever
            
            # Use native retriever search
            docs = await retriever.ainvoke(query)
            
            results = []
            for i, doc in enumerate(docs[:limit]):
                results.append(MemoryResult(
                    content=doc.page_content,
                    metadata=doc.metadata,
                    similarity_score=doc.metadata.get("similarity_score"),
                    timestamp=doc.metadata.get("timestamp")
                ))
            
            return results
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []
    
    async def clear_user_memory(self, user_id: str) -> bool:
        """Clear all memory for a user"""
        try:
            if user_id in self.user_memories:
                memory = self.user_memories[user_id]
                memory.clear()
                del self.user_memories[user_id]
            
            if user_id in self.user_vectors:
                # Note: Vector store clearing depends on implementation
                # For now, just remove from cache
                del self.user_vectors[user_id]
            
            logger.info(f"Cleared memory for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to clear memory for user {user_id}: {e}")
            return False
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return {
            "total_users": len(self.user_memories),
            "users_with_vectors": len(self.user_vectors),
            "total_queries": self.query_count,
            "cache_hits": self.cache_hits,
            "checkpointer_type": type(self.checkpointer).__name__,
            "memory_type": self.config.memory_type.value,
            "context_tier": self.config.context_tier.value
        }

class NativeMemoryNode:
    """LangGraph node for native memory integration"""
    
    def __init__(self, memory_manager: NativeMemoryManager):
        self.memory_manager = memory_manager
    
    async def load_memory_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Load memory context into graph state"""
        user_id = state.get("user_id")
        if not user_id:
            logger.warning("No user_id in state for memory loading")
            return state
        
        # Get conversation context
        query = state.get("messages", [])[-1].content if state.get("messages") else None
        context = await self.memory_manager.get_conversation_context(user_id, query)
        
        # Add context to state
        state["memory_context"] = context
        
        # Save checkpoint
        thread_id = state.get("thread_id", "default")
        await self.memory_manager.save_conversation_checkpoint(
            user_id, thread_id, state
        )
        
        return state
    
    async def persist_conversation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Persist conversation messages to memory"""
        user_id = state.get("user_id")
        messages = state.get("messages", [])
        
        if not user_id or not messages:
            return state
        
        # Add latest message to memory
        latest_message = messages[-1]
        await self.memory_manager.add_message(user_id, latest_message)
        
        logger.debug(f"Persisted message for user {user_id}")
        return state

# Factory functions for easy integration
def create_native_memory_manager(config: Optional[MemoryConfig] = None) -> NativeMemoryManager:
    """Factory function to create native memory manager"""
    return NativeMemoryManager(config)

def create_memory_node(memory_manager: NativeMemoryManager) -> NativeMemoryNode:
    """Factory function to create memory node for LangGraph"""
    return NativeMemoryNode(memory_manager)

# Backwards compatibility with existing system
class NativeMemoryIntegration:
    """High-level interface for native memory integration
    
    Provides a simple interface that can replace existing custom implementations.
    """
    
    def __init__(self, 
                 memory_type: MemoryType = MemoryType.COMBINED,
                 context_tier: ContextTier = ContextTier.STANDARD):
        config = MemoryConfig(memory_type=memory_type, context_tier=context_tier)
        self.manager = NativeMemoryManager(config)
        self.node = NativeMemoryNode(self.manager)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the memory integration"""
        if not self._initialized:
            await self.manager.initialize()
            self._initialized = True
    
    async def enhance_agent_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance agent state with memory context"""
        if not self._initialized:
            await self.initialize()
        
        # Load memory context
        state = await self.node.load_memory_context(state)
        
        # This can be called after agent processing to persist
        # For now, we persist immediately
        state = await self.node.persist_conversation(state)
        
        return state
    
    async def search_user_memories(self, user_id: str, query: str) -> List[MemoryResult]:
        """Search user memories"""
        if not self._initialized:
            await self.initialize()
        
        return await self.manager.search_memories(user_id, query)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        return self.manager.get_memory_stats()

# Example usage and testing
async def main():
    """Example usage of native memory integration"""
    logging.basicConfig(level=logging.INFO)
    
    # Create native memory integration
    memory_integration = NativeMemoryIntegration(
        memory_type=MemoryType.COMBINED,
        context_tier=ContextTier.STANDARD
    )
    
    await memory_integration.initialize()
    
    # Simulate agent state
    test_state = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "messages": [HumanMessage(content="Hello, I need help with API integration")]
    }
    
    # Enhance state with memory
    enhanced_state = await memory_integration.enhance_agent_state(test_state)
    
    print("Enhanced state keys:", list(enhanced_state.keys()))
    print("Memory context:", enhanced_state.get("memory_context", {}).keys())
    
    # Search memories
    results = await memory_integration.search_user_memories(
        "test_user", "API integration help"
    )
    print(f"Found {len(results)} relevant memories")
    
    # Get stats
    stats = memory_integration.get_stats()
    print("Memory stats:", stats)

if __name__ == "__main__":
    asyncio.run(main())
