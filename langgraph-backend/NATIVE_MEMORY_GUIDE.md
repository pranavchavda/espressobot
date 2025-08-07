# Native LangChain/LangGraph Memory Integration Guide

This guide explains how to use the native LangChain/LangGraph memory features instead of custom implementations. The native approach provides better maintainability, standardization, and leverages the full ecosystem of LangChain memory capabilities.

## Overview

The native memory integration provides:

- **LangGraph PostgresSaver**: Built-in checkpointing and state persistence
- **LangChain Memory Classes**: Standard memory interfaces (Buffer, Summary, Vector)
- **Native PGVector Integration**: Seamless vector store integration
- **OpenAI Embeddings**: Native embedding management
- **Standardized APIs**: Consistent interfaces across the LangChain ecosystem

## Key Components

### 1. LangGraph Native Checkpointing

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver

# PostgreSQL persistent checkpointing
checkpointer = PostgresSaver.from_conn_string(
    "postgresql://user:pass@host:5432/db",
    sync_connection=False
)

# In-memory checkpointing (development)
checkpointer = MemorySaver()
```

### 2. LangChain Memory Classes

```python
from langchain.memory import (
    ConversationBufferMemory,        # Keep last N messages
    ConversationSummaryMemory,       # Summarize old messages  
    VectorStoreRetrieverMemory,      # Semantic search
    ConversationBufferWindowMemory   # Sliding window
)

# Buffer memory - keeps recent messages
memory = ConversationBufferWindowMemory(
    k=10,  # Keep last 10 messages
    return_messages=True,
    memory_key="chat_history"
)

# Summary memory - condenses old conversations
memory = ConversationSummaryMemory(
    llm=ChatOpenAI(model="gpt-4o-mini"),
    return_messages=True,
    memory_key="chat_history"
)

# Vector memory - semantic search on conversation history
memory = VectorStoreRetrieverMemory(
    retriever=vector_store.as_retriever(),
    memory_key="chat_history",
    return_messages=True
)
```

### 3. Native Vector Store Integration

```python
from langchain_postgres import PGVector
from langchain_openai import OpenAIEmbeddings

# Native pgvector integration
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

vector_store = PGVector(
    embeddings=embeddings,
    connection_string="postgresql://user:pass@host:5432/db",
    collection_name="user_memories",
    use_jsonb=True
)

# Use as retriever for semantic search
retriever = vector_store.as_retriever(
    search_kwargs={"k": 5}
)
```

## Usage Examples

### Basic Integration

```python
from app.memory.native_memory_integration import (
    NativeMemoryIntegration,
    MemoryType,
    ContextTier
)

# Create native memory integration
memory = NativeMemoryIntegration(
    memory_type=MemoryType.COMBINED,  # Buffer + Vector
    context_tier=ContextTier.STANDARD # 4K tokens
)

await memory.initialize()

# Use in your agent
enhanced_state = await memory.enhance_agent_state(state)
```

### Advanced Configuration

```python
from app.memory.native_memory_integration import (
    NativeMemoryManager,
    MemoryConfig,
    MemoryType
)

# Custom configuration
config = MemoryConfig(
    memory_type=MemoryType.VECTOR,
    buffer_size=15,
    summary_max_tokens=1000,
    vector_similarity_threshold=0.75,
    vector_top_k=10,
    embedding_model="text-embedding-3-large",
    llm_model="gpt-4o-mini",
    database_url="postgresql://...",
    collection_name="custom_memories"
)

manager = NativeMemoryManager(config)
await manager.initialize()
```

### LangGraph Integration

```python
from app.memory.native_memory_integration import (
    create_native_memory_manager,
    create_memory_node
)
from langgraph.graph import StateGraph, START, END

# Create memory components
memory_manager = create_native_memory_manager()
memory_node = create_memory_node(memory_manager)

# Build graph with native memory
workflow = StateGraph(GraphState)

