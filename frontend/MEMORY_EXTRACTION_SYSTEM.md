# Memory Extraction System

## Overview
We've implemented an intelligent memory extraction system that uses GPT-4.1-mini (or GPT-4.1-nano) to extract key facts from conversations and store them as embeddings for semantic search.

## Key Features

### 1. Intelligent Fact Extraction
- Uses GPT-4.1-mini/nano to extract important facts as single sentences
- Each fact is self-contained and understandable without context
- Extracts user preferences, personal details, business context, and decisions
- Ignores small talk and transient information
- Maximum 10 facts per conversation to keep it focused

### 2. Model Flexibility
- Default: GPT-4.1-mini for better extraction quality
- Option: GPT-4.1-nano for cost-effective extraction
- Configurable via environment variable: `USE_GPT_NANO_FOR_MEMORY=true`
- Can be set per-extraction via context parameter

### 3. Deduplication
- Checks for similar memories before storing (85% similarity threshold)
- Uses cosine similarity on embeddings to detect duplicates
- Prevents storing redundant information
- Checks against the 50 most recent memories for efficiency

### 4. Storage Format
Each extracted fact is stored as:
- **Content**: Single, self-contained sentence
- **Embedding**: OpenAI text-embedding-3-small vector
- **Metadata**: 
  - Timestamp
  - Conversation ID
  - Agent name
  - Source model (gpt-4.1-mini/nano)
  - Extraction source

## Example Extractions

From this conversation:
```
User: Hi, my name is Pranav and I manage the iDrinkCoffee.com store. 
      I particularly enjoy Ethiopian Yirgacheffe coffee.
Assistant: Hello Pranav! It's great to meet you...
User: Yes, we do! We offer 15% bulk discounts on combo products. 
      By the way, who is the CEO?
Assistant: The CEO of iDrinkCoffee.com is Slawek Janicki...
```

Extracted facts:
1. The user's name is Pranav.
2. Pranav manages the iDrinkCoffee.com store.
3. Pranav particularly enjoys Ethiopian Yirgacheffe coffee.
4. iDrinkCoffee.com offers 15% bulk discounts on combo products.
5. The CEO of iDrinkCoffee.com is Slawek Janicki.

## Integration with Bash Orchestrator

The system automatically extracts and stores memories after each conversation:
1. Conversation completes
2. GPT-4.1-mini/nano extracts facts
3. Each fact is checked for duplicates
4. Non-duplicate facts are stored with embeddings
5. Facts are available for future conversations

## Cost Comparison

### GPT-4.1-mini
- Better extraction quality
- More nuanced understanding
- Recommended for important conversations

### GPT-4.1-nano
- Very cost-effective
- Good for basic fact extraction
- Suitable for high-volume usage

## Usage

### Automatic (in bash orchestrator)
Facts are automatically extracted and stored after each conversation.

### Manual Testing
```javascript
// Extract facts from a conversation
const facts = await memoryOperations.extractMemorySummary(conversationText, {
  conversationId: 'test-1',
  agent: 'test',
  useNano: false  // Set to true for nano model
});

// Store each fact
for (const fact of facts) {
  await memoryOperations.add(fact.content, userId, fact.metadata);
}
```

### Retrieval
```bash
# Via Python CLI
python3 memory_operations.py search "coffee preferences"

# Via JavaScript
const memories = await memoryOperations.search("coffee preferences", userId);
```

## Benefits

1. **Context Persistence**: Important facts persist across conversations
2. **Semantic Search**: Find relevant memories based on meaning, not keywords
3. **User Personalization**: Each user has their own memory space
4. **Efficient Storage**: Deduplication prevents memory bloat
5. **Cost Control**: Choose between quality (mini) and cost (nano)

## Configuration

Set model preference:
```bash
# Use nano for all memory extraction
export USE_GPT_NANO_FOR_MEMORY=true
```

Or set per-extraction:
```javascript
const facts = await extractMemorySummary(text, { useNano: true });
```