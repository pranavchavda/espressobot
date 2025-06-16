# Memory System Implementation Plan

## Overview
Implement a lightweight memory system for the Flask-Shopify bot that automatically saves important information and provides context for future conversations without relying on external vector databases.

## Architecture

### Phase 1: Core Memory System

#### 1. Memory Storage
- **JSON File Storage**: Store memories in a simple JSON file (`memories/user_memories.json`)
- **Structure**:
  ```json
  {
    "memories": [
      {
        "id": "mem_12345",
        "user_id": 1,
        "conversation_id": 123,
        "content": "User prefers dark theme for their store",
        "timestamp": "2024-01-15T10:30:00Z",
        "category": "preference",
        "embedding": [0.1, 0.2, ...], // OpenAI embedding vector
        "metadata": {
          "importance": "high",
          "source": "conversation"
        }
      }
    ]
  }
  ```

#### 2. Memory Agent (Parallel Execution)
- Create a `memory-agent.js` that runs in parallel with the main agent
- Monitors conversation for important information
- Categories to track:
  - User preferences
  - Store configuration details
  - Common tasks/workflows
  - Business context
  - Technical constraints

#### 3. Embedding Generation
- Use OpenAI's embeddings API (already available)
- Generate embeddings for each memory when created
- Store embeddings directly in the JSON file

#### 4. Semantic Search
- Implement simple cosine similarity search in JavaScript
- No external vector database needed
- Return top 3 most relevant memories for each query

### Phase 2: Database Integration (Optional)

#### 1. Prisma Schema Update
```prisma
model Memory {
  id            Int      @id @default(autoincrement())
  user_id       Int
  conversation_id Int?
  content       String
  category      String
  embedding     Json     // Store as JSON array
  importance    String
  created_at    DateTime @default(now())
  updated_at    DateTime @updatedAt
  
  @@index([user_id])
  @@index([category])
}
```

#### 2. Migration Path
- Start with JSON files
- Migrate to database when needed
- Keep the same interface for easy transition

## Implementation Steps

### Step 1: Memory Agent Creation
1. Create `/server/memory-agent.js`
2. Define memory detection logic
3. Implement parallel execution with main agent

### Step 2: Memory Storage
1. Create `/server/memory-store.js` for CRUD operations
2. Implement JSON file handling
3. Add memory categorization logic

### Step 3: Embedding Integration
1. Add embedding generation to memory creation
2. Implement cosine similarity function
3. Create semantic search functionality

### Step 4: Context Injection
1. Modify `unified-orchestrator.js` to:
   - Retrieve relevant memories before agent execution
   - Inject memories into agent context
   - Pass conversation to memory agent

### Step 5: Memory Management
1. Add memory pruning (keep most recent/important)
2. Implement memory deduplication
3. Add user controls for memory viewing/deletion

## Benefits of This Approach

1. **No External Dependencies**: Uses only OpenAI API (already integrated)
2. **Simple Storage**: JSON files are easy to backup/migrate
3. **Fast Performance**: In-memory search for small user base
4. **Easy Debugging**: Human-readable JSON format
5. **Gradual Scaling**: Can migrate to database when needed

## Future Enhancements

1. **Memory Clustering**: Group similar memories
2. **Memory Decay**: Reduce importance over time
3. **User Feedback**: Allow users to mark memories as important/outdated
4. **Export/Import**: Let users manage their memory data

## Technical Considerations

1. **File Locking**: Use proper file locking for concurrent access
2. **Memory Limits**: Set max memories per user (e.g., 1000)
3. **Backup Strategy**: Regular JSON file backups
4. **Privacy**: Ensure memories are user-scoped

## Example Memory Flow

1. User: "I prefer to use Helvetica font for all my product descriptions"
2. Memory Agent detects preference → Creates memory
3. Generates embedding for the memory
4. Saves to JSON file
5. Next conversation: User asks about product formatting
6. System retrieves relevant memories (including font preference)
7. Agent has context without user repeating preference

This approach provides a robust memory system suitable for a small user base while maintaining simplicity and avoiding external dependencies.