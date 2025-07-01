# Strong Memory Deduplication System

## Overview
We've implemented a multi-layered deduplication system that prevents storing duplicate or highly similar memories using multiple strategies.

## Deduplication Strategies

### 1. **Exact Match Check** (Fastest)
- Case-insensitive exact string comparison
- Catches identical memories regardless of capitalization
- Example: "The user's name is Pranav." = "THE USER'S NAME IS PRANAV."

### 2. **Fuzzy Match Check** 
- Normalizes text by removing punctuation and extra whitespace
- Uses Jaccard similarity index on word sets
- Threshold: 90% similarity
- Example: "The user's name is Pranav!" ≈ "The users name is Pranav"

### 3. **Key Phrase Detection**
- Extracts important phrases:
  - Quoted text: "Ethiopian Yirgacheffe"
  - Email addresses: user@example.com
  - Names: Pranav Chavda, Slawek Janicki
  - Patterns: $29.99, 15%, 2025-06-30
- Checks if key phrases already exist in memories
- Logs warnings but continues to semantic check

### 4. **Semantic Similarity Check** (Most Accurate)
- Uses OpenAI embeddings to compare meaning
- Cosine similarity threshold: 85%
- Checks against 200 most recent memories
- Catches paraphrases and related content
- Example: "Pranav is the user's name" ≈ "The name of the user is Pranav"

## Test Results

From 18 test memories:
- **8 stored successfully** (unique facts)
- **10 rejected as duplicates**:
  - 3 exact matches
  - 3 fuzzy matches
  - 4 semantic matches

### Examples of Caught Duplicates:
1. **Exact**: "The user's name is Pranav." = "the user's name is pranav."
2. **Fuzzy**: "The user's name is Pranav!" ≈ "The users name is Pranav"
3. **Semantic**: "The user likes Ethiopian coffee" ≈ "The user prefers Ethiopian Yirgacheffe coffee"

## Memory Consolidation

The system can also merge related memories:

### Before Consolidation:
- "The user's name is Pranav and he manages iDrinkCoffee.com."
- "Pranav manages the iDrinkCoffee.com store."

### After Consolidation:
- "Pranav manages the iDrinkCoffee.com store."

## Configuration Options

```javascript
await isDuplicate(content, userId, {
  semanticThreshold: 0.85,    // Semantic similarity threshold
  exactMatchCheck: true,       // Enable exact string matching
  fuzzyMatchCheck: true,       // Enable fuzzy text matching
  keyPhraseCheck: true,        // Enable key phrase detection
  checkAllMemories: false,     // Check all vs recent memories
  recentLimit: 200            // Number of recent memories to check
});
```

## Performance Considerations

1. **Exact match**: O(1) - Single database query
2. **Fuzzy match**: O(n) - Checks recent memories
3. **Key phrases**: O(k) - Checks each extracted phrase
4. **Semantic**: O(n) - Embedding generation + comparisons

The system runs checks in order of performance, failing fast on exact/fuzzy matches before expensive semantic comparison.

## Benefits

1. **Storage Efficiency**: Prevents memory bloat from duplicates
2. **Better Context**: Consolidated facts are cleaner and more useful
3. **Flexible Control**: Multiple strategies catch different types of duplicates
4. **Performance**: Fast checks before expensive operations
5. **Transparency**: Clear logging shows why memories were rejected

## Usage in Production

The deduplication runs automatically when:
1. Facts are extracted from conversations
2. Memories are added via the memory tool
3. Bulk imports or migrations occur

No configuration needed - it works out of the box with sensible defaults.