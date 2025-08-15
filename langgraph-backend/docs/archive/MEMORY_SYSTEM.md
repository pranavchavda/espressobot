# PostgreSQL Memory Management System

A comprehensive memory management system for the LangGraph backend using PostgreSQL with pgvector for semantic search and OpenAI embeddings.

## Features

- **PostgreSQL + pgvector**: Vector similarity search with 3072-dimensional embeddings
- **4-layer deduplication**: Exact, fuzzy, key phrase, and semantic deduplication
- **Intelligent prompt assembly**: GPT-4o-mini powered context consolidation
- **Tiered context system**: Core, standard, and full context levels
- **Performance optimized**: < 200ms search latency with connection pooling
- **User isolation**: Complete separation of memories between users

## Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   LangGraph Agent   │────│  Memory Persistence  │────│  PostgreSQL + PG    │
│                     │    │       Node           │    │     Vector          │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
                                        │
                           ┌──────────────────────┐    ┌─────────────────────┐
                           │   Prompt Assembler   │────│   OpenAI Embedding  │
                           │  (GPT-4o-mini)       │    │   Service (3-large) │
                           └──────────────────────┘    └─────────────────────┘
```

## Database Schema

### Core Tables

- **memories**: User memories with embeddings and metadata
- **prompt_fragments**: Agent-specific prompt fragments for context
- **memory_duplicates**: Deduplication tracking
- **memory_analytics**: Search performance analytics

### Key Features

- Vector indexes using `ivfflat` for fast similarity search
- Automatic deduplication using 4-layer approach
- User-specific memory isolation
- Performance tracking and analytics

## Quick Start

### 1. Setup Database Schema

```bash
cd langgraph-backend
python setup_memory_schema.py
```

### 2. Test the System

```bash
python test_memory_system.py
```

### 3. Use in Your Agent

```python
from app.memory.memory_persistence import get_memory_node
from app.agents.memory_enhanced_agent import MemoryEnhancedAgent

# Initialize memory-enhanced agent
agent = MemoryEnhancedAgent(agent_type="general")

# Process with memory context
enhanced_state = await agent.process_with_memory(state)
```

## API Endpoints

### Memory Management

- `POST /api/memory/search` - Search user memories
- `POST /api/memory/create` - Create new memory
- `GET /api/memory/stats/{user_id}` - Get memory statistics

### Prompt Fragments

- `POST /api/memory/fragments` - Create prompt fragment
- `GET /api/memory/fragments/stats` - Get fragment statistics

### Performance

- `GET /api/memory/performance` - Get performance stats
- `POST /api/memory/cleanup` - Clean up old memories

## Configuration

### Environment Variables

```env
DATABASE_URL=postgresql://user:pass@host:5432/db
OPENAI_API_KEY=your_openai_key
MEMORY_TYPE=postgres
MAX_HISTORY_LENGTH=50
SUMMARIZE_AFTER=20
```

### Context Tiers

- **Core**: Minimal context (2K tokens) - Essential information only
- **Standard**: Balanced context (4K tokens) - Relevant details
- **Full**: Complete context (8K tokens) - Comprehensive information

## Memory Types

### User Memories

Automatically extracted from conversations:

- **Preferences**: User settings and choices
- **Personal**: Background information
- **Goals**: Objectives and deadlines
- **Facts**: Important information mentioned
- **Decisions**: Conclusions reached

### Prompt Fragments

Agent-specific context:

- **Guidelines**: Behavioral instructions
- **Templates**: Response patterns
- **Domain Knowledge**: Specialized information
- **Constraints**: Operational limits

## Deduplication System

Four-layer approach prevents memory bloat:

1. **Exact**: SHA256 hash matching
2. **Fuzzy**: String similarity (95% threshold)
3. **Key Phrase**: Important term overlap (80% threshold)
4. **Semantic**: Embedding similarity (85% threshold)

## Performance Optimization

- **Connection Pooling**: 2-20 connections per instance
- **Embedding Cache**: In-memory caching with hit rate tracking
- **Batch Processing**: Up to 100 embeddings per API call
- **Query Optimization**: Optimized indexes and query patterns

## Usage Examples

### Basic Memory Search

```python
from app.memory import PostgresMemoryManager

memory_manager = PostgresMemoryManager()
await memory_manager.initialize()

results = await memory_manager.search_memories(
    user_id="user123",
    query="user preferences",
    limit=5,
    similarity_threshold=0.7
)
```

### Intelligent Prompt Assembly

```python
from app.memory import PromptAssembler, ContextTier

assembler = PromptAssembler(memory_manager)

prompt = await assembler.assemble_prompt(
    user_query="Help me with API integration",
    user_id="user123", 
    agent_type="integrations",
    context_tier=ContextTier.STANDARD
)
```

### LangGraph Integration

```python
from app.memory.memory_persistence import get_memory_node

memory_node = get_memory_node()

# In your agent node function
async def my_agent_node(state: GraphState) -> GraphState:
    # Load memory context
    state = await memory_node.load_memory_context(state)
    
    # Process with enhanced context
    # ... your agent logic ...
    
    # Persist new memories
    state = await memory_node.persist_conversation_memories(state)
    
    return state
```

## Monitoring and Analytics

### Performance Metrics

- Average query time (target: < 200ms)
- Cache hit rates (target: > 80%)
- Memory storage efficiency
- Deduplication effectiveness

### User Analytics

- Total memories per user
- Memory categories and distribution
- Access patterns and frequency
- Context tier usage

## Troubleshooting

### Common Issues

1. **pgvector extension missing**: Install with `CREATE EXTENSION vector;`
2. **Slow queries**: Check index usage and connection pool size
3. **High memory usage**: Tune embedding cache size and cleanup frequency
4. **API rate limits**: Implement backoff and batch operations

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration from Existing Systems

The system is designed to work alongside existing memory systems:

1. **SQLite Memory**: Gradual migration with dual support
2. **Redis Cache**: Can complement PostgreSQL for hot data
3. **In-Memory**: Fallback support for development

## Future Enhancements

- **Memory Importance Scoring**: ML-based importance classification
- **Cross-User Insights**: Privacy-preserving shared learnings
- **Advanced Summarization**: Hierarchical memory compression
- **Multi-Modal Support**: Image and document embeddings