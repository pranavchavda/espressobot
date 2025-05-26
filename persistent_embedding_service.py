"""
Persistent embedding service that caches embeddings in PostgreSQL.
Integrates with existing models and prevents regeneration on startup.
"""
import hashlib
import pickle
import logging
from typing import List, Optional, Dict, Any
from sqlalchemy.exc import IntegrityError

from extensions import db
from models import EmbeddingCache, UserMemoryEmbedding
from embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class PersistentEmbeddingService:
    """Service that provides persistent embedding caching using PostgreSQL."""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.model_name = self.embedding_service._openai_model_name or 'text-embedding-3-small'
    
    def _hash_text(self, text: str) -> str:
        """Generate SHA256 hash for text and model combination."""
        content = f"{text}|{self.model_name}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def get_or_create_embedding(self, text: str) -> Optional[List[float]]:
        """
        Get embedding from cache or generate and cache it.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector or None if generation fails
        """
        if not text or not isinstance(text, str):
            logger.warning("Invalid text input for embedding")
            return None
        
        text_hash = self._hash_text(text)
        
        # Try to get from cache first
        cached_embedding = self._get_cached_embedding(text_hash)
        if cached_embedding:
            logger.info(f"✅ Using cached embedding for text hash: {text_hash[:8]}... (text: '{text[:50]}...')")
            return cached_embedding
        
        # Generate new embedding
        logger.info(f"🔄 Cache miss - generating new embedding for text hash: {text_hash[:8]}... (text: '{text[:50]}...')")
        embedding = self.embedding_service.get_embedding(text)
        if embedding:
            # Cache the new embedding
            self._cache_embedding(text_hash, text, embedding)
            logger.info(f"✅ Generated and cached new embedding for text hash: {text_hash[:8]}...")
            return embedding
        
        logger.error("Failed to generate embedding for text")
        return None
    
    def _get_cached_embedding(self, text_hash: str) -> Optional[List[float]]:
        """Retrieve embedding from cache."""
        try:
            cache_entry = EmbeddingCache.query.filter_by(
                text_hash=text_hash,
                model_name=self.model_name
            ).first()
            
            if cache_entry:
                # Update last accessed time
                cache_entry.last_accessed = db.func.now()
                db.session.commit()
                
                # Deserialize embedding
                embedding = pickle.loads(cache_entry.embedding_data)
                logger.debug(f"Cache hit for hash {text_hash[:8]}... - text: '{cache_entry.text_content[:50]}...'")
                return embedding
            else:
                logger.debug(f"Cache miss for hash {text_hash[:8]}... - no entry found")
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving cached embedding for hash {text_hash[:8]}...: {e}")
            return None
    
    def _cache_embedding(self, text_hash: str, text: str, embedding: List[float]) -> bool:
        """Store embedding in cache."""
        try:
            # Serialize embedding
            embedding_data = pickle.dumps(embedding)
            
            # Create cache entry
            cache_entry = EmbeddingCache(
                text_hash=text_hash,
                text_content=text,
                embedding_data=embedding_data,
                model_name=self.model_name
            )
            
            db.session.add(cache_entry)
            db.session.commit()
            
            logger.debug(f"Cached embedding for text hash: {text_hash[:8]}...")
            return True
            
        except IntegrityError:
            # Hash already exists, that's fine
            db.session.rollback()
            logger.debug(f"Embedding already cached for text hash: {text_hash[:8]}...")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error caching embedding: {e}")
            return False
    
    def link_user_memory_embedding(self, user_id: int, memory_key: str, text: str) -> bool:
        """
        Link a user memory to its embedding.
        
        Args:
            user_id: User ID
            memory_key: Memory key
            text: Text content of the memory
            
        Returns:
            True if linking successful
        """
        try:
            text_hash = self._hash_text(text)
            
            # Ensure embedding exists in cache
            self.get_or_create_embedding(text)
            
            # Get the cache entry
            cache_entry = EmbeddingCache.query.filter_by(
                text_hash=text_hash,
                model_name=self.model_name
            ).first()
            
            if not cache_entry:
                logger.error(f"No cache entry found for text hash: {text_hash[:8]}...")
                return False
            
            # Create or update user memory embedding link
            existing_link = UserMemoryEmbedding.query.filter_by(
                user_id=user_id,
                memory_key=memory_key
            ).first()
            
            if existing_link:
                # Update existing link
                existing_link.embedding_cache_id = cache_entry.id
            else:
                # Create new link
                memory_embedding = UserMemoryEmbedding(
                    user_id=user_id,
                    memory_key=memory_key,
                    embedding_cache_id=cache_entry.id
                )
                db.session.add(memory_embedding)
            
            db.session.commit()
            logger.debug(f"Linked user {user_id} memory '{memory_key}' to embedding")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error linking user memory embedding: {e}")
            return False
    
    def get_user_memory_embedding(self, user_id: int, memory_key: str) -> Optional[List[float]]:
        """Get embedding for a specific user memory."""
        try:
            memory_embedding = UserMemoryEmbedding.query.filter_by(
                user_id=user_id,
                memory_key=memory_key
            ).first()
            
            if memory_embedding and memory_embedding.embedding_cache:
                # Update last accessed time
                memory_embedding.embedding_cache.last_accessed = db.func.now()
                db.session.commit()
                
                # Return the embedding
                embedding = pickle.loads(memory_embedding.embedding_cache.embedding_data)
                return embedding
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving user memory embedding: {e}")
            return None
    
    def delete_user_memory_embedding(self, user_id: int, memory_key: str) -> bool:
        """Delete user memory embedding link."""
        try:
            memory_embedding = UserMemoryEmbedding.query.filter_by(
                user_id=user_id,
                memory_key=memory_key
            ).first()
            
            if memory_embedding:
                db.session.delete(memory_embedding)
                db.session.commit()
                logger.debug(f"Deleted user memory embedding link for {user_id}:{memory_key}")
                return True
            
            return False
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting user memory embedding: {e}")
            return False
    
    def get_user_memory_keys_with_embeddings(self, user_id: int) -> List[str]:
        """Get all memory keys for a user that have embeddings."""
        try:
            memory_embeddings = UserMemoryEmbedding.query.filter_by(
                user_id=user_id
            ).order_by(UserMemoryEmbedding.created_at).all()
            
            return [me.memory_key for me in memory_embeddings]
            
        except Exception as e:
            logger.error(f"Error retrieving user memory keys: {e}")
            return []
    
    def get_multiple_cached_embeddings(self, text_hashes: List[str]) -> Dict[str, List[float]]:
        """Batch retrieve multiple cached embeddings at once."""
        try:
            cache_entries = EmbeddingCache.query.filter(
                EmbeddingCache.text_hash.in_(text_hashes),
                EmbeddingCache.model_name == self.model_name
            ).all()
            
            result = {}
            for entry in cache_entries:
                # Update last accessed time
                entry.last_accessed = db.func.now()
                
                # Deserialize embedding
                embedding = pickle.loads(entry.embedding_data)
                result[entry.text_hash] = embedding
                logger.debug(f"Batch cache hit for hash {entry.text_hash[:8]}... - text: '{entry.text_content[:50]}...'")
            
            db.session.commit()
            
            # Log cache misses
            for text_hash in text_hashes:
                if text_hash not in result:
                    logger.debug(f"Batch cache miss for hash {text_hash[:8]}... - no entry found")
            
            return result
            
        except Exception as e:
            logger.error(f"Error batch retrieving cached embeddings: {e}")
            return {}
    
    def find_similar_user_memories(self, user_id: int, query_text: str, top_n: int = 5) -> List[tuple[str, float]]:
        """
        Find similar user memories using vector similarity.
        
        Args:
            user_id: User ID
            query_text: Text to find similar memories for
            top_n: Maximum number of results
            
        Returns:
            List of (memory_key, similarity_score) tuples
        """
        try:
            import numpy as np
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Get query embedding
            query_embedding = self.get_or_create_embedding(query_text)
            if not query_embedding:
                return []
            
            # Get all user memory embeddings
            memory_embeddings = UserMemoryEmbedding.query.filter_by(
                user_id=user_id
            ).join(EmbeddingCache).all()
            
            if not memory_embeddings:
                return []
            
            # Prepare data for similarity calculation
            memory_keys = []
            stored_embeddings = []
            
            for me in memory_embeddings:
                try:
                    embedding = pickle.loads(me.embedding_cache.embedding_data)
                    memory_keys.append(me.memory_key)
                    stored_embeddings.append(embedding)
                except Exception as e:
                    logger.warning(f"Error deserializing embedding for memory {me.memory_key}: {e}")
            
            if not stored_embeddings:
                return []
            
            # Calculate similarities
            query_vec = np.array(query_embedding).reshape(1, -1)
            stored_vecs = np.array(stored_embeddings)
            
            similarities = cosine_similarity(query_vec, stored_vecs)[0]
            
            # Pair keys with similarities and sort
            scored_keys = list(zip(memory_keys, similarities))
            scored_keys.sort(key=lambda x: x[1], reverse=True)
            
            return scored_keys[:top_n]
            
        except Exception as e:
            logger.error(f"Error finding similar user memories: {e}")
            return []
    
    def cleanup_old_embeddings(self, days_old: int = 30) -> int:
        """Remove embeddings not accessed in specified days."""
        try:
            from datetime import datetime, timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find old embeddings
            old_embeddings = EmbeddingCache.query.filter(
                EmbeddingCache.last_accessed < cutoff_date
            ).all()
            
            count = 0
            for embedding in old_embeddings:
                # Check if any user memories reference this embedding
                if not embedding.user_memories:
                    db.session.delete(embedding)
                    count += 1
            
            db.session.commit()
            logger.info(f"Cleaned up {count} old embeddings (older than {days_old} days)")
            return count
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during cleanup: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the embedding cache."""
        try:
            total_embeddings = EmbeddingCache.query.count()
            total_user_links = UserMemoryEmbedding.query.count()
            
            # Get unique users with embeddings
            unique_users = db.session.query(UserMemoryEmbedding.user_id).distinct().count()
            
            # Get model distribution
            model_counts = db.session.query(
                EmbeddingCache.model_name,
                db.func.count(EmbeddingCache.id)
            ).group_by(EmbeddingCache.model_name).all()
            
            return {
                "total_embeddings": total_embeddings,
                "total_user_links": total_user_links,
                "unique_users": unique_users,
                "model_distribution": dict(model_counts)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

# Singleton instance
_persistent_embedding_service = None

def get_persistent_embedding_service() -> PersistentEmbeddingService:
    """Get the singleton persistent embedding service."""
    global _persistent_embedding_service
    
    if _persistent_embedding_service is None:
        _persistent_embedding_service = PersistentEmbeddingService()
    
    return _persistent_embedding_service