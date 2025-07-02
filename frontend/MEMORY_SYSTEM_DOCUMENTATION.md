# Memory System Documentation

## Overview
EspressoBot uses a custom local memory system built with SQLite and OpenAI embeddings, providing unlimited memory operations without API limits.

## Architecture
- **Storage**: SQLite database at `/server/memory/data/espressobot_memory.db`
- **Embeddings**: OpenAI text-embedding-3-small (1536 dimensions)
- **Search**: Cosine similarity with configurable threshold (default 0.1)
- **Extraction**: GPT-4o-mini for intelligent fact extraction

## Key Features

### 1. Intelligent Fact Extraction
- Extracts 2 facts per message exchange (not per conversation)
- Includes both user and assistant facts worth remembering
- Always honors explicit "remember this" requests
- Facts are stored as self-contained sentences

### 2. Strong Deduplication System
Four-layer deduplication prevents memory bloat:
1. **Exact Match**: Checks for identical memories
2. **Fuzzy Match**: 90% similarity threshold for near-duplicates
3. **Key Phrase Match**: Identifies memories with same key entities
4. **Semantic Match**: 85% cosine similarity threshold

### 3. User Isolation
- Each user has their own memory space
- Memories persist across conversations
- User ID format: `user_{id}` (e.g., `user_2`)

### 4. Python CLI Integration
Bash agents can access memories via:
```bash
python /home/pranav/espressobot/frontend/python-tools/memory_operations.py search "query"
```

## Implementation Files
- `/server/memory/simple-local-memory.js` - Core SQLite + embeddings
- `/server/memory/memory-operations-local.js` - Operations wrapper
- `/server/tools/memory-tool.js` - Tool integration
- `/python-tools/memory_operations.py` - CLI for bash agents

## Memory Management UI
- Accessible via the memory icon in the UI
- Features bulk deletion with checkboxes
- Wide dialog (max-w-6xl) for better visibility
- Real-time search and filtering

## Performance
- Storage: ~100ms for add operations (with embedding)
- Search: ~200ms for semantic search
- Deduplication: ~50ms for all checks

## Configuration
Environment variables:
- `OPENAI_API_KEY` - Required for embeddings
- `ESPRESSOBOT_USER_ID` - Used by Python CLI tool

## Benefits Over Previous System (Mem0)
- ✅ No API limits (was 1000/month)
- ✅ No external dependencies
- ✅ Full control over data
- ✅ Better performance
- ✅ Privacy (all data local)

## Example Usage
```javascript
// Add memory
await memoryOperations.add("User prefers Ethiopian coffee", userId, {
  category: "preference"
});

// Search memories
const memories = await memoryOperations.search("coffee preferences", userId);

// Extract from conversation
const facts = await memoryOperations.extractMemorySummary(conversation, {
  conversationId: "123",
  useNano: false  // Use GPT-4o-mini
});
```