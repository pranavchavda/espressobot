"""Memory-aware mixin for agents to use the memory system effectively"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import asyncio
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

class MemoryAwareMixin:
    """Mixin to make agents memory-aware with automatic memory operations"""
    
    def __init__(self):
        self._memory_manager = None
        self._memory_cache = {}
        self._memory_enabled = True
        
    async def _get_memory_manager(self):
        """Get or initialize memory manager"""
        if not self._memory_manager:
            from app.memory.postgres_memory_manager import PostgresMemoryManager
            self._memory_manager = PostgresMemoryManager()
            await self._memory_manager.initialize()
        return self._memory_manager
    
    async def get_relevant_memories(
        self, 
        query: str, 
        user_id: str,
        limit: int = 5,
        category: Optional[str] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Fetch memories relevant to the current query"""
        try:
            if not self._memory_enabled:
                return []
            
            # Check cache first
            cache_key = f"{user_id}:{query[:50]}:{category}"
            if cache_key in self._memory_cache:
                cached_result, timestamp = self._memory_cache[cache_key]
                # Cache valid for 5 minutes
                if (datetime.utcnow() - timestamp).seconds < 300:
                    return cached_result
            
            manager = await self._get_memory_manager()
            
            # Search for relevant memories
            search_results = await manager.search_memories(
                user_id=user_id,
                query=query,
                limit=limit,
                similarity_threshold=similarity_threshold
            )
            
            # Filter by category if specified
            memories = []
            for result in search_results:
                if category and result.memory.category != category:
                    continue
                    
                memories.append({
                    "content": result.memory.content,
                    "category": result.memory.category,
                    "importance": result.memory.importance_score,
                    "similarity": result.similarity_score,
                    "metadata": result.memory.metadata,
                    "created_at": result.memory.created_at
                })
            
            # Update cache
            self._memory_cache[cache_key] = (memories, datetime.utcnow())
            
            # Clean old cache entries
            self._clean_cache()
            
            return memories
            
        except Exception as e:
            logger.error(f"Error fetching relevant memories: {e}")
            return []
    
    async def store_interaction_memory(
        self,
        user_id: str,
        content: str,
        category: str,
        importance: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """Store an important interaction as a memory"""
        try:
            if not self._memory_enabled:
                return None
            
            from app.memory.postgres_memory_manager import Memory
            
            manager = await self._get_memory_manager()
            
            # Add agent context to metadata
            agent_metadata = {
                "agent": getattr(self, 'name', 'unknown'),
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            memory = Memory(
                user_id=user_id,
                content=content,
                category=category,
                importance_score=importance,
                metadata=agent_metadata
            )
            
            memory_id = await manager.store_memory(memory)
            
            logger.info(f"Stored memory {memory_id} for user {user_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Error storing interaction memory: {e}")
            return None
    
    async def extract_and_store_facts(
        self,
        state: Dict[str, Any],
        messages: List[Any]
    ) -> List[int]:
        """Extract important facts from conversation and store as memories"""
        try:
            if not self._memory_enabled:
                return []
            
            user_id = state.get("user_id")
            if not user_id:
                return []
            
            stored_ids = []
            
            # Extract facts from recent messages
            for msg in messages[-5:]:  # Last 5 messages
                if isinstance(msg, AIMessage):
                    # Look for important information in AI responses
                    content = msg.content
                    
                    # Extract product recommendations
                    if "recommend" in content.lower() or "suggest" in content.lower():
                        memory_id = await self.store_interaction_memory(
                            user_id=user_id,
                            content=f"Product recommendation: {content[:500]}",
                            category="products",
                            importance=2.0,
                            metadata={
                                "type": "recommendation",
                                "thread_id": state.get("thread_id")
                            }
                        )
                        if memory_id:
                            stored_ids.append(memory_id)
                    
                    # Extract problem solutions
                    if "solved" in content.lower() or "fixed" in content.lower():
                        memory_id = await self.store_interaction_memory(
                            user_id=user_id,
                            content=f"Solution: {content[:500]}",
                            category="solutions",
                            importance=3.0,
                            metadata={
                                "type": "solution",
                                "thread_id": state.get("thread_id")
                            }
                        )
                        if memory_id:
                            stored_ids.append(memory_id)
                
                elif isinstance(msg, HumanMessage):
                    # Extract user preferences
                    content = msg.content
                    
                    if "prefer" in content.lower() or "like" in content.lower():
                        memory_id = await self.store_interaction_memory(
                            user_id=user_id,
                            content=f"User preference: {content[:300]}",
                            category="preferences",
                            importance=2.5,
                            metadata={
                                "type": "preference",
                                "thread_id": state.get("thread_id")
                            }
                        )
                        if memory_id:
                            stored_ids.append(memory_id)
            
            return stored_ids
            
        except Exception as e:
            logger.error(f"Error extracting and storing facts: {e}")
            return []
    
    def build_memory_context(
        self,
        memories: List[Dict[str, Any]],
        max_tokens: int = 500
    ) -> str:
        """Build a context string from memories"""
        if not memories:
            return ""
        
        context_parts = ["Relevant memories from past interactions:"]
        token_count = 0
        
        for memory in memories:
            memory_text = f"- {memory['content']} (importance: {memory['importance']:.1f})"
            
            # Rough token estimation (1 token ≈ 4 chars)
            estimated_tokens = len(memory_text) // 4
            
            if token_count + estimated_tokens > max_tokens:
                break
            
            context_parts.append(memory_text)
            token_count += estimated_tokens
        
        return "\n".join(context_parts)
    
    async def update_memory_importance(
        self,
        memory_id: int,
        importance_delta: float
    ):
        """Update memory importance based on usage"""
        try:
            if not self._memory_enabled:
                return
            
            manager = await self._get_memory_manager()
            
            # Get current importance
            query = "SELECT importance_score FROM memories WHERE id = $1"
            result = await manager._execute_one(query, memory_id)
            
            if result:
                new_importance = min(10.0, result['importance_score'] + importance_delta)
                await manager.update_memory_importance(memory_id, new_importance)
                
        except Exception as e:
            logger.error(f"Error updating memory importance: {e}")
    
    async def get_user_context(
        self,
        user_id: str,
        include_preferences: bool = True,
        include_history: bool = True,
        include_problems: bool = False
    ) -> Dict[str, Any]:
        """Get comprehensive user context from memories"""
        try:
            if not self._memory_enabled:
                return {}
            
            manager = await self._get_memory_manager()
            context = {}
            
            if include_preferences:
                # Get user preferences
                preferences = await manager.get_memories_by_category(
                    user_id=user_id,
                    category="preferences",
                    limit=10
                )
                context["preferences"] = [
                    {
                        "content": mem.content,
                        "importance": mem.importance_score
                    }
                    for mem in preferences
                ]
            
            if include_history:
                # Get recent interactions
                recent_query = """
                SELECT content, category, importance_score 
                FROM memories 
                WHERE user_id = $1 
                ORDER BY last_accessed_at DESC 
                LIMIT 20
                """
                recent_results = await manager._execute_query(recent_query, user_id)
                context["recent_interactions"] = [
                    {
                        "content": row['content'],
                        "category": row['category'],
                        "importance": float(row['importance_score'])
                    }
                    for row in recent_results
                ]
            
            if include_problems:
                # Get past problems and solutions
                problems = await manager.get_memories_by_category(
                    user_id=user_id,
                    category="problems",
                    limit=5
                )
                solutions = await manager.get_memories_by_category(
                    user_id=user_id,
                    category="solutions",
                    limit=5
                )
                
                context["problems"] = [
                    {"content": mem.content, "importance": mem.importance_score}
                    for mem in problems
                ]
                context["solutions"] = [
                    {"content": mem.content, "importance": mem.importance_score}
                    for mem in solutions
                ]
            
            # Get memory statistics
            stats = await manager.get_user_memory_stats(user_id)
            context["stats"] = stats
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {}
    
    async def consolidate_memories(
        self,
        user_id: str,
        category: str,
        max_age_days: int = 30
    ) -> str:
        """Consolidate old memories into a summary"""
        try:
            if not self._memory_enabled:
                return ""
            
            from datetime import timedelta
            
            manager = await self._get_memory_manager()
            
            # Get old memories in category
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            
            query = """
            SELECT content, importance_score 
            FROM memories 
            WHERE user_id = $1 AND category = $2 AND created_at < $3
            ORDER BY importance_score DESC
            LIMIT 50
            """
            
            results = await manager._execute_query(query, user_id, category, cutoff_date)
            
            if not results:
                return ""
            
            # Create summary
            summary_parts = [f"Summary of {category} memories:"]
            for row in results[:10]:  # Top 10 by importance
                summary_parts.append(f"- {row['content'][:100]}")
            
            summary = "\n".join(summary_parts)
            
            # Store summary as new memory
            await self.store_interaction_memory(
                user_id=user_id,
                content=summary,
                category=f"{category}_summary",
                importance=5.0,
                metadata={
                    "type": "consolidation",
                    "original_count": len(results),
                    "consolidation_date": datetime.utcnow().isoformat()
                }
            )
            
            # Delete old memories (optional, based on policy)
            # await manager.cleanup_old_memories(days_old=max_age_days)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error consolidating memories: {e}")
            return ""
    
    def _clean_cache(self):
        """Clean old entries from memory cache"""
        try:
            current_time = datetime.utcnow()
            keys_to_delete = []
            
            for key, (_, timestamp) in self._memory_cache.items():
                # Remove entries older than 10 minutes
                if (current_time - timestamp).seconds > 600:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self._memory_cache[key]
                
        except Exception as e:
            logger.error(f"Error cleaning cache: {e}")
    
    async def search_similar_interactions(
        self,
        user_id: str,
        current_query: str,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """Search for similar past interactions"""
        try:
            if not self._memory_enabled:
                return []
            
            # Search for similar queries in interaction history
            memories = await self.get_relevant_memories(
                query=current_query,
                user_id=user_id,
                limit=limit,
                category="interactions",
                similarity_threshold=0.8
            )
            
            return memories
            
        except Exception as e:
            logger.error(f"Error searching similar interactions: {e}")
            return []
    
    def format_memory_for_prompt(
        self,
        memories: List[Dict[str, Any]],
        format_type: str = "bullet"
    ) -> str:
        """Format memories for inclusion in prompts"""
        if not memories:
            return ""
        
        if format_type == "bullet":
            lines = ["Relevant context from memory:"]
            for mem in memories:
                lines.append(f"• {mem['content']}")
            return "\n".join(lines)
            
        elif format_type == "numbered":
            lines = ["Relevant context from memory:"]
            for i, mem in enumerate(memories, 1):
                lines.append(f"{i}. {mem['content']}")
            return "\n".join(lines)
            
        elif format_type == "detailed":
            lines = ["Relevant context from memory:"]
            for mem in memories:
                lines.append(f"[{mem.get('category', 'general')} - importance: {mem.get('importance', 1.0):.1f}]")
                lines.append(f"  {mem['content']}")
                lines.append("")
            return "\n".join(lines)
            
        else:
            return " ".join([mem['content'] for mem in memories])