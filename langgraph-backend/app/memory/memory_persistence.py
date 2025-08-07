"""Memory Persistence Node for LangGraph Integration"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from ..state.graph_state import GraphState
from .postgres_memory_manager import PostgresMemoryManager, Memory
from .prompt_assembler import PromptAssembler, ContextTier
from .embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

class MemoryExtractionService:
    """Service for extracting memories from conversations"""
    
    def __init__(self):
        self.openai_client = None
        self._initialize_openai()
    
    def _initialize_openai(self):
        """Initialize OpenAI client lazily"""
        try:
            import openai
            import os
            self.openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
    
    async def extract_memories_from_conversation(self, messages: List[BaseMessage], 
                                               user_id: str) -> List[Memory]:
        """Extract meaningful memories from conversation messages"""
        
        if not self.openai_client:
            return []
        
        # Get recent messages for extraction
        recent_messages = messages[-10:] if len(messages) > 10 else messages
        
        # Format messages for analysis
        conversation_text = self._format_messages_for_extraction(recent_messages)
        
        if not conversation_text.strip():
            return []
        
        extraction_prompt = f"""
Analyze the following conversation and extract important memories that should be preserved for future interactions.

Focus on:
1. User preferences and personal information
2. Important facts mentioned by the user
3. Decisions made or conclusions reached
4. Context that would be valuable in future conversations
5. User goals or objectives mentioned

Conversation:
{conversation_text}

Return a JSON list of memories to extract. Each memory should have:
- "content": The specific memory content (be concise but complete)
- "category": Category like "preference", "fact", "decision", "goal", "personal"
- "importance": Score from 0.1 to 1.0 indicating importance
- "metadata": Any additional context

Example format:
[
    {{
        "content": "User prefers email notifications over SMS",
        "category": "preference", 
        "importance": 0.8,
        "metadata": {{"topic": "notifications", "context": "communication preferences"}}
    }}
]

