# Context Loading Evolution Plan

## Current State: Pattern Matching
- Simple regex patterns for context selection
- Fast and deterministic
- No external dependencies
- Good for MVP and testing

## Near-term Consideration: Mem0 OSS Migration
If we hit API limits (1000 retrievals/month), migrate to:
- Self-hosted Mem0 OSS
- SQLite for storage
- Local Qdrant for vector search
- Same API interface (minimal code changes)

```bash
# Migration would be simple:
cd server/memory
pip install mem0ai
# Configure for local SQLite instead of API
```

## Future Evolution: Semantic Context Loading

### Phase 1: Hybrid Approach
Keep pattern matching for speed, add semantic search for edge cases:

```javascript
// Quick pattern check first
const patternMatches = analyzeContextNeeds(message);

// If no strong matches, use semantic search
if (patternMatches.length <= 1) {
  const semanticMatches = await semanticContextSearch(message);
  return [...patternMatches, ...semanticMatches];
}
```

### Phase 2: Full Semantic Search

#### 1. Vectorize Documentation
```javascript
// One-time indexing of all documentation
const documentChunks = [
  {
    id: 'preorder-rules',
    content: 'Preorder management: Add preorder-2-weeks tag...',
    embedding: [0.1, 0.2, ...] // 1536-dim vector
  },
  // ... all other sections
];
```

#### 2. Semantic Context Manager
```javascript
class SemanticContextManager {
  constructor() {
    this.vectorStore = new VectorStore(); // Could use Pinecone, Weaviate, or local
    this.embedder = new OpenAIEmbeddings();
  }
  
  async getRelevantContext(message) {
    // Embed the query
    const queryEmbedding = await this.embedder.embed(message);
    
    // Semantic search
    const results = await this.vectorStore.search({
      vector: queryEmbedding,
      topK: 5,
      threshold: 0.7
    });
    
    return results.map(r => r.metadata.section);
  }
}
```

#### 3. Local Vector Options
For fully local operation:
- **ChromaDB**: Python/JS, persist to disk
- **Faiss**: Facebook's library, very fast
- **SQLite-VSS**: Vector search in SQLite
- **LanceDB**: Embedded vector database

### Implementation Roadmap

#### Step 1: Prepare for Migration (Current)
- Keep context loading interface generic
- Document all context sections well
- Track pattern matching effectiveness

#### Step 2: Add Metrics (Next Sprint)
```javascript
// Track what contexts are actually useful
async function trackContextUsage(message, loadedContexts, wasSuccessful) {
  await memoryOperations.add(
    `Context usage: ${loadedContexts.join(',')} for "${message}" - ${wasSuccessful ? 'success' : 'failed'}`,
    'system_metrics'
  );
}
```

#### Step 3: Build Semantic Index (When Needed)
```python
# Script to vectorize all documentation
import openai
from typing import List, Dict
import json

def create_embeddings_index():
    sections = load_all_documentation_sections()
    
    embeddings = []
    for section in sections:
        embedding = openai.Embedding.create(
            input=section['content'],
            model="text-embedding-3-small"
        )
        embeddings.append({
            'id': section['id'],
            'embedding': embedding['data'][0]['embedding'],
            'metadata': section['metadata']
        })
    
    # Save to local vector store
    save_to_vector_store(embeddings)
```

#### Step 4: A/B Test Approaches
```javascript
// Compare pattern matching vs semantic
async function getSmartContextWithComparison(message) {
  const patternResults = await patternBasedContext(message);
  const semanticResults = await semanticContext(message);
  
  // Log differences for analysis
  logContextDifferences(patternResults, semanticResults);
  
  // Use pattern matching for now, but collect data
  return patternResults;
}
```

### Benefits of Semantic Approach

1. **Handles Ambiguity**: "Make this product available next month" → understands preorder context
2. **Cross-Language**: Works with queries in different phrasings
3. **Learns Relationships**: Discovers that "oversell" relates to "inventory policy"
4. **No Pattern Maintenance**: Self-organizing based on content

### Keeping It Practical

For now, pattern matching is:
- ✅ Fast (< 5ms)
- ✅ Predictable
- ✅ No dependencies
- ✅ Easy to debug

We'll evolve to semantic when:
- ❌ Patterns become too complex
- ❌ Missing relevant contexts often
- ❌ Users complain about relevance
- ❌ We have usage data to train on

### Hybrid Sweet Spot

The ideal might be hybrid:
```javascript
// Fast path for common cases
if (COMMON_PATTERNS.test(message)) {
  return patternBasedContext(message);
}

// Semantic for complex queries
return semanticContext(message);
```

This gives us:
- Speed for 80% of cases
- Intelligence for the complex 20%
- Graceful degradation
- Progressive enhancement

## Next Steps

1. **Continue with pattern matching** (current approach is good)
2. **Add usage tracking** to understand what works
3. **Prepare for Mem0 OSS** if we hit limits
4. **Experiment with semantic** in parallel
5. **Migrate when data justifies it**

The architecture is already flexible enough to support any of these approaches!