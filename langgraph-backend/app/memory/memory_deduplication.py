"""
Memory Deduplication Service
Identifies and merges similar memories using vector similarity
"""

import asyncio
import logging
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass

from .postgres_memory_manager_v2 import Memory, SimpleMemoryManager, SearchResult
from .embedding_service import get_embedding_service

logger = logging.getLogger(__name__)

@dataclass
class DuplicateGroup:
    """Group of similar memories that should be merged"""
    primary_memory: Memory  # The best memory to keep
    duplicates: List[Memory]  # Memories to merge/remove
    similarity_scores: List[float]  # Similarity scores to primary
    merged_content: str  # Combined content if merging
    
class MemoryDeduplicationService:
    """Service for identifying and removing duplicate memories"""
    
    def __init__(self, similarity_threshold: float = 0.85):
        self.memory_manager = SimpleMemoryManager()
        self.embedding_service = get_embedding_service()
        self.similarity_threshold = similarity_threshold
        
    async def find_duplicate_groups(self, user_id: str, category: Optional[str] = None) -> List[DuplicateGroup]:
        """Find groups of similar memories for a user"""
        
        # Get all memories for the user
        if category:
            memories = await self._get_memories_by_category(user_id, category)
        else:
            memories = await self._get_all_user_memories(user_id)
        
        logger.info(f"Analyzing {len(memories)} memories for duplicates")
        
        # Group similar memories
        duplicate_groups = []
        processed_ids = set()
        
        for i, memory in enumerate(memories):
            if memory.id in processed_ids:
                continue
                
            # Find similar memories to this one
            similar_memories = []
            similarity_scores = []
            
            for j, other_memory in enumerate(memories[i+1:], i+1):
                if other_memory.id in processed_ids:
                    continue
                    
                if memory.category != other_memory.category:
                    continue  # Only dedupe within same category
                
                # Calculate similarity using embeddings
                similarity = await self._calculate_similarity(memory, other_memory)
                
                if similarity >= self.similarity_threshold:
                    similar_memories.append(other_memory)
                    similarity_scores.append(similarity)
                    logger.debug(f"Found similar memories (similarity: {similarity:.3f}):")
                    logger.debug(f"  Primary: '{memory.content[:50]}...'")
                    logger.debug(f"  Similar: '{other_memory.content[:50]}...'")
            
            # If we found similar memories, create a duplicate group
            if similar_memories:
                # Choose the best memory as primary (highest importance, then most recent)
                all_memories = [memory] + similar_memories
                primary = max(all_memories, key=lambda m: (m.importance_score, m.created_at))
                duplicates = [m for m in all_memories if m.id != primary.id]
                
                # Create merged content
                merged_content = await self._create_merged_content(primary, duplicates)
                
                group = DuplicateGroup(
                    primary_memory=primary,
                    duplicates=duplicates,
                    similarity_scores=similarity_scores,
                    merged_content=merged_content
                )
                duplicate_groups.append(group)
                
                # Mark all as processed
                for mem in all_memories:
                    processed_ids.add(mem.id)
            else:
                processed_ids.add(memory.id)
        
        logger.info(f"Found {len(duplicate_groups)} duplicate groups")
        return duplicate_groups
    
    async def deduplicate_memories(self, user_id: str, category: Optional[str] = None, 
                                 dry_run: bool = False) -> Dict[str, any]:
        """Deduplicate memories for a user"""
        
        duplicate_groups = await self.find_duplicate_groups(user_id, category)
        
        stats = {
            "groups_found": len(duplicate_groups),
            "memories_analyzed": 0,
            "memories_merged": 0,
            "memories_removed": 0,
            "dry_run": dry_run
        }
        
        for group in duplicate_groups:
            stats["memories_analyzed"] += len(group.duplicates) + 1
            
            if not dry_run:
                # Update primary memory with merged content
                if group.merged_content != group.primary_memory.content:
                    await self._update_memory_content(group.primary_memory.id, group.merged_content)
                    stats["memories_merged"] += 1
                
                # Remove duplicate memories
                for duplicate in group.duplicates:
                    await self._remove_memory(duplicate.id)
                    stats["memories_removed"] += 1
            else:
                # Dry run - just count what would happen
                if group.merged_content != group.primary_memory.content:
                    stats["memories_merged"] += 1
                stats["memories_removed"] += len(group.duplicates)
        
        logger.info(f"Deduplication complete: {stats}")
        return stats
    
    async def _calculate_similarity(self, memory1: Memory, memory2: Memory) -> float:
        """Calculate cosine similarity between two memories using their embeddings"""
        
        # Get embeddings if not already present
        if not memory1.embedding:
            embedding_result = await self.embedding_service.get_embedding(memory1.content)
            memory1.embedding = embedding_result.embedding
        
        if not memory2.embedding:
            embedding_result = await self.embedding_service.get_embedding(memory2.content)
            memory2.embedding = embedding_result.embedding
        
        # Calculate cosine similarity
        import numpy as np
        
        vec1 = np.array(memory1.embedding)
        vec2 = np.array(memory2.embedding)
        
        # Cosine similarity
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        similarity = dot_product / (norm1 * norm2)
        return float(similarity)
    
    async def _create_merged_content(self, primary: Memory, duplicates: List[Memory]) -> str:
        """Create merged content from primary and duplicate memories"""
        
        # Start with primary content
        merged = primary.content
        
        # Add any unique information from duplicates
        all_contents = [primary.content] + [dup.content for dup in duplicates]
        
        # For now, just return the most comprehensive version
        # TODO: Could use LLM to intelligently merge content
        longest_content = max(all_contents, key=len)
        
        return longest_content
    
    async def _get_all_user_memories(self, user_id: str) -> List[Memory]:
        """Get all memories for a user"""
        
        rows = await self.memory_manager.db.fetch("""
            SELECT id, user_id, content, embedding, metadata, category,
                   importance_score, created_at, updated_at
            FROM memories 
            WHERE user_id = $1 AND status = 'active'
            ORDER BY created_at DESC
        """, user_id)
        
        memories = []
        for row in rows:
            memory = Memory(
                id=row['id'],
                user_id=row['user_id'],
                content=row['content'],
                embedding=None,  # Will load on demand
                metadata=row['metadata'] if row['metadata'] else {},
                category=row['category'],
                importance_score=row['importance_score'],
                created_at=row['created_at']
            )
            memories.append(memory)
        
        return memories
    
    async def _get_memories_by_category(self, user_id: str, category: str) -> List[Memory]:
        """Get memories for a specific category"""
        
        rows = await self.memory_manager.db.fetch("""
            SELECT id, user_id, content, embedding, metadata, category,
                   importance_score, created_at, updated_at
            FROM memories 
            WHERE user_id = $1 AND category = $2 AND status = 'active'
            ORDER BY created_at DESC
        """, user_id, category)
        
        memories = []
        for row in rows:
            memory = Memory(
                id=row['id'],
                user_id=row['user_id'],
                content=row['content'],
                embedding=None,  # Will load on demand
                metadata=row['metadata'] if row['metadata'] else {},
                category=row['category'],
                importance_score=row['importance_score'],
                created_at=row['created_at']
            )
            memories.append(memory)
        
        return memories
    
    async def _update_memory_content(self, memory_id: str, new_content: str):
        """Update memory content"""
        
        await self.memory_manager.db.execute("""
            UPDATE memories 
            SET content = $2, updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, memory_id, new_content)
        
        logger.info(f"Updated memory {memory_id} with merged content")
    
    async def _remove_memory(self, memory_id: str):
        """Remove a memory (mark as inactive)"""
        
        await self.memory_manager.db.execute("""
            UPDATE memories 
            SET status = 'deduplicated', updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, memory_id)
        
        logger.info(f"Marked memory {memory_id} as deduplicated")

# Global instance
_deduplication_service: Optional[MemoryDeduplicationService] = None

def get_deduplication_service() -> MemoryDeduplicationService:
    """Get singleton deduplication service"""
    global _deduplication_service
    if _deduplication_service is None:
        _deduplication_service = MemoryDeduplicationService()
    return _deduplication_service