Return empty array [] if no significant memories found.
"""
        
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.1,
                max_tokens=1500
            )
            
            import json
            extracted_data = json.loads(response.choices[0].message.content)
            
            # Convert to Memory objects
            memories = []
            for item in extracted_data:
                memory = Memory(
                    user_id=user_id,
                    content=item.get("content", ""),
                    category=item.get("category", "general"),
                    importance_score=item.get("importance", 0.5),
                    metadata=item.get("metadata", {})
                )
                memories.append(memory)
            
            logger.info(f"Extracted {len(memories)} memories from conversation")
            return memories
            
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")
            return []
    
    def _format_messages_for_extraction(self, messages: List[BaseMessage]) -> str:
        """Format messages for memory extraction"""
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append(f"User: {msg.content}")
            elif isinstance(msg, AIMessage):
                # Extract main content, skip tool calls
                content = msg.content
                if content and content.strip():
                    formatted.append(f"Assistant: {content}")
        
        return "\n".join(formatted)

class MemoryPersistenceNode:
    """Memory persistence node for LangGraph workflow"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.memory_manager = PostgresMemoryManager(database_url)
        self.prompt_assembler = PromptAssembler(self.memory_manager)
        self.extraction_service = MemoryExtractionService()
        self.embedding_service = get_embedding_service()
        self._initialized = False
    
    async def initialize(self):
        """Initialize the memory system"""
        if not self._initialized:
            await self.memory_manager.initialize()
            self._initialized = True
            logger.info("Memory persistence node initialized")
    
    async def close(self):
        """Close resources"""
        if self._initialized:
            await self.memory_manager.close()
            self._initialized = False
    
    async def load_memory_context(self, state: GraphState) -> GraphState:
        """Load relevant memory context for the conversation"""
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get current message to search for relevant memories
            current_message = state["messages"][-1] if state["messages"] else None
            if not current_message or not isinstance(current_message, HumanMessage):
                return state
            
            user_id = state.get("user_id")
            if not user_id:
                logger.warning("No user_id provided for memory context loading")
                return state
            
            query = current_message.content
            current_agent = state.get("current_agent", "general")
            
            # Determine context tier based on query complexity
            context_tier = self._determine_context_tier(query, state)
            
            # Assemble intelligent prompt with memory context
            assembled_prompt = await self.prompt_assembler.assemble_prompt(
                user_query=query,
                user_id=user_id,
                agent_type=current_agent,
                context_tier=context_tier,
                conversation_context=self._extract_conversation_context(state)
            )
            
            # Update state with memory context
            state["memory_context"] = [
                {
                    "id": mem.id,
                    "content": mem.content,
                    "category": mem.category,
                    "importance": mem.importance_score,
                    "similarity": getattr(mem, 'similarity_score', None)
                }
                for mem in assembled_prompt.relevant_memories
            ]
            
            state["prompt_fragments"] = [
                {
                    "category": frag.category,
                    "content": frag.content,
                    "priority": frag.priority,
                    "agent_type": frag.agent_type
                }
                for frag in assembled_prompt.prompt_fragments
            ]
            
            state["context_tier"] = context_tier.value
            state["memory_search_query"] = query
            state["consolidated_context"] = assembled_prompt.consolidation_applied
            
            # Update system context with assembled prompt
            if "context" not in state:
                state["context"] = {}
            
            state["context"]["memory_summary"] = assembled_prompt.context_summary
            state["context"]["system_prompt_enhancement"] = assembled_prompt.system_prompt
            state["context"]["memory_count"] = len(assembled_prompt.relevant_memories)
            state["context"]["fragment_count"] = len(assembled_prompt.prompt_fragments)
            
            logger.info(f"Loaded memory context: {len(assembled_prompt.relevant_memories)} memories, "
                       f"{len(assembled_prompt.prompt_fragments)} fragments, tier: {context_tier.value}")
            
        except Exception as e:
            logger.error(f"Failed to load memory context: {e}")
            # Continue without memory context rather than fail
        
        return state
    
    async def persist_conversation_memories(self, state: GraphState) -> GraphState:
        """Extract and persist memories from the conversation"""
        
        if not self._initialized:
            await self.initialize()
        
        try:
            user_id = state.get("user_id")
            if not user_id:
                return state
            
            messages = state.get("messages", [])
            if len(messages) < 2:  # Need at least user message and response
                return state
            
            # Extract memories from conversation
            new_memories = await self.extraction_service.extract_memories_from_conversation(
                messages, user_id
            )
            
            # Store memories
            stored_count = 0
            for memory in new_memories:
                try:
                    memory_id = await self.memory_manager.store_memory(memory)
                    if memory_id:
                        stored_count += 1
                except Exception as e:
                    logger.error(f"Failed to store memory: {e}")
            
            # Update metadata
            if "metadata" not in state:
                state["metadata"] = {}
            
            state["metadata"]["memories_extracted"] = len(new_memories)
            state["metadata"]["memories_stored"] = stored_count
            
            if stored_count > 0:
                logger.info(f"Persisted {stored_count} memories from conversation")
            
        except Exception as e:
            logger.error(f"Failed to persist conversation memories: {e}")
        
        return state
    
    def _determine_context_tier(self, query: str, state: GraphState) -> ContextTier:
        """Determine appropriate context tier based on query complexity"""
        
        query_lower = query.lower()
        
        # Complex queries that need full context
        complex_indicators = [
            "analyze", "compare", "detailed", "comprehensive", "explain why",
            "what are all", "give me everything", "full report", "in depth"
        ]
        
        # Simple queries that need minimal context
        simple_indicators = [
            "what is", "who is", "when", "where", "yes", "no", "thanks",
            "hello", "hi", "ok", "sure", "help"
        ]
        
        if any(indicator in query_lower for indicator in complex_indicators):
            return ContextTier.FULL
        elif any(indicator in query_lower for indicator in simple_indicators):
            return ContextTier.CORE
        elif len(query.split()) > 20:  # Long queries get more context
            return ContextTier.FULL
        else:
            return ContextTier.STANDARD
    
    def _extract_conversation_context(self, state: GraphState) -> List[Dict]:
        """Extract conversation context from state"""
        messages = state.get("messages", [])
        context = []
        
        for msg in messages[-5:]:  # Last 5 messages
            context.append({
                "role": msg.type,
                "content": msg.content[:200] if len(msg.content) > 200 else msg.content,
                "timestamp": getattr(msg, 'timestamp', None)
            })
        
        return context
    
    async def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for a user"""
        if not self._initialized:
            await self.initialize()
        
        try:
            stats = await self.memory_manager.get_user_memory_stats(user_id)
            performance = self.memory_manager.get_performance_stats()
            
            return {
                **stats,
                "performance": performance
            }
        except Exception as e:
            logger.error(f"Failed to get memory stats: {e}")
            return {}
    
    async def search_user_memories(self, user_id: str, query: str, 
                                 limit: int = 10) -> List[Dict[str, Any]]:
        """Search user memories"""
        if not self._initialized:
            await self.initialize()
        
        try:
            results = await self.memory_manager.search_memories(
                user_id=user_id,
                query=query,
                limit=limit
            )
            
            return [
                {
                    "content": result.memory.content,
                    "category": result.memory.category,
                    "similarity_score": result.similarity_score,
                    "importance": result.memory.importance_score,
                    "created_at": result.memory.created_at.isoformat() if result.memory.created_at else None
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"Failed to search memories: {e}")
            return []

# Global instance for graph integration
_memory_node_instance: Optional[MemoryPersistenceNode] = None

def get_memory_node(database_url: Optional[str] = None) -> MemoryPersistenceNode:
    """Get singleton memory persistence node"""
    global _memory_node_instance
    if _memory_node_instance is None:
        _memory_node_instance = MemoryPersistenceNode(database_url)
    return _memory_node_instance