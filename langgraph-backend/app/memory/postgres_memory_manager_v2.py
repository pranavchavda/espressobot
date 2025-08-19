"""
Simplified PostgreSQL Memory Manager v2
Uses simple connections instead of pools to avoid connection issues
"""

import os
import asyncio
import hashlib
import logging
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import json

from app.db.connection_pool import get_database_pool
from .embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """Memory record structure"""
    id: Optional[int] = None
    user_id: str = ""
    content: str = ""
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = None
    category: Optional[str] = None
    importance_score: float = 1.0
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class SearchResult:
    """Memory search result with similarity score"""
    memory: Memory
    similarity_score: float
    rank: int


class SimpleMemoryManager:
    """Simplified memory manager with robust connection handling"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        """Ensure singleton instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if hasattr(self, '_initialized'):
            return
            
        self.db = get_database_pool()
        self.embedding_service = get_embedding_service()
        
        # Performance tracking
        self.query_times = []
        self.connection_errors = 0
        
        # Simple concurrency control
        self._semaphore = asyncio.Semaphore(3)
        self._initialized = True
        
        logger.info("Simple memory manager initialized")
    
    async def initialize(self):
        """Compatibility method"""
        pass
    
    async def close(self):
        """Compatibility method"""
        pass
    
    async def store_memory(self, memory: Memory) -> Optional[int]:
        """Store a memory with deduplication"""
        async with self._semaphore:
            try:
                # Generate embedding if not provided
                if not memory.embedding:
                    embedding_result = await self.embedding_service.get_embedding(memory.content)
                    memory.embedding = embedding_result.embedding
                
                # Check for duplicates based on content similarity
                existing = await self.db.fetchrow(
                    """
                    SELECT id FROM memories 
                    WHERE user_id = $1 
                    AND content = $2
                    AND status = 'active'
                    LIMIT 1
                    """,
                    memory.user_id,
                    memory.content
                )
                
                if existing:
                    logger.debug(f"Memory already exists: {memory.content[:50]}...")
                    return existing['id']
                
                # Insert new memory
                result = await self.db.fetchrow(
                    """
                    INSERT INTO memories (
                        user_id, content, embedding, metadata, category,
                        importance_score, confidence_score, created_at, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'active')
                    RETURNING id
                    """,
                    memory.user_id,
                    memory.content,
                    json.dumps(memory.embedding) if memory.embedding else None,
                    json.dumps(memory.metadata) if memory.metadata else '{}',
                    memory.category or 'general',
                    memory.importance_score,
                    memory.metadata.get('confidence', 0.5) if memory.metadata else 0.5,
                    memory.created_at
                )
                
                if result:
                    logger.info(f"Stored memory {result['id']}: {memory.content[:50]}...")
                    return result['id']
                    
            except Exception as e:
                logger.error(f"Failed to store memory: {e}")
                self.connection_errors += 1
                
        return None
    
    async def search_memories(
        self, 
        user_id: str,
        query: str,
        limit: int = 10,
        category: Optional[str] = None,
        similarity_threshold: float = 0.0
    ) -> List[SearchResult]:
        """Search memories by semantic similarity"""
        async with self._semaphore:
            try:
                # Generate query embedding
                embedding_result = await self.embedding_service.get_embedding(query)
                query_embedding = embedding_result.embedding
                
                # Build query
                sql = """
                    SELECT 
                        id, user_id, content, metadata, category, 
                        importance_score, created_at,
                        1 - (embedding <=> $2::vector) as similarity
                    FROM memories
                    WHERE user_id = $1
                    AND status = 'active'
                """
                
                params = [user_id, json.dumps(query_embedding)]
                
                if category:
                    sql += " AND category = $3"
                    params.append(category)
                
                sql += """
                    ORDER BY similarity DESC, importance_score DESC
                    LIMIT ${}
                """.format(len(params) + 1)
                params.append(limit)
                
                rows = await self.db.fetch(sql, *params)
                
                results = []
                for i, row in enumerate(rows):
                    # Skip results below similarity threshold
                    if row['similarity'] < similarity_threshold:
                        continue
                        
                    memory = Memory(
                        id=row['id'],
                        user_id=row['user_id'],
                        content=row['content'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else {},
                        category=row['category'],
                        importance_score=row['importance_score'],
                        created_at=row['created_at']
                    )
                    
                    results.append(SearchResult(
                        memory=memory,
                        similarity_score=row['similarity'],
                        rank=i + 1
                    ))
                
                return results
                
            except Exception as e:
                logger.error(f"Failed to search memories: {e}")
                self.connection_errors += 1
                return []
    
    async def get_user_memories(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Memory]:
        """Get all memories for a user"""
        async with self._semaphore:
            try:
                rows = await self.db.fetch(
                    """
                    SELECT id, user_id, content, metadata, category, 
                           importance_score, created_at
                    FROM memories
                    WHERE user_id = $1 AND status = 'active'
                    ORDER BY created_at DESC
                    LIMIT $2 OFFSET $3
                    """,
                    user_id, limit, offset
                )
                
                memories = []
                for row in rows:
                    memories.append(Memory(
                        id=row['id'],
                        user_id=row['user_id'],
                        content=row['content'],
                        metadata=json.loads(row['metadata']) if row['metadata'] else {},
                        category=row['category'],
                        importance_score=row['importance_score'],
                        created_at=row['created_at']
                    ))
                
                return memories
                
            except Exception as e:
                logger.error(f"Failed to get user memories: {e}")
                return []
    
    async def delete_memory(self, memory_id: int, user_id: str) -> bool:
        """Delete a memory (soft delete)"""
        async with self._semaphore:
            try:
                result = await self.db.execute(
                    """
                    UPDATE memories 
                    SET status = 'deleted', updated_at = $3
                    WHERE id = $1 AND user_id = $2 AND status = 'active'
                    """,
                    memory_id, user_id, datetime.utcnow()
                )
                
                return "UPDATE" in result
                
            except Exception as e:
                logger.error(f"Failed to delete memory: {e}")
                return False
    
    async def get_user_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for a user"""
        async with self._semaphore:
            try:
                # Get total count
                total = await self.db.fetchval(
                    "SELECT COUNT(*) FROM memories WHERE user_id = $1 AND status = 'active'",
                    user_id
                )
                
                # Get category breakdown
                categories = await self.db.fetch(
                    """
                    SELECT category, COUNT(*) as count 
                    FROM memories 
                    WHERE user_id = $1 AND status = 'active'
                    GROUP BY category
                    """,
                    user_id
                )
                
                category_stats = {row['category']: row['count'] for row in categories}
                
                return {
                    "total_memories": total or 0,
                    "categories": len(category_stats),  # Return count, not the object
                    "category_breakdown": category_stats,  # Keep the full breakdown as separate field
                    "connection_errors": self.connection_errors
                }
                
            except Exception as e:
                logger.error(f"Failed to get memory stats: {e}")
                return {
                    "total_memories": 0,
                    "categories": 0,  # Return count, not the object
                    "category_breakdown": {},  # Keep the full breakdown as separate field  
                    "connection_errors": self.connection_errors
                }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        if self.query_times:
            avg_time = sum(self.query_times) / len(self.query_times)
            max_time = max(self.query_times)
            min_time = min(self.query_times)
        else:
            avg_time = max_time = min_time = 0
        
        return {
            "avg_query_time_ms": round(avg_time, 2),
            "max_query_time_ms": round(max_time, 2),
            "min_query_time_ms": round(min_time, 2),
            "total_queries": len(self.query_times),
            "connection_errors": self.connection_errors
        }
    
    async def _execute_query(self, query: str, *params) -> List[Dict]:
        """Execute a query and return results as list of dicts"""
        async with self._semaphore:
            try:
                start_time = time.time()
                rows = await self.db.fetch(query, *params)
                query_time = (time.time() - start_time) * 1000
                self.query_times.append(query_time)
                
                # Convert asyncpg records to dicts
                results = []
                for row in rows:
                    results.append(dict(row))
                
                return results
                
            except Exception as e:
                logger.error(f"Failed to execute query: {e}")
                self.connection_errors += 1
                return []
    
    async def _execute_command(self, query: str, *params) -> str:
        """Execute a command (INSERT/UPDATE/DELETE) and return status"""
        async with self._semaphore:
            try:
                start_time = time.time()
                result = await self.db.execute(query, *params)
                query_time = (time.time() - start_time) * 1000
                self.query_times.append(query_time)
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to execute command: {e}")
                self.connection_errors += 1
                return ""
    
    async def _execute_one(self, query: str, *params) -> Dict:
        """Execute a query and return first result as dict"""
        async with self._semaphore:
            try:
                start_time = time.time()
                row = await self.db.fetchrow(query, *params)
                query_time = (time.time() - start_time) * 1000
                self.query_times.append(query_time)
                
                if row:
                    return dict(row)
                else:
                    return {}
                
            except Exception as e:
                logger.error(f"Failed to execute query: {e}")
                self.connection_errors += 1
                return {}
    
    async def _update_memory_access(self, memory_id: int):
        """Update memory access count and last_accessed_at"""
        async with self._semaphore:
            try:
                await self.db.execute(
                    """
                    UPDATE memories 
                    SET access_count = access_count + 1, 
                        last_accessed_at = $2,
                        updated_at = $2
                    WHERE id = $1 AND status = 'active'
                    """,
                    memory_id, datetime.utcnow()
                )
            except Exception as e:
                logger.error(f"Failed to update memory access: {e}")