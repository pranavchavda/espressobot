from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, Text, JSON, ARRAY, LargeBinary, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()

class TaskConversation(Base):
    __tablename__ = "task_conversations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String)
    description = Column(String)
    agent_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    status = Column(String, default="active", nullable=False)
    meta_data = Column(String)
    
    # Relationships
    tasks = relationship("Task", back_populates="task_conversation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, default="pending", nullable=False)
    priority = Column(Integer, default=3, nullable=False)
    category = Column(String)
    tags = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    conversation_id = Column(String, ForeignKey("task_conversations.id"))
    agent_id = Column(String)
    parent_task_id = Column(Integer, ForeignKey("tasks.id"))
    meta_data = Column(String)
    
    # Relationships
    task_conversation = relationship("TaskConversation", back_populates="tasks")
    parent_task = relationship("Task", remote_side=[id], back_populates="child_tasks")
    child_tasks = relationship("Task", back_populates="parent_task")
    
    # Task dependencies relationships
    dependent_tasks = relationship(
        "TaskDependency", 
        foreign_keys="TaskDependency.task_id",
        back_populates="task",
        cascade="all, delete-orphan"
    )
    dependency_tasks = relationship(
        "TaskDependency",
        foreign_keys="TaskDependency.depends_on_task_id", 
        back_populates="depends_on_task",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    dependency_type = Column(String, default="blocks", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", foreign_keys=[task_id], back_populates="dependent_tasks")
    depends_on_task = relationship("Task", foreign_keys=[depends_on_task_id], back_populates="dependency_tasks")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    summary = Column(String, nullable=False)
    start_msg_index = Column(Integer, nullable=False)
    end_msg_index = Column(Integer, nullable=False)
    chunk_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships - Note: conversation relationship should be defined in main models
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class AgentRun(Base):
    __tablename__ = "agent_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conv_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    tasks = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships - Note: conversation relationship should be defined in main models
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class EmbeddingCache(Base):
    __tablename__ = "embedding_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    text_hash = Column(String, unique=True, nullable=False)
    text_content = Column(String, nullable=False)
    embedding_data = Column(LargeBinary, nullable=False)
    model_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user_memory_embeddings = relationship("UserMemoryEmbedding", back_populates="embedding_cache", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class UserMemory(Base):
    __tablename__ = "user_memories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    key = Column(String, nullable=False)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships - Note: user relationship should be defined in main models
    
    # Indexes and constraints
    __table_args__ = (
        {"extend_existing": True}
    )

class UserMemoryEmbedding(Base):
    __tablename__ = "user_memory_embeddings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    memory_key = Column(String, nullable=False)
    embedding_cache_id = Column(Integer, ForeignKey("embedding_cache.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    embedding_cache = relationship("EmbeddingCache", back_populates="user_memory_embeddings")
    # Note: user relationship should be defined in main models
    
    # Indexes and constraints
    __table_args__ = (
        {"extend_existing": True}
    )

class ToolResultCache(Base):
    __tablename__ = "tool_result_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tool_name = Column(String, nullable=False)
    input_hash = Column(String, unique=True, nullable=False)
    result = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class JobExecutionLog(Base):
    __tablename__ = "job_execution_log"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String, nullable=False)  # shopify_sync, competitor_scrape, violation_scan, etc.
    status = Column(String, nullable=False)  # completed, failed, running
    details = Column(JSON)  # Additional job-specific details
    executed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class Memory(Base):
    __tablename__ = "memories"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(LargeBinary)
    meta_data = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        {"extend_existing": True}
    )

class AlembicVersion(Base):
    __tablename__ = "alembic_version"
    
    version_num = Column(String, primary_key=True)