# Add memory loading node
workflow.add_node("load_memory", memory_node.load_memory_context)
workflow.add_node("your_agent", your_agent_function)
workflow.add_node("persist_memory", memory_node.persist_conversation)

# Connect nodes
workflow.add_edge(START, "load_memory")
workflow.add_edge("load_memory", "your_agent")
workflow.add_edge("your_agent", "persist_memory")
workflow.add_edge("persist_memory", END)

# Compile with native checkpointing
app = workflow.compile(checkpointer=memory_manager.checkpointer)
```

## Memory Types

### Buffer Memory (MemoryType.BUFFER)
- **Use Case**: Simple chat applications
- **Behavior**: Keeps last N messages in memory
- **Pros**: Fast, simple, predictable token usage
- **Cons**: Limited context for long conversations

### Summary Memory (MemoryType.SUMMARY)
- **Use Case**: Long conversations that need condensing
- **Behavior**: Summarizes old messages when buffer fills
- **Pros**: Maintains context over long conversations
- **Cons**: Requires LLM calls for summarization

### Vector Memory (MemoryType.VECTOR)
- **Use Case**: Knowledge-based applications
- **Behavior**: Semantic search over conversation history
- **Pros**: Finds relevant context regardless of recency
- **Cons**: Requires embeddings, more complex setup

### Combined Memory (MemoryType.COMBINED)
- **Use Case**: Production applications needing both patterns
- **Behavior**: Recent messages + semantic search
- **Pros**: Best of both worlds
- **Cons**: Higher resource usage

## Context Tiers

```python
from app.memory.native_memory_integration import ContextTier

# Minimal context (2K tokens) - essential only
ContextTier.MINIMAL

# Standard context (4K tokens) - balanced
ContextTier.STANDARD  

# Full context (8K tokens) - comprehensive
ContextTier.FULL
```

## Migration from Custom Implementation

### 1. Replace Custom Memory Manager

**Before (Custom):**
```python
from app.memory.postgres_memory_manager import PostgresMemoryManager

memory_manager = PostgresMemoryManager()
await memory_manager.initialize()
```

**After (Native):**
```python
from app.memory.native_memory_integration import NativeMemoryIntegration

memory = NativeMemoryIntegration()
await memory.initialize()
```

### 2. Replace Custom Checkpointing

**Before (Custom):**
```python
from app.memory.postgres_checkpointer import PostgresCheckpointer

checkpointer = PostgresCheckpointer(database_url)
```

**After (Native):**
```python
from langgraph.checkpoint.postgres import PostgresSaver

checkpointer = PostgresSaver.from_conn_string(database_url)
```

### 3. Replace Custom Vector Search

**Before (Custom):**
```python
results = await memory_manager.search_memories(
    user_id, query, limit=5
)
```

**After (Native):**
```python
results = await memory.search_user_memories(
    user_id, query
)
```

## Configuration

### Environment Variables

```env
# Database connection
DATABASE_URL=postgresql://user:pass@host:5432/db

# OpenAI API (for embeddings and summarization)
OPENAI_API_KEY=sk-...

# Optional: Customize models
EMBEDDING_MODEL=text-embedding-3-large
SUMMARY_LLM_MODEL=gpt-4o-mini
```

### Database Setup

The native integration uses standard PostgreSQL with pgvector:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- LangGraph checkpointing tables are created automatically
-- PGVector tables are created automatically
```

## Testing

Run the comprehensive test suite:

```bash
# Test all native memory features
python test_native_memory.py

# Test specific memory types
OPENAI_API_KEY=sk-... DATABASE_URL=postgresql://... python test_native_memory.py
```

## Performance Considerations

### Buffer Memory
- **Latency**: ~1-5ms (in-memory)
- **Memory Usage**: O(k) messages
- **Scalability**: Excellent

