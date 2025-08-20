# Semantic Search Implementation for EspressoBot

## Overview
We've implemented semantic search using OpenAI's built-in file search capability through the @openai/agents SDK. This provides powerful semantic context loading without building our own vector infrastructure.

## Architecture

### 1. Vector Store Manager
**File**: `vector-store-manager.js`
- Creates and manages OpenAI Vector Stores
- Uploads documentation files
- Caches vector store ID for reuse
- Handles file processing and status

### 2. Semantic Bash Agent
**File**: `agents/semantic-bash-agent.js`
- Extends regular bash agent with file search tool
- Can search documentation semantically
- Falls back to regular bash agent if vector store unavailable

### 3. Integration with Orchestrator
- Dynamic orchestrator can spawn semantic bash agents
- Use `useSemanticSearch: true` parameter
- Automatic fallback to regular agents

## Setup Instructions

### 1. Create Vector Store
```bash
# One-time setup
node server/context-loader/setup-vector-store.js

# Fresh setup (recreate store)
node server/context-loader/setup-vector-store.js --fresh

# With test searches
node server/context-loader/setup-vector-store.js --test
```

### 2. Environment Variable (Optional)
```bash
# Add to .env
VECTOR_STORE_ID=vs_xxxxxxxxxxxxx
```

## Usage Examples

### From Orchestrator
```javascript
// Spawn agent with semantic search
await spawn_bash_agent({
  agentName: "Preorder_Manager",
  task: "Add product to preorder with proper tags",
  useSemanticSearch: true
});
```

### Direct Usage
```javascript
import { createSemanticBashAgent } from './agents/semantic-bash-agent.js';

const agent = await createSemanticBashAgent(
  'My_Agent',
  'Find and apply preorder rules',
  conversationId
);
```

### In Agent Instructions
```
Use search_documentation to find:
- "preorder management rules"
- "update_pricing tool usage"
- "create combo product workflow"
- "metafields product features"
```

## Included Documentation

Currently indexed in vector store:
1. **Tool Usage Guide** - Complete tool documentation
2. **Business Rules** - iDrinkCoffee.com specific rules
3. **Agent Instructions** - Enhanced bash agent prompt
4. **Product Guidelines** - Creation, metafields, tags

## Benefits

### 1. **Natural Language Queries**
- "How do I add a product to preorder?"
- "What's the process for bulk pricing?"
- "Show me combo product creation"

### 2. **Context Understanding**
- Finds related concepts automatically
- Understands synonyms and variations
- Returns relevant sections only

### 3. **No Maintenance**
- No pattern updates needed
- Self-organizing based on content
- Learns from documentation changes

### 4. **Performance**
- Hosted by OpenAI (fast)
- Cached vector store ID
- Parallel search capability

## Cost Considerations

- **Storage**: ~$0.10/GB/day for vector stores
- **Queries**: Included in API usage
- **Updates**: Reupload files as needed

## Future Enhancements

1. **More Documentation**
   - Workflow examples
   - Error solutions
   - Best practices

2. **Dynamic Updates**
   - Auto-refresh on doc changes
   - Version tracking
   - Change notifications

3. **Usage Analytics**
   - Track most searched topics
   - Identify documentation gaps
   - Optimize content

## Troubleshooting

### Vector Store Not Found
```bash
# Recreate store
node server/context-loader/setup-vector-store.js --fresh
```

### Search Not Working
- Check OpenAI API key
- Verify vector store has files
- Check file processing status

### Fallback Behavior
If semantic search fails, agents automatically fall back to:
1. Pattern-based context loading
2. Basic bash agent functionality

## Comparison: Pattern vs Semantic

| Feature | Pattern Matching | Semantic Search |
|---------|-----------------|-----------------|
| Setup | Immediate | Requires vector store |
| Maintenance | Update patterns | Update documents |
| Flexibility | Limited | High |
| Context | Exact matches | Related concepts |
| Performance | <5ms | ~200-500ms |
| Cost | Free | API usage |

## Best Practices

1. **Use Semantic Search For:**
   - Complex business rules
   - Tool discovery
   - Workflow guidance
   - Error resolution

2. **Use Pattern Matching For:**
   - Known exact queries
   - Simple lookups
   - Performance critical
   - Offline operation

3. **Hybrid Approach:**
   - Try patterns first
   - Fall back to semantic
   - Cache common queries
   - Learn from usage

## Summary

Semantic search provides a powerful, maintenance-free way to give agents access to documentation. It understands intent, finds related information, and adapts as documentation evolves. Combined with pattern matching for speed, it provides the best of both worlds.