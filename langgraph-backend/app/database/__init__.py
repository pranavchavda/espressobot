"""
Database models and initialization for the EspressoBot application.

This module provides SQLAlchemy models for:
1. Core application tables (users, conversations, messages, etc.)
2. Price monitoring system tables (products, competitors, matches, etc.) 
3. Extended functionality tables (tasks, embeddings, caching, etc.)
"""

# Import all models to make them available
from .models import (
    Base,
    User,
    Conversation, 
    Message,
    AgentConfig,
    Checkpoint,
    Memory,
    UserMemory,
    UserMemoryEmbedding,
    EmbeddingCache,
    AgentRun,
    ConversationSummary
)

from .price_monitor_models import (
    IdcProduct,
    CompetitorProduct,
    ProductMatch,
    Competitor,
    MonitoredBrand,
    MonitoredCollection,
    PriceHistory,
    PriceAlert,
    ViolationHistory,
    ScrapeJob
)

from .extended_models import (
    TaskConversation,
    Task,
    TaskDependency,
    ToolResultCache,
    JobExecutionLog
)

# Export all models for easy import
__all__ = [
    'Base',
    
    # Core models
    'User',
    'Conversation',
    'Message', 
    'AgentConfig',
    'Checkpoint',
    'Memory',
    'UserMemory',
    'UserMemoryEmbedding',
    'EmbeddingCache',
    'AgentRun',
    'ConversationSummary',
    
    # Price monitoring models
    'IdcProduct',
    'CompetitorProduct',
    'ProductMatch',
    'Competitor',
    'MonitoredBrand',
    'MonitoredCollection',
    'PriceHistory',
    'PriceAlert',
    'ViolationHistory',
    'ScrapeJob',
    
    # Extended models
    'TaskConversation',
    'Task',
    'TaskDependency',
    'ToolResultCache',
    'JobExecutionLog',
]