### Summary Memory  
- **Latency**: ~100-500ms (LLM calls)
- **Memory Usage**: O(1) summary + O(k) recent
- **Scalability**: Good (batched summaries)

### Vector Memory
- **Latency**: ~10-50ms (vector search)
- **Memory Usage**: O(n) embeddings
- **Scalability**: Very good (indexed search)

### Combined Memory
- **Latency**: ~20-100ms
- **Memory Usage**: O(k) + O(n) embeddings
- **Scalability**: Good

## Best Practices

### 1. Choose the Right Memory Type

```python
# Simple chat bots
MemoryType.BUFFER

# Customer support (long conversations)
MemoryType.SUMMARY

# Knowledge assistants
MemoryType.VECTOR

# Production applications
MemoryType.COMBINED
```

### 2. Configure Context Tiers Appropriately

```python
# Mobile/low-latency applications
ContextTier.MINIMAL

# Most applications
ContextTier.STANDARD

# Complex reasoning tasks
ContextTier.FULL
```

### 3. Monitor Performance

```python
stats = memory.get_stats()
print(f"Total users: {stats['total_users']}")
print(f"Query count: {stats['total_queries']}")
print(f"Memory type: {stats['memory_type']}")
```

### 4. Handle Errors Gracefully

```python
try:
    enhanced_state = await memory.enhance_agent_state(state)
except Exception as e:
    logger.error(f"Memory enhancement failed: {e}")
    # Fallback to stateless processing
    enhanced_state = state
```

## Advantages of Native Approach

### vs Custom Implementation

| Aspect | Custom | Native |
|--------|--------|--------|
| **Maintenance** | High (custom code) | Low (maintained by LangChain) |
| **Features** | Limited | Full ecosystem |
| **Testing** | Custom tests | Battle-tested |
| **Documentation** | Limited | Comprehensive |
| **Updates** | Manual | Automatic |
| **Compatibility** | Breaking changes | Stable APIs |

### Benefits

1. **Reduced Maintenance**: LangChain team maintains the code
2. **Better Testing**: Components are tested across many use cases
3. **Feature Rich**: Access to full LangChain ecosystem
4. **Standardization**: Consistent APIs and patterns
5. **Performance**: Optimized implementations
6. **Documentation**: Extensive documentation and examples

## Troubleshooting

### Common Issues

**SQLAlchemy Compatibility Error**
```
TypeError: Can't replace canonical symbol for '__firstlineno__'
```
*Solution*: This is a known issue with some package versions. The implementation includes fallbacks.

**PostgreSSaver Setup Failed**
```
Failed to setup PostgresSaver, falling back to MemorySaver
```
*Solution*: Check DATABASE_URL format and PostgreSQL connection.

**Vector Store Unavailable**
```
langchain-postgres not available, using fallback implementations
```
*Solution*: Install required packages: `pip install langchain-postgres pgvector`

**OpenAI API Errors**
```
Embedding generation failed
```
*Solution*: Check OPENAI_API_KEY and API quota.

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enables detailed logging from native components
```

## Migration Timeline

### Phase 1: Setup (Week 1)
- Install native dependencies
- Create native memory integration
- Run tests to verify functionality

### Phase 2: Parallel Running (Week 2-3)
- Run native system alongside custom
- Compare performance and functionality
- Address any compatibility issues

### Phase 3: Migration (Week 4)
- Switch agents to use native memory
- Update API endpoints
- Remove custom implementations

### Phase 4: Optimization (Week 5)
- Fine-tune memory configurations
- Optimize performance
- Monitor production metrics

## Future Enhancements

The native approach provides a foundation for:

- **Multi-modal Memory**: Image and document embeddings
- **Cross-User Learning**: Shared knowledge bases
- **Advanced Retrieval**: Hybrid search strategies
- **Memory Analytics**: Built-in usage tracking
- **Memory Optimization**: Automatic importance scoring

By using native LangChain/LangGraph components, you get these features as they're released, without custom development.
