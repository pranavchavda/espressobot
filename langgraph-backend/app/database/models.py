from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Float, Boolean, ForeignKey, JSON, LargeBinary, Index, Enum
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))
    bio = Column(String)
    password_hash = Column(String)
    is_whitelisted = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Google Workspace OAuth tokens
    google_id = Column(String, unique=True)
    profile_picture = Column(String)
    google_access_token = Column(Text)
    google_refresh_token = Column(Text)
    google_token_expiry = Column(DateTime)
    
    # GA4 Analytics configuration
    ga4_property_id = Column(String(255), default="325181275")
    ga4_enabled = Column(Boolean, default=True)
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    user_memories = relationship("UserMemory", back_populates="user")
    user_memory_embeddings = relationship("UserMemoryEmbedding", back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255))
    topic_title = Column(String)
    topic_details = Column(String)
    filename = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")
    checkpoints = relationship("Checkpoint", back_populates="conversation")
    agent_runs = relationship("AgentRun", back_populates="conversation")
    conversation_summaries = relationship("ConversationSummary", back_populates="conversation")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50))
    content = Column(Text, nullable=False)
    original_content = Column(String)
    tool_call_id = Column(String)
    tool_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    edited_at = Column(DateTime)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    # For backward compatibility, keep both column names
    @property
    def conversation_id(self):
        return self.conv_id
    
    @conversation_id.setter
    def conversation_id(self, value):
        self.conv_id = value

class AgentConfig(Base):
    __tablename__ = "agent_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(255), unique=True, nullable=False)
    agent_type = Column(String(100), nullable=False)
    model_slug = Column(String(255), default="openrouter/horizon-alpha")
    system_prompt = Column(Text)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_agent_configs_active", "is_active"),
        Index("idx_agent_configs_name", "agent_name"),
        Index("idx_agent_configs_type", "agent_type"),
    )

class Checkpoint(Base):
    __tablename__ = "checkpoints"
    
    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), nullable=False, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"))
    checkpoint_data = Column(LargeBinary, nullable=False)
    meta_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="checkpoints")

class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(LargeBinary)
    meta_data = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_memories_user_id", "user_id"),
        Index("idx_memories_created_at", "created_at"),
    )

# Additional models for completeness
class UserMemory(Base):
    __tablename__ = "user_memories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String(255), nullable=False)
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="user_memories")
    
    # Constraints
    __table_args__ = (
        Index("unique_user_memory_key", "user_id", "key", unique=True),
    )

class UserMemoryEmbedding(Base):
    __tablename__ = "user_memory_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    memory_key = Column(String, nullable=False)
    embedding_cache_id = Column(Integer, ForeignKey("embedding_cache.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="user_memory_embeddings")
    embedding_cache = relationship("EmbeddingCache", back_populates="user_memory_embeddings")
    
    # Constraints
    __table_args__ = (
        Index("unique_user_memory_embedding", "user_id", "memory_key", unique=True),
    )

class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    text_hash = Column(String, unique=True, nullable=False)
    text_content = Column(String, nullable=False)
    embedding_data = Column(LargeBinary, nullable=False)
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_memory_embeddings = relationship("UserMemoryEmbedding", back_populates="embedding_cache")

class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    tasks = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="agent_runs")

class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    summary = Column(String, nullable=False)
    start_msg_index = Column(Integer, nullable=False)
    end_msg_index = Column(Integer, nullable=False)
    chunk_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="conversation_summaries")
    
    # Indexes
    __table_args__ = (
        Index("idx_conv_summaries_conv_chunk", "conv_id", "chunk_number"),
    )


# Analytics Cache Models
class DailyAnalyticsCache(Base):
    """Cache daily analytics data from multiple sources"""
    
    __tablename__ = "daily_analytics_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    
    # Shopify data
    shopify_revenue = Column(Float)
    shopify_orders = Column(Integer)
    shopify_aov = Column(Float)
    shopify_top_products = Column(JSON)  # Store top 10 products as JSON
    shopify_raw_data = Column(JSON)  # Full raw response for future needs
    
    # GA4 data
    ga4_revenue = Column(Float)
    ga4_transactions = Column(Integer)
    ga4_users = Column(Integer)
    ga4_conversion_rate = Column(Float)
    ga4_traffic_sources = Column(JSON)
    ga4_ads_performance = Column(JSON)
    ga4_raw_data = Column(JSON)
    
    # Google Workspace data (optional, as it changes frequently)
    workspace_data = Column(JSON, nullable=True)
    
    # Metadata
    is_complete = Column(Boolean, default=False)  # Whether all data sources succeeded
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Create composite index for efficient queries
    __table_args__ = (
        Index('idx_date_complete', 'date', 'is_complete'),
    )


class HourlyAnalyticsCache(Base):
    """Cache hourly analytics for today's data"""
    
    __tablename__ = "hourly_analytics_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer, nullable=False)  # 0-23
    
    # Hourly metrics
    revenue = Column(Float)
    orders = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Composite unique constraint
    __table_args__ = (
        Index('idx_date_hour', 'date', 'hour', unique=True),
    )


class AnalyticsSyncStatus(Base):
    """Track sync status for bulk data fetching"""
    
    __tablename__ = "analytics_sync_status"
    
    id = Column(Integer, primary_key=True, index=True)
    sync_type = Column(String(50), nullable=False)  # 'daily', 'monthly', 'yearly'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Status tracking
    status = Column(String(20), default='pending')  # pending, in_progress, completed, failed
    total_days = Column(Integer)
    processed_days = Column(Integer, default=0)
    failed_days = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Error tracking
    last_error = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# Dynamic Agent Models
class DynamicAgent(Base):
    """User-created agents that can be loaded at runtime"""
    
    __tablename__ = "dynamic_agents"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    
    # Agent configuration
    agent_type = Column(String(50), default='specialist')
    system_prompt = Column(Text, nullable=False)
    
    # Model configuration
    model_provider = Column(String(50), default='openai')
    model_name = Column(String(100), default='gpt-5-nano')
    temperature = Column(JSON, nullable=True)
    max_tokens = Column(Integer, nullable=True)
    max_completion_tokens = Column(Integer, nullable=True)
    
    # Tools configuration
    tools = Column(JSON, default=[])
    mcp_servers = Column(JSON, default=[])
    
    # Capabilities and routing
    capabilities = Column(JSON, default=[])
    routing_keywords = Column(JSON, default=[])
    example_queries = Column(JSON, default=[])
    
    # Status
    is_active = Column(Boolean, default=True)
    is_tested = Column(Boolean, default=False)
    last_error = Column(Text, nullable=True)
    
    # Metadata
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Performance metrics
    usage_count = Column(Integer, default=0)
    success_rate = Column(JSON, default={"success": 0, "total": 0})
    avg_response_time = Column(Integer, nullable=True)


class AgentTemplate(Base):
    """Pre-built agent templates users can clone"""
    
    __tablename__ = "agent_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))
    description = Column(Text)
    config = Column(JSON)
    usage_count = Column(Integer, default=0)
    rating = Column(JSON, default={"score": 0, "count": 0})
    is_public = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# MCP Server Enums
class MCPServerStatus(enum.Enum):
    PENDING = "pending"
    TESTING = "testing"
    CONNECTED = "connected"
    FAILED = "failed"
    DISABLED = "disabled"


class MCPServerType(enum.Enum):
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"
    HTTP = "http"


class UserMCPServer(Base):
    """User-configured MCP servers"""
    
    __tablename__ = "user_mcp_servers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    
    server_type = Column(Enum(MCPServerType), default=MCPServerType.STDIO)
    connection_config = Column(JSON, nullable=False)
    
    available_tools = Column(JSON, default=[])
    tool_count = Column(Integer, default=0)
    supports_resources = Column(Boolean, default=False)
    supports_prompts = Column(Boolean, default=False)
    
    requires_auth = Column(Boolean, default=False)
    auth_config = Column(JSON, nullable=True)
    
    status = Column(Enum(MCPServerStatus), default=MCPServerStatus.PENDING)
    last_connected = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    is_public = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    last_used = Column(DateTime(timezone=True), nullable=True)
    
    rate_limit = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class MCPServerTool(Base):
    """Tools discovered from user MCP servers"""
    
    __tablename__ = "mcp_server_tools"
    
    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("user_mcp_servers.id"), nullable=False, index=True)
    
    name = Column(String(200), nullable=False)
    display_name = Column(String(300))
    description = Column(Text)
    
    input_schema = Column(JSON)
    output_schema = Column(JSON)
    
    category = Column(String(100))
    tags = Column(JSON, default=[])
    
    usage_count = Column(Integer, default=0)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    avg_response_time = Column(Integer, nullable=True)
    
    is_available = Column(Boolean, default=True)
    last_error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())