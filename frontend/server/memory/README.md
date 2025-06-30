# Memory System for EspressoBot

This directory contains the memory implementation for EspressoBot, providing persistent context across conversations.

## Current Implementation

The system is currently configured to use **Mem0 Platform** (hosted service) with the API key set in the environment.

Supported modes:

1. **Mem0 Platform (Active)** ✅ - Hosted service by Mem0
2. **Self-hosted Mem0** - Using local storage (has SQLite issues with pnpm)
3. **Simple Memory Store** - In-memory fallback with semantic search

## Setup

### Option 1: Mem0 Platform (Recommended)

1. Sign up at https://mem0.dev/pd-api
2. Get your API key from the dashboard
3. Set the environment variable:
   ```bash
   export MEM0_API_KEY="your-api-key"
   ```
4. Restart the server

The system will automatically use the platform when the API key is set.

### Option 2: Simple Memory Store (Default)

No setup required. The system automatically falls back to the simple in-memory store if no API key is provided.

**Note**: Memory is lost when the server restarts with this option.

## Features

- **Automatic Memory Extraction**: Uses GPT-4o-mini to extract important facts from conversations
- **Semantic Search**: Uses OpenAI embeddings for relevance-based memory retrieval
- **Cross-Conversation Persistence**: Memories are stored per user, accessible across all conversations
- **Smart Updates**: Avoids duplicate memories and updates existing ones when appropriate

## Architecture

```
memory/
├── mem0-platform-config.js  # Platform configuration
├── mem0-config.js          # Self-hosted configuration (backup)
├── memory-operations.js    # Main API interface
├── simple-memory-store.js  # Fallback implementation
└── README.md              # This file
```

## API Usage

```javascript
import { memoryOperations } from '../tools/memory-tool.js';

// Add memory
await memoryOperations.add(
  "User: I prefer dark roast coffee\nAssistant: Noted!",
  "user_123",
  { source: "chat" }
);

// Search memories
const results = await memoryOperations.search(
  "coffee preferences",
  "user_123",
  5
);

// Get all memories
const all = await memoryOperations.getAll("user_123");

// Reset memories
await memoryOperations.reset("user_123");
```

## Memory Tool for Agents

The memory system is also available as a tool for agents:

```javascript
import { memoryTool } from '../tools/memory-tool.js';

// Register with agent
agent.tools.push(memoryTool);
```

## Benefits

- **No Python Dependencies**: Pure JavaScript implementation
- **No Virtual Environment**: Runs in the same Node.js process
- **Better Performance**: No subprocess overhead
- **Type Safety**: Full TypeScript support
- **Production Ready**: Mem0 Platform handles scaling and reliability

## Migration from Python

We migrated from a Python-based mem0 implementation to JavaScript to:
- Eliminate subprocess overhead
- Remove virtual environment complexity
- Simplify deployment
- Improve error handling
- Enable better integration with the Node.js server

The API remains the same, so no changes are needed in the orchestrator or agents.