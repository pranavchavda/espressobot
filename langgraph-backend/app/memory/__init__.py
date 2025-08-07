"""
Memory Management Package for LangGraph Backend

This package provides comprehensive memory management capabilities including:
- PostgreSQL-based memory storage with pgvector similarity search
- OpenAI text-embedding-3-large embeddings for semantic search
- 4-layer deduplication (exact, fuzzy, key phrase, semantic)
- Intelligent prompt assembly with GPT-4o-mini consolidation
- Tiered context system (core, standard, full)
- Performance optimization with connection pooling
"""

from .postgres_memory_manager import (
    PostgresMemoryManager,
    Memory,
    PromptFragment,
    SearchResult,
    MemoryDeduplicator
)

from .embedding_service import (
    EmbeddingService,
    EmbeddingResult,
    get_embedding_service
)

from .prompt_assembler import (
    PromptAssembler,
    AssembledPrompt,
    ContextTier
)

from .memory_config import (
    MemoryConfig,
    ConversationMemory
)

from .memory_persistence import (
    MemoryPersistenceNode,
    MemoryExtractionService,
    get_memory_node
)

__all__ = [
    # Core classes
    'PostgresMemoryManager',
    'Memory',
    'PromptFragment', 
    'SearchResult',
    'MemoryDeduplicator',
    
    # Embedding service
    'EmbeddingService',
    'EmbeddingResult',
    'get_embedding_service',
    
    # Prompt assembly
    'PromptAssembler',
    'AssembledPrompt', 
    'ContextTier',
    
    # Legacy compatibility
    'MemoryConfig',
    'ConversationMemory',
    
    # Memory persistence
    'MemoryPersistenceNode',
    'MemoryExtractionService',
    'get_memory_node'
]

# Version info
__version__ = '1.0.0'
__author__ = 'EspressoBot Team'
__description__ = 'PostgreSQL-based memory management with pgvector similarity search'