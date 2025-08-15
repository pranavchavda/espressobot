# EspressoBot Memory System

## Overview

EspressoBot now supports three memory implementations:

1. **Mem0 Platform (Hosted)** - Default when `MEM0_API_KEY` is set
2. **Mem0 OSS (Local)** - Self-hosted with SQLite and vector storage
3. **Hybrid Approach** - Automatic fallback with API limit handling

## Current Setup

### Mem0 Platform (Current Default)
- Uses hosted Mem0 service with API key
- 1000 free retrievals per month
- Automatic memory extraction and semantic search
- Located in: `memory-operations.js`

### Mem0 OSS Local
- Self-hosted memory using SQLite + in-memory vector store
- No API limits but requires local storage setup
- Located in: `memory-operations-local.js`, `mem0-local-config.js`

### Hybrid System
- Automatically uses Platform when available
- Falls back to local storage on API limits (403 errors)
- Located in: `memory-operations-hybrid.js`

## Environment Variables

```bash
# For Mem0 Platform
MEM0_API_KEY=your_mem0_api_key

# To force local storage (even with API key)
MEM0_USE_LOCAL=true

# OpenAI API key (required for both local and platform)
OPENAI_API_KEY=your_openai_api_key
```

## Usage

The memory system is automatically integrated into the bash orchestrator:

```javascript
import { memoryOperations } from './memory/memory-operations-hybrid.js';

// Add memory
await memoryOperations.add("User prefers dark roast coffee", userId);

// Search memories
const memories = await memoryOperations.search("coffee", userId);

// Get all memories
const all = await memoryOperations.getAll(userId);
```

## Files

- `memory-operations.js` - Original Mem0 Platform integration
- `memory-operations-local.js` - Local Mem0 OSS implementation
- `memory-operations-hybrid.js` - Hybrid with automatic fallback
- `mem0-local-config.js` - Local configuration
- `mem0-platform-config.js` - Platform configuration
- `test-*.js` - Test scripts for each implementation

## Testing

```bash
# Test Platform implementation
node server/memory/test-mem0-platform.js

# Test Local implementation  
node server/memory/test-local-mem0.js

# Test Hybrid implementation
node server/memory/test-hybrid-mem0.js
```

## Migration Notes

- The orchestrator now uses the hybrid approach by default
- API limits automatically trigger fallback to local storage
- Local storage requires sqlite3 native compilation
- All implementations share the same interface

## Future Improvements

1. **Enable Vector Stores**: Migrate from in-memory to Qdrant for persistence
2. **Smart Context**: Integrate with existing smart context loading
3. **Performance**: Optimize memory extraction and search
4. **Backup**: Implement memory export/import functionality
5. **Analytics**: Add memory usage metrics and insights