"""PostgreSQL-based Memory Manager with pgvector similarity search"""

import os
import asyncio
import hashlib
import logging
import time
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import asyncpg
from asyncpg.pool import Pool
import json
import re
from difflib import SequenceMatcher

from .embedding_service import get_embedding_service, EmbeddingResult

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
    access_count: int = 0
    last_accessed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.last_accessed_at is None:
            self.last_accessed_at = datetime.utcnow()
        if self.created_at is None:
            self.created_at = datetime.utcnow()

@dataclass
class PromptFragment:
    """Prompt fragment for context assembly"""
    id: Optional[int] = None
    category: str = ""
    priority: int = 0
    content: str = ""
    tags: List[str] = None
    embedding: Optional[List[float]] = None
    agent_type: Optional[str] = None
    context_tier: str = "standard"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()

@dataclass
class SearchResult:
    """Memory search result with similarity score"""
    memory: Memory
    similarity_score: float
    rank: int

class MemoryDeduplicator:
    """4-layer deduplication system"""
    
    def __init__(self, embedding_service):
        self.embedding_service = embedding_service
    
    def get_content_hash(self, content: str) -> str:
        """Exact content hash"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def fuzzy_similarity(self, text1: str, text2: str) -> float:
        """Fuzzy string similarity"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def extract_key_phrases(self, content: str) -> set:
        """Extract key phrases for deduplication"""
        # Simple key phrase extraction
        words = re.findall(r'\b\w{4,}\b', content.lower())
        return set(words)
    
    def key_phrase_similarity(self, content1: str, content2: str) -> float:
        """Key phrase based similarity"""
        phrases1 = self.extract_key_phrases(content1)
        phrases2 = self.extract_key_phrases(content2)
        
        if not phrases1 or not phrases2:
            return 0.0
        
        intersection = phrases1.intersection(phrases2)
        union = phrases1.union(phrases2)
        
        return len(intersection) / len(union) if union else 0.0
    
    async def semantic_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Semantic similarity using embeddings"""
        return self.embedding_service.cosine_similarity(embedding1, embedding2)

class PostgresMemoryManager:
    """PostgreSQL-based memory manager with pgvector similarity search"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.pool: Optional[Pool] = None
        self.embedding_service = get_embedding_service()
        self.deduplicator = MemoryDeduplicator(self.embedding_service)
        
        # Deduplication thresholds
        self.exact_threshold = 1.0
        self.fuzzy_threshold = 0.95
        self.key_phrase_threshold = 0.8
        self.semantic_threshold = 0.85
        
        # Performance tracking
        self.query_times = []
        self.connection_errors = 0
        
        # Concurrency control - limit concurrent DB operations
        self._db_semaphore = asyncio.Semaphore(5)  # Max 5 concurrent DB operations
    
    async def _init_connection(self, conn):
        """Initialize each new connection in the pool"""
        # Set statement timeout to prevent long-running queries
        await conn.execute("SET statement_timeout = '30s'")
        # Set lock timeout to prevent long waits
        await conn.execute("SET lock_timeout = '10s'")
        # Set idle transaction timeout
        await conn.execute("SET idle_in_transaction_session_timeout = '60s'")
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=10,  # Increased minimum connections
                max_size=30,  # Increased max connections
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=60,
                connection_class=asyncpg.Connection,
                init=self._init_connection,  # Initialize each connection
                server_settings={
                    'application_name': 'espressobot_memory',
                    'jit': 'off'  # Disable JIT for consistent performance
                }
            )
            logger.info("Memory manager database pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Memory manager database pool closed")
    
    async def _execute_query(self, query: str, *args) -> Any:
        """Execute query with error handling and timing"""
        async with self._db_semaphore:  # Limit concurrent DB operations
            start_time = time.time()
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    async with self.pool.acquire() as conn:
                        result = await conn.fetch(query, *args)
                        duration = (time.time() - start_time) * 1000
                        self.query_times.append(duration)
                        return result
                except (asyncpg.exceptions.ConnectionDoesNotExistError, 
                        asyncpg.exceptions.InterfaceError) as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self.connection_errors += 1
                        logger.error(f"Database query failed after {max_retries} retries: {e}")
                        raise
                    await asyncio.sleep(0.1 * retry_count)  # Exponential backoff
                    logger.warning(f"Retrying query due to connection error (attempt {retry_count}/{max_retries})")
                except asyncpg.exceptions.InternalClientError as e:
                    # Handle "another operation is in progress" errors
                    if "another operation is in progress" in str(e):
                        retry_count += 1
                        if retry_count >= max_retries:
                            logger.error(f"Database query failed - connection busy: {e}")
                            raise
                        await asyncio.sleep(0.2 * retry_count)  # Longer wait for busy connections
                        logger.warning(f"Connection busy, retrying (attempt {retry_count}/{max_retries})")
                    else:
                        logger.error(f"Database query failed: {e}")
                        raise
                except Exception as e:
                    self.connection_errors += 1
                    logger.error(f"Database query failed: {e}")
                    raise
    
    async def _execute_one(self, query: str, *args) -> Any:
        """Execute query expecting single result"""
        async with self._db_semaphore:  # Limit concurrent DB operations
            start_time = time.time()
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    async with self.pool.acquire() as conn:
                        result = await conn.fetchrow(query, *args)
                        duration = (time.time() - start_time) * 1000
                        self.query_times.append(duration)
                        return result
                except asyncpg.exceptions.ConnectionDoesNotExistError as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self.connection_errors += 1
                        logger.error(f"Database query failed after {max_retries} retries: {e}")
                        raise
                    await asyncio.sleep(0.1 * retry_count)
                    logger.warning(f"Retrying query due to connection error (attempt {retry_count}/{max_retries})")
                except Exception as e:
                    self.connection_errors += 1
                    logger.error(f"Database query failed: {e}")
                    raise
    
    async def _execute_command(self, query: str, *args) -> Any:
        """Execute command (INSERT, UPDATE, DELETE)"""
        async with self._db_semaphore:  # Limit concurrent DB operations
            start_time = time.time()
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries:
                try:
                    async with self.pool.acquire() as conn:
                        result = await conn.execute(query, *args)
                        duration = (time.time() - start_time) * 1000
                        self.query_times.append(duration)
                        return result
                except asyncpg.exceptions.ConnectionDoesNotExistError:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self.connection_errors += 1
                        logger.error(f"Database command failed after {max_retries} retries: connection lost")
                        raise
                    await asyncio.sleep(0.1 * retry_count)  # Exponential backoff
                except Exception as e:
                    self.connection_errors += 1
                    logger.error(f"Database command failed: {str(e)[:200]}")
                    raise
    
    async def check_duplicates(self, user_id: str, content: str, embedding: List[float]) -> Optional[int]:
        """Check for duplicates using 4-layer approach"""
        
        # Layer 1: Exact hash match
        content_hash = self.deduplicator.get_content_hash(content)
        
        duplicate_query = """
        SELECT original_id FROM memory_duplicates 
        WHERE duplicate_hash = $1
        """
        
        result = await self._execute_one(duplicate_query, content_hash)
        if result:
            logger.debug(f"Exact duplicate found for hash {content_hash[:8]}")
            return result['original_id']
        
        # Layer 2-4: Check existing memories for this user
        existing_memories_query = """
        SELECT id, content, embedding FROM memories 
        WHERE user_id = $1 
        ORDER BY created_at DESC 
        LIMIT 100
        """
        
        existing_memories = await self._execute_query(existing_memories_query, user_id)
        
        for existing in existing_memories:
            existing_content = existing['content']
            existing_embedding = existing['embedding']
            
            # Layer 2: Fuzzy similarity
            fuzzy_score = self.deduplicator.fuzzy_similarity(content, existing_content)
            if fuzzy_score >= self.fuzzy_threshold:
                await self._record_duplicate(existing['id'], content_hash, fuzzy_score, 'fuzzy')
                logger.debug(f"Fuzzy duplicate found with score {fuzzy_score}")
                return existing['id']
            
            # Layer 3: Key phrase similarity
            key_phrase_score = self.deduplicator.key_phrase_similarity(content, existing_content)
            if key_phrase_score >= self.key_phrase_threshold:
                await self._record_duplicate(existing['id'], content_hash, key_phrase_score, 'key_phrase')
                logger.debug(f"Key phrase duplicate found with score {key_phrase_score}")
                return existing['id']
            
            # Layer 4: Semantic similarity
            if existing_embedding and embedding:
                try:
                    # Deserialize embedding from JSON if it's a string
                    if isinstance(existing_embedding, str):
                        existing_embedding = json.loads(existing_embedding)
                    semantic_score = await self.deduplicator.semantic_similarity(embedding, existing_embedding)
                    if semantic_score >= self.semantic_threshold:
                        await self._record_duplicate(existing['id'], content_hash, semantic_score, 'semantic')
                        logger.debug(f"Semantic duplicate found with score {semantic_score}")
                        return existing['id']
                except (json.JSONDecodeError, ValueError) as e:
                    logger.debug(f"Could not parse embedding for deduplication: {str(e)[:100]}")
                except Exception as e:
                    logger.debug(f"Semantic similarity check failed: {str(e)[:100]}")
        
        return None
    
    async def _record_duplicate(self, original_id: int, duplicate_hash: str, 
                              similarity_score: float, dedup_type: str):
        """Record duplicate detection"""
        query = """
        INSERT INTO memory_duplicates (original_id, duplicate_hash, similarity_score, dedup_type)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT DO NOTHING
        """
        await self._execute_command(query, original_id, duplicate_hash, similarity_score, dedup_type)
    
    async def store_memory(self, memory: Memory) -> int:
        """Store memory with deduplication"""
        
        # Generate embedding if not provided
        if not memory.embedding:
            embedding_result = await self.embedding_service.get_embedding(memory.content)
            memory.embedding = embedding_result.embedding
        
        # Check for duplicates
        duplicate_id = await self.check_duplicates(memory.user_id, memory.content, memory.embedding)
        if duplicate_id:
            # Update access count and return existing ID
            await self._update_memory_access(duplicate_id)
            logger.info(f"🔄 Memory deduplicated (existing ID: {duplicate_id}): '{memory.content[:60]}...'")
            return duplicate_id
        
        # Store new memory
        query = """
        INSERT INTO memories (user_id, content, embedding, metadata, category, 
                             importance_score, access_count, last_accessed_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        RETURNING id
        """
        
        result = await self._execute_one(
            query,
            memory.user_id,
            memory.content,
            json.dumps(memory.embedding) if memory.embedding else None,  # Serialize embedding as JSON
            json.dumps(memory.metadata),
            memory.category,
            memory.importance_score,
            memory.access_count,
            memory.last_accessed_at
        )
        
        memory_id = result['id']
        logger.info(f"✅ Stored new memory {memory_id}: '{memory.content[:60]}...' (category: {memory.category}, user: {memory.user_id})")
        return memory_id
    
    async def _update_memory_access(self, memory_id: int):
        """Update memory access statistics"""
        query = """
        UPDATE memories 
        SET access_count = access_count + 1, last_accessed_at = CURRENT_TIMESTAMP
        WHERE id = $1
        """
        await self._execute_command(query, memory_id)
    
    async def search_memories(self, user_id: str, query: str, limit: int = 10,
                            similarity_threshold: float = 0.7,
                            include_metadata: bool = True) -> List[SearchResult]:
        """Search memories using semantic similarity or fallback to text search"""
        
        start_time = time.time()
        
        # Generate embedding for the query
        try:
            embedding_result = await self.embedding_service.get_embedding(query)
            query_embedding = embedding_result.embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding for search: {e}")
            # Fallback to text search
            search_query = """
            SELECT id, user_id, content, metadata, category, importance_score,
                   access_count, last_accessed_at, created_at, updated_at,
                   embedding,
                   1.0 as similarity
            FROM memories 
            WHERE user_id = $1 
              AND (content ILIKE $2 OR category ILIKE $2)
            ORDER BY importance_score DESC, created_at DESC
            LIMIT $3
            """
            
            search_pattern = f'%{query}%'
            results = await self._execute_query(
                search_query, user_id, search_pattern, limit
            )
        else:
            # Use vector similarity search with pgvector
            search_query = """
            SELECT id, user_id, content, metadata, category, importance_score,
                   access_count, last_accessed_at, created_at, updated_at,
                   embedding,
                   1 - (embedding <=> $2::vector) as similarity
            FROM memories 
            WHERE user_id = $1 
              AND 1 - (embedding <=> $2::vector) >= $3
            ORDER BY similarity DESC, importance_score DESC
            LIMIT $4
            """
            
            results = await self._execute_query(
                search_query, user_id, str(query_embedding), similarity_threshold, limit
            )
        
        # Convert to SearchResult objects
        search_results = []
        for i, row in enumerate(results):
            memory = Memory(
                id=row['id'],
                user_id=row['user_id'],
                content=row['content'],
                metadata=json.loads(row['metadata']) if include_metadata else {},
                category=row['category'],
                importance_score=row['importance_score'],
                access_count=row['access_count'],
                last_accessed_at=row['last_accessed_at'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            
            search_results.append(SearchResult(
                memory=memory,
                similarity_score=row['similarity'],
                rank=i + 1
            ))
            
            # Update access count
            await self._update_memory_access(row['id'])
        
        # Record analytics
        duration = (time.time() - start_time) * 1000
        await self._record_search_analytics(user_id, query, len(search_results), duration)
        
        return search_results
    
    async def _record_search_analytics(self, user_id: str, query: str, 
                                     results_count: int, response_time_ms: float):
        """Record search analytics"""
        query_analytics = """
        INSERT INTO memory_analytics (user_id, query_text, results_count, response_time_ms)
        VALUES ($1, $2, $3, $4)
        """
        try:
            await self._execute_command(query_analytics, user_id, query[:500], 
                                      results_count, int(response_time_ms))
        except Exception as e:
            logger.error(f"Failed to record analytics: {e}")
    
    async def get_memories_by_category(self, user_id: str, category: str,
                                     limit: int = 50) -> List[Memory]:
        """Get memories by category"""
        query = """
        SELECT id, user_id, content, metadata, category, importance_score,
               access_count, last_accessed_at, created_at, updated_at
        FROM memories 
        WHERE user_id = $1 AND category = $2
        ORDER BY importance_score DESC, created_at DESC
        LIMIT $3
        """
        
        results = await self._execute_query(query, user_id, category, limit)
        
        memories = []
        for row in results:
            memory = Memory(
                id=row['id'],
                user_id=row['user_id'],
                content=row['content'],
                metadata=json.loads(row['metadata']),
                category=row['category'],
                importance_score=row['importance_score'],
                access_count=row['access_count'],
                last_accessed_at=row['last_accessed_at'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            memories.append(memory)
        
        return memories
    
    async def delete_memory(self, memory_id: int, user_id: str) -> bool:
        """Delete memory and related duplicates"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Delete duplicates first
                await conn.execute(
                    "DELETE FROM memory_duplicates WHERE original_id = $1",
                    memory_id
                )
                
                # Delete memory
                result = await conn.execute(
                    "DELETE FROM memories WHERE id = $1 AND user_id = $2",
                    memory_id, user_id
                )
                
                return "DELETE 1" in str(result)
    
    async def update_memory_importance(self, memory_id: int, importance_score: float) -> bool:
        """Update memory importance score"""
        query = """
        UPDATE memories 
        SET importance_score = $2, updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        """
        result = await self._execute_command(query, memory_id, importance_score)
        return "UPDATE 1" in str(result)
    
    async def get_user_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for user"""
        stats_query = """
        SELECT 
            COUNT(*) as total_memories,
            COUNT(DISTINCT category) as categories,
            AVG(importance_score) as avg_importance,
            SUM(access_count) as total_accesses,
            MAX(created_at) as latest_memory
        FROM memories 
        WHERE user_id = $1
        """
        
        result = await self._execute_one(stats_query, user_id)
        
        return {
            "total_memories": result['total_memories'],
            "categories": result['categories'],
            "avg_importance": float(result['avg_importance']) if result['avg_importance'] else 0.0,
            "total_accesses": result['total_accesses'],
            "latest_memory": result['latest_memory']
        }
    
    async def cleanup_old_memories(self, days_old: int = 90, 
                                 min_access_count: int = 1) -> int:
        """Clean up old, unused memories"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        
        cleanup_query = """
        DELETE FROM memories 
        WHERE created_at < $1 AND access_count < $2
        """
        
        result = await self._execute_command(cleanup_query, cutoff_date, min_access_count)
        deleted_count = int(result.split()[-1]) if result else 0
        
        logger.info(f"Cleaned up {deleted_count} old memories")
        return deleted_count
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_query_time = sum(self.query_times) / len(self.query_times) if self.query_times else 0
        
        return {
            "avg_query_time_ms": round(avg_query_time, 2),
            "total_queries": len(self.query_times),
            "connection_errors": self.connection_errors,
            "embedding_cache_stats": self.embedding_service.get_cache_stats()
        }