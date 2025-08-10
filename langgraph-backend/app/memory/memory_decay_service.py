"""Memory Decay and Feedback Service

Handles:
- Memory usage tracking
- Usefulness score updates
- Decay calculations
- Feedback loop implementation
"""

import logging
import asyncio
import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from .postgres_memory_manager import PostgresMemoryManager, Memory

logger = logging.getLogger(__name__)

class MemoryDecayService:
    """Service for managing memory decay and feedback"""
    
    def __init__(self, memory_manager: PostgresMemoryManager):
        self.memory_manager = memory_manager
        
        # Configuration
        self.base_decay_rate = 0.01
        self.category_decay_rates = {
            "preferences": 0.005,   # Slow decay - preferences last long
            "facts": 0.008,        # Slow decay - facts remain true
            "expertise": 0.008,    # Slow decay - expertise is stable
            "relationships": 0.010, # Medium decay
            "solutions": 0.012,    # Medium decay - solutions may become outdated
            "problems": 0.015,     # Medium decay - problems may be solved
            "interactions": 0.020, # Fast decay - interactions are temporal
            "general": 0.015      # Default medium decay
        }
        
        self.usefulness_increment = 0.1
        self.usefulness_decrement = 0.05
        self.archive_threshold = 0.1
        
    async def track_memory_usage(self,
                                conversation_id: str,
                                memories_provided: List[Memory],
                                agent_response: str,
                                user_message: str = None) -> Dict[str, Any]:
        """Track which memories were useful in a conversation"""
        
        used_memories = []
        unused_memories = []
        
        for memory in memories_provided:
            # Increment access count
            await self._increment_access_count(memory.id, conversation_id)
            
            # Check if memory influenced the response
            was_used = await self._detect_memory_usage(memory, agent_response, user_message)
            
            if was_used:
                used_memories.append(memory)
                # Increase usefulness score
                await self._update_usefulness_score(memory.id, increment=True)
                logger.info(f"📈 Memory {memory.id} was useful: '{memory.content[:50]}...'")
            else:
                unused_memories.append(memory)
                # Slightly decrease usefulness score
                await self._update_usefulness_score(memory.id, increment=False)
                logger.debug(f"📉 Memory {memory.id} was not used: '{memory.content[:50]}...'")
        
        # Return analytics
        return {
            "conversation_id": conversation_id,
            "total_memories_provided": len(memories_provided),
            "memories_used": len(used_memories),
            "memories_unused": len(unused_memories),
            "usage_rate": len(used_memories) / len(memories_provided) if memories_provided else 0,
            "used_memory_ids": [m.id for m in used_memories],
            "unused_memory_ids": [m.id for m in unused_memories]
        }
    
    async def _detect_memory_usage(self, 
                                  memory: Memory, 
                                  response: str,
                                  user_message: str = None) -> bool:
        """Detect if a memory influenced the response using heuristics"""
        
        # Simple heuristic checks
        memory_keywords = set(memory.content.lower().split())
        response_lower = response.lower()
        
        # Check for direct content overlap
        keyword_matches = sum(1 for keyword in memory_keywords 
                             if len(keyword) > 4 and keyword in response_lower)
        
        # If significant overlap, likely used
        if keyword_matches >= 2:
            return True
        
        # Check for category-specific patterns
        if memory.category == "preferences":
            # Check if response respects the preference
            preference_indicators = ["as you prefer", "based on your preference", 
                                    "since you like", "given your preference"]
            if any(indicator in response_lower for indicator in preference_indicators):
                return True
        
        elif memory.category == "facts":
            # Check if facts are referenced
            fact_indicators = ["you mentioned", "you said", "you work", 
                              "your team", "your company"]
            if any(indicator in response_lower for indicator in fact_indicators):
                return True
        
        elif memory.category == "expertise":
            # Check if expertise level influenced response complexity
            if "experienced" in memory.content.lower():
                # Advanced explanations for experts
                if any(term in response_lower for term in ["advanced", "complex", "detailed"]):
                    return True
            elif "new to" in memory.content.lower() or "beginner" in memory.content.lower():
                # Simple explanations for beginners
                if any(term in response_lower for term in ["basic", "simple", "let me explain"]):
                    return True
        
        return False
    
    async def _increment_access_count(self, memory_id: str, conversation_id: str):
        """Increment memory access count and update last accessed time"""
        
        query = """
        UPDATE memories 
        SET 
            access_count = access_count + 1,
            last_accessed_at = NOW(),
            used_in_conversations = 
                CASE 
                    WHEN used_in_conversations IS NULL OR used_in_conversations = '[]' THEN 
                        $2::text
                    ELSE 
                        (used_in_conversations::jsonb || to_jsonb($3))::text
                END
        WHERE id = $1
        """
        
        await self.memory_manager._execute_command(
            query, 
            memory_id, 
            json.dumps([conversation_id]),
            conversation_id
        )
    
    async def _update_usefulness_score(self, memory_id: str, increment: bool = True):
        """Update memory usefulness score"""
        
        change = self.usefulness_increment if increment else -self.usefulness_decrement
        
        query = """
        UPDATE memories 
        SET usefulness_score = GREATEST(0, LEAST(1, usefulness_score + $2))
        WHERE id = $1
        """
        
        await self.memory_manager._execute_command(query, memory_id, change)
    
    async def archive_old_memories(self) -> int:
        """Archive memories with low effective importance"""
        
        query = """
        WITH to_archive AS (
            SELECT id 
            FROM memories
            WHERE user_id IS NOT NULL
              AND status = 'active'
              AND (
                -- Very low effective importance
                calculate_effective_importance(
                    importance_score, created_at, decay_rate, 
                    access_count, usefulness_score
                ) < $1
                -- Never accessed and old
                OR (last_accessed_at IS NULL AND created_at < NOW() - INTERVAL '30 days')
                -- Not accessed recently
                OR (last_accessed_at < NOW() - INTERVAL '60 days')
                -- Ephemeral memories older than 7 days
                OR (is_ephemeral = true AND created_at < NOW() - INTERVAL '7 days')
              )
        )
        UPDATE memories 
        SET status = 'archived', updated_at = NOW()
        WHERE id IN (SELECT id FROM to_archive)
        RETURNING id
        """
        
        results = await self.memory_manager._execute_query(query, self.archive_threshold)
        archived_count = len(results)
        
        if archived_count > 0:
            logger.info(f"🗄️ Archived {archived_count} old/unused memories")
        
        return archived_count
    
    async def boost_verified_memories(self, memory_ids: List[str]):
        """Boost memories that have been verified as accurate/useful"""
        
        query = """
        UPDATE memories 
        SET 
            verification_status = 'verified',
            importance_score = LEAST(1.0, importance_score * 1.2),
            decay_rate = decay_rate * 0.8,  -- Slow down decay
            usefulness_score = LEAST(1.0, usefulness_score + 0.2)
        WHERE id = ANY($1)
        """
        
        await self.memory_manager._execute_command(query, memory_ids)
        logger.info(f"✅ Boosted {len(memory_ids)} verified memories")
    
    async def get_memory_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics about memory usage and health"""
        
        query = """
        SELECT 
            COUNT(*) FILTER (WHERE status = 'active') as active_count,
            COUNT(*) FILTER (WHERE status = 'archived') as archived_count,
            AVG(usefulness_score) FILTER (WHERE status = 'active') as avg_usefulness,
            AVG(access_count) FILTER (WHERE status = 'active') as avg_access_count,
            AVG(confidence_score) FILTER (WHERE status = 'active') as avg_confidence,
            COUNT(*) FILTER (WHERE is_ephemeral = true AND status = 'active') as ephemeral_count,
            COUNT(*) FILTER (WHERE verification_status = 'verified' AND status = 'active') as verified_count,
            MAX(last_accessed_at) as last_activity,
            json_agg(DISTINCT category) FILTER (WHERE category IS NOT NULL) as categories
        FROM memories
        WHERE user_id = $1
        """
        
        result = await self.memory_manager._execute_one(query, user_id)
        
        # Get top accessed memories
        top_memories_query = """
        SELECT id, content, category, access_count, usefulness_score,
               calculate_effective_importance(
                   importance_score, created_at, decay_rate, 
                   access_count, usefulness_score
               ) as effective_importance
        FROM memories
        WHERE user_id = $1 AND status = 'active'
        ORDER BY access_count DESC
        LIMIT 5
        """
        
        top_memories = await self.memory_manager._execute_query(top_memories_query, user_id)
        
        return {
            "user_id": user_id,
            "active_memories": result['active_count'] or 0,
            "archived_memories": result['archived_count'] or 0,
            "average_usefulness": float(result['avg_usefulness'] or 0),
            "average_access_count": float(result['avg_access_count'] or 0),
            "average_confidence": float(result['avg_confidence'] or 0),
            "ephemeral_count": result['ephemeral_count'] or 0,
            "verified_count": result['verified_count'] or 0,
            "last_activity": result['last_activity'].isoformat() if result['last_activity'] else None,
            "categories": result['categories'] or [],
            "top_accessed_memories": [
                {
                    "id": m['id'],
                    "content": m['content'][:100] + "..." if len(m['content']) > 100 else m['content'],
                    "category": m['category'],
                    "access_count": m['access_count'],
                    "usefulness_score": float(m['usefulness_score']),
                    "effective_importance": float(m['effective_importance'])
                }
                for m in top_memories
            ],
            "health_score": self._calculate_health_score(result)
        }
    
    def _calculate_health_score(self, stats: Dict) -> float:
        """Calculate overall memory system health score"""
        
        score = 0.0
        
        # Good usefulness average (40% weight)
        if stats['avg_usefulness']:
            score += float(stats['avg_usefulness']) * 0.4
        
        # Good confidence average (20% weight)
        if stats['avg_confidence']:
            score += float(stats['avg_confidence']) * 0.2
        
        # Low ephemeral ratio (20% weight)
        total = (stats['active_count'] or 0) + (stats['archived_count'] or 0)
        if total > 0:
            non_ephemeral_ratio = 1 - ((stats['ephemeral_count'] or 0) / total)
            score += non_ephemeral_ratio * 0.2
        
        # Good verification ratio (20% weight)
        if stats['active_count'] and stats['active_count'] > 0:
            verified_ratio = (stats['verified_count'] or 0) / stats['active_count']
            score += verified_ratio * 0.2
        
        return round(score, 2)

# Singleton instance
_decay_service_instance: Optional[MemoryDecayService] = None

def get_decay_service(memory_manager: PostgresMemoryManager) -> MemoryDecayService:
    """Get singleton decay service instance"""
    global _decay_service_instance
    if _decay_service_instance is None:
        _decay_service_instance = MemoryDecayService(memory_manager)
    return _decay_service_instance