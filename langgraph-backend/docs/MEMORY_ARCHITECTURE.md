# EspressoBot Memory Architecture

## Overview

EspressoBot uses a sophisticated multi-tier memory system built on LangGraph with PostgreSQL/pgvector for semantic search and persistence.

## Current Architecture

### 1. Memory Layers

#### Short-term Memory (Conversation State)
- **Storage**: LangGraph checkpointers (PostgreSQL/SQLite)
- **Scope**: Per-thread conversation history
- **Duration**: Session-based (configurable retention)
- **Access**: Direct via thread_id
- **Usage**: Active conversation context

#### Long-term Memory (Semantic Store)
- **Storage**: PostgreSQL with pgvector
- **Scope**: User-specific persistent memories
- **Duration**: Permanent (with cleanup policies)
- **Access**: Semantic search via embeddings
- **Usage**: Cross-conversation knowledge retention

#### Working Memory (Agent Context)
- **Storage**: In-memory during execution
- **Scope**: Per-agent task execution
- **Duration**: Task lifetime
- **Access**: Via ContextAwareMixin
- **Usage**: A2A context passing

### 2. Database Schema

```sql
memories
├── id (primary key)
├── user_id (indexed)
├── content (text)
├── embedding (vector 3072)
├── metadata (jsonb)
├── category (indexed)
├── importance_score (indexed)
├── access_count
├── last_accessed_at
└── timestamps

prompt_fragments
├── id (primary key)
├── category
├── priority (indexed)
├── content
├── embedding (vector 3072)
├── agent_type (indexed)
├── context_tier (core/standard/full)
└── is_active

memory_duplicates
├── original_id (foreign key)
├── duplicate_hash
├── similarity_score
└── dedup_type (exact/fuzzy/key_phrase/semantic)

memory_analytics
├── user_id
├── query_text
├── results_count
├── response_time_ms
└── context_tier
```

### 3. Memory Operations

#### Storage
- Automatic embedding generation (text-embedding-3-large)
- 4-layer deduplication (exact → fuzzy → key-phrase → semantic)
- Importance scoring and categorization
- Access tracking for relevance decay

#### Retrieval
- Semantic similarity search using pgvector
- Category-based filtering
- Importance-weighted ranking
- Access count boosting for frequently used memories

#### Management
- Automatic cleanup of old, unused memories
- Memory consolidation and summarization
- Performance monitoring and optimization

## Proposed Enhancements

### 1. User-Facing Memory Interface

#### Memory Dashboard API
```python
GET /api/memory/dashboard/{user_id}
Response:
{
  "stats": {
    "total_memories": 234,
    "categories": ["products", "preferences", "interactions"],
    "storage_used_mb": 12.5,
    "last_updated": "2025-01-09T02:00:00Z"
  },
  "recent_memories": [...],
  "important_memories": [...],
  "memory_timeline": [...]
}
```

#### Memory CRUD Operations
```python
# List memories with filtering
GET /api/memory/list/{user_id}?category=products&limit=50&importance_min=0.7

# Get specific memory
GET /api/memory/{memory_id}

# Update memory
PUT /api/memory/{memory_id}
{
  "content": "Updated content",
  "category": "products",
  "importance_score": 0.9
}

# Delete memory
DELETE /api/memory/{memory_id}

# Bulk operations
POST /api/memory/bulk
{
  "operation": "delete|update|export",
  "memory_ids": [1, 2, 3],
  "updates": {...}
}
```

#### Memory Export/Import
```python
# Export memories
GET /api/memory/export/{user_id}?format=json|csv

# Import memories
POST /api/memory/import/{user_id}
Content-Type: multipart/form-data
```

### 2. Enhanced Agent Memory Usage

#### Memory-Aware Agent Mixin
```python
class MemoryAwareAgent(ContextAwareMixin):
    async def get_relevant_memories(self, query: str, limit: int = 5):
        """Fetch memories relevant to current query"""
        memory_manager = self.get_memory_manager()
        memories = await memory_manager.search_memories(
            user_id=self.state.get("user_id"),
            query=query,
            limit=limit,
            similarity_threshold=0.7
        )
        return memories
    
    async def store_interaction_memory(self, content: str, category: str):
        """Store important interaction as memory"""
        memory = Memory(
            user_id=self.state.get("user_id"),
            content=content,
            category=category,
            metadata={
                "agent": self.name,
                "thread_id": self.state.get("thread_id"),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        await memory_manager.store_memory(memory)
```

#### Memory Integration Patterns
1. **Pre-query Memory Fetch**: Agents search memories before processing
2. **Post-action Memory Store**: Important outcomes saved as memories
3. **Memory-guided Decisions**: Use past interactions to inform responses
4. **Cross-agent Memory Sharing**: Shared memory pool for collaboration

### 3. Memory UI Components

#### React Components
```typescript
// Memory viewer component
<MemoryViewer 
  userId={userId}
  onEdit={(memory) => handleEdit(memory)}
  onDelete={(id) => handleDelete(id)}
/>

// Memory search interface
<MemorySearch
  onSearch={(query) => searchMemories(query)}
  filters={['category', 'importance', 'date']}
/>

// Memory statistics dashboard
<MemoryStats
  userId={userId}
  showCharts={true}
  timeRange="30d"
/>

// Memory management toolbar
<MemoryToolbar
  onExport={() => exportMemories()}
  onImport={(file) => importMemories(file)}
  onCleanup={() => cleanupOldMemories()}
/>
```

### 4. Memory Lifecycle Management

#### Automatic Memory Creation
- Extract key facts from conversations
- Identify user preferences and patterns
- Store successful problem resolutions
- Track product interests and purchases

#### Memory Consolidation
- Merge similar memories periodically
- Summarize old conversation threads
- Update importance scores based on usage
- Archive rarely accessed memories

#### Privacy & Security
- User-controlled memory deletion
- Encryption at rest for sensitive data
- Audit logging for memory access
- GDPR compliance (right to be forgotten)

## Implementation Plan

### Phase 1: API Enhancement (Week 1)
1. Extend memory API endpoints
2. Add bulk operations support
3. Implement export/import functionality
4. Add memory statistics endpoints

### Phase 2: Agent Integration (Week 2)
1. Create MemoryAwareAgent mixin
2. Update agents to use memory system
3. Implement memory creation patterns
4. Add cross-agent memory sharing

### Phase 3: UI Development (Week 3)
1. Build React components for memory management
2. Create memory dashboard page
3. Add memory search and filtering
4. Implement memory timeline view

### Phase 4: Optimization (Week 4)
1. Performance tuning for large memory sets
2. Implement memory consolidation jobs
3. Add caching layer for frequent queries
4. Monitor and optimize pgvector indexes

## Performance Considerations

### Query Optimization
- Use HNSW indexes for faster similarity search
- Implement query result caching
- Batch embedding generation
- Connection pooling for PostgreSQL

### Scaling Strategy
- Partition memories by user_id for large datasets
- Use read replicas for search queries
- Implement memory archival for old data
- Consider distributed vector databases (Pinecone, Weaviate) for massive scale

## Monitoring & Analytics

### Key Metrics
- Memory search latency (p50, p95, p99)
- Memory storage growth rate
- Deduplication effectiveness
- Agent memory usage patterns
- User engagement with memory features

### Dashboards
- Memory system health dashboard
- User memory usage analytics
- Agent memory access patterns
- Performance monitoring dashboard

## Security & Privacy

### Data Protection
- Encrypt sensitive memory content
- Implement access controls per user
- Audit logging for all memory operations
- Regular security assessments

### Compliance
- GDPR right to deletion
- Data retention policies
- User consent for memory storage
- Export functionality for data portability

## Future Enhancements

### Advanced Features
1. **Memory Chains**: Link related memories together
2. **Temporal Memories**: Time-based memory decay
3. **Collaborative Memories**: Shared team knowledge base
4. **Memory Templates**: Structured memory types
5. **Memory Reasoning**: Use memories for complex reasoning
6. **Memory Visualization**: Graph-based memory exploration

### Integration Possibilities
1. External knowledge bases (Notion, Confluence)
2. CRM system integration for customer memories
3. Product catalog enrichment from memories
4. Predictive memory pre-fetching
5. Memory-based personalization engine