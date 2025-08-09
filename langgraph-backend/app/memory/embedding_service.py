"""OpenAI Embedding Service for text-embedding-3-large"""

import os
import asyncio
import hashlib
import logging
from typing import List, Dict, Optional, Union, Any
from dataclasses import dataclass
import openai
from openai import AsyncOpenAI
import numpy as np
from functools import lru_cache
import json

logger = logging.getLogger(__name__)

@dataclass
class EmbeddingResult:
    """Result from embedding operation"""
    embedding: List[float]
    token_count: int
    cached: bool = False

class EmbeddingService:
    """Async service for generating embeddings using OpenAI's text-embedding-3-large"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "text-embedding-3-large"
        self.dimensions = 3072
        self.max_batch_size = 100  # OpenAI's batch limit
        self.cache: Dict[str, EmbeddingResult] = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text for embedding"""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        # Limit length (text-embedding-3-large has 8191 token limit)
        if len(text) > 30000:  # Rough character limit
            text = text[:30000] + "..."
        return text
    
    async def get_embedding(self, text: str) -> EmbeddingResult:
        """Get embedding for a single text"""
        text = self._clean_text(text)
        cache_key = self._get_cache_key(text)
        
        # Check cache first
        if cache_key in self.cache:
            self.cache_hits += 1
            result = self.cache[cache_key]
            return EmbeddingResult(
                embedding=result.embedding,
                token_count=result.token_count,
                cached=True
            )
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=[text],
                dimensions=self.dimensions
            )
            
            embedding = response.data[0].embedding
            token_count = response.usage.total_tokens
            
            result = EmbeddingResult(
                embedding=embedding,
                token_count=token_count,
                cached=False
            )
            
            # Cache the result
            self.cache[cache_key] = result
            self.cache_misses += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Get embeddings for multiple texts efficiently"""
        if not texts:
            return []
        
        # Process in batches
        results = []
        for i in range(0, len(texts), self.max_batch_size):
            batch = texts[i:i + self.max_batch_size]
            batch_results = await self._process_batch(batch)
            results.extend(batch_results)
        
        return results
    
    async def _process_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Process a batch of texts"""
        cleaned_texts = [self._clean_text(text) for text in texts]
        cache_keys = [self._get_cache_key(text) for text in cleaned_texts]
        
        # Separate cached and non-cached texts
        cached_results = {}
        non_cached_texts = []
        non_cached_indices = []
        
        for i, (text, cache_key) in enumerate(zip(cleaned_texts, cache_keys)):
            if cache_key in self.cache:
                cached_results[i] = self.cache[cache_key]
                self.cache_hits += 1
            else:
                non_cached_texts.append(text)
                non_cached_indices.append(i)
        
        # Get embeddings for non-cached texts
        new_embeddings = {}
        if non_cached_texts:
            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=non_cached_texts,
                    dimensions=self.dimensions
                )
                
                for i, (embedding_data, text_idx) in enumerate(zip(response.data, non_cached_indices)):
                    embedding = embedding_data.embedding
                    token_count = response.usage.total_tokens // len(non_cached_texts)  # Approximate
                    
                    result = EmbeddingResult(
                        embedding=embedding,
                        token_count=token_count,
                        cached=False
                    )
                    
                    new_embeddings[text_idx] = result
                    cache_key = cache_keys[text_idx]
                    self.cache[cache_key] = result
                    self.cache_misses += 1
                    
            except Exception as e:
                logger.error(f"Failed to generate batch embeddings: {e}")
                raise
        
        # Combine results in original order
        final_results = []
        for i in range(len(texts)):
            if i in cached_results:
                result = cached_results[i]
                final_results.append(EmbeddingResult(
                    embedding=result.embedding,
                    token_count=result.token_count,
                    cached=True
                ))
            else:
                final_results.append(new_embeddings[i])
        
        return final_results
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Handle zero vectors
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            return float(np.dot(a, b) / (norm_a * norm_b))
        except Exception as e:
            error_msg = str(e)
            # Truncate error message if it's too long (likely contains embeddings)
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "... (truncated)"
            logger.error(f"Error calculating cosine similarity: {error_msg}")
            return 0.0
    
    def calculate_similarities(self, query_embedding: List[float], 
                             target_embeddings: List[List[float]]) -> List[float]:
        """Calculate similarities between query and multiple target embeddings"""
        return [self.cosine_similarity(query_embedding, target) for target in target_embeddings]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_size": len(self.cache),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests
        }
    
    def clear_cache(self):
        """Clear embedding cache"""
        self.cache.clear()
        self.cache_hits = 0
        self.cache_misses = 0
        logger.info("Embedding cache cleared")

# Global singleton instance
_embedding_service_instance: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    """Get singleton embedding service instance"""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance