from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, LargeBinary, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

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