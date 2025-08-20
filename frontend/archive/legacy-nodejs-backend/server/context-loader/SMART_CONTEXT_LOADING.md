# Smart Context Loading System

## Overview

The Smart Context Loading system analyzes user requests and agent tasks to intelligently load only relevant documentation, avoiding prompt bloat while ensuring agents have all necessary information.

## How It Works

### 1. Pattern Analysis
When a message comes in, the system analyzes it against predefined patterns:

```javascript
// Example patterns
PRODUCT_CREATION: [/create.*product/i, /new.*product/i, ...]
PRICING_UPDATES: [/update.*pric/i, /bulk.*pric/i, ...]
PREORDER_MANAGEMENT: [/preorder/i, /shipping.*nis/i, ...]
```

### 2. Context Selection
Based on matched patterns, relevant context sections are selected:

```javascript
// If message matches PREORDER_MANAGEMENT patterns, load:
- 'preorder-rules' from business rules
- 'inventory-management' tools documentation
- 'tag-management' workflows
```

### 3. Section Extraction
The system extracts only the relevant sections from documentation files:

```javascript
// Instead of loading entire TOOL_USAGE_GUIDE.md
// Only loads "### 🏷️ Tags & Metadata Tools" section
```

### 4. Memory Integration
If enabled, relevant memories are fetched from Mem0:

```javascript
// Searches for memories related to the task
// Adds them as "## Relevant Memories" section
```

## Benefits

### 1. **Reduced Token Usage**
- Only loads what's needed for the specific task
- Typical reduction: 10,000+ tokens → 1,000-3,000 tokens

### 2. **Better Focus**
- Agents aren't distracted by irrelevant information
- More accurate task completion

### 3. **Dynamic Adaptation**
- Context changes based on task requirements
- No manual prompt engineering needed

### 4. **Memory-Aware**
- Integrates learned patterns and user preferences
- Improves over time

## Usage Examples

### Example 1: Preorder Request
**User**: "Add the Breville machine to preorder with July shipping"

**Loaded Context**:
- Preorder management rules
- Tag conventions (preorder-2-weeks, shipping-nis-*)
- Inventory policy rules
- manage_tags.py documentation
- manage_inventory_policy.py documentation

### Example 2: Product Creation
**User**: "Create a new DeLonghi espresso machine"

**Loaded Context**:
- Product naming conventions
- Create_full_product.py documentation
- Metafields guide
- Features workflow (add one at a time)
- Canadian English reminder

### Example 3: Bulk Pricing
**User**: "Update prices for all grinders with 15% discount"

**Loaded Context**:
- Bulk_price_update.py documentation
- CSV format examples
- Pricing rules (CAD default, USD price list)
- Search syntax for finding products

## Configuration

### Adding New Patterns
Edit `context-manager.js`:

```javascript
CONTEXT_PATTERNS.NEW_CATEGORY = {
  patterns: [
    /pattern1/i,
    /pattern2/i
  ],
  contexts: [
    'context-key-1',
    'context-key-2'
  ]
};
```

### Adding New Context Sources
```javascript
CONTEXT_FILES['new-context-key'] = {
  file: '../path/to/doc.md',
  section: '## Section Header'  // Optional
};
```

## Testing

Run the test script to see context loading in action:

```bash
node server/test-smart-context.js
```

This shows:
- What patterns match your message
- Which contexts are loaded
- Preview of loaded content

## Integration Points

### 1. Bash Agents
```javascript
// In createBashAgent()
const smartContext = await getSmartContext(task, {
  taskDescription: task,
  includeMemory: true
});
```

### 2. Dynamic Orchestrator
```javascript
// In runDynamicOrchestrator()
const smartContext = await getSmartContext(message, {
  includeMemory: true
});
```

### 3. Custom Usage
```javascript
import { getSmartContext } from './context-loader/context-manager.js';

const context = await getSmartContext("your message here", {
  includeMemory: true,
  taskDescription: "optional task description"
});
```

## Performance Considerations

1. **Caching**: File reads are fast, but consider caching for high-frequency operations
2. **Pattern Matching**: Regex patterns are efficient, but keep them simple
3. **Memory Searches**: May add 100-500ms depending on Mem0 configuration
4. **Section Extraction**: Optimized for markdown structure

## Future Enhancements

1. **Learning Patterns**: Track which contexts lead to successful completions
2. **User Preferences**: Remember user-specific context preferences
3. **Context Scoring**: Rank contexts by relevance
4. **Lazy Loading**: Load additional context on-demand during execution

## Troubleshooting

### Context Not Loading
1. Check pattern matches your message
2. Verify context file exists
3. Check section header matches exactly

### Too Much Context
1. Make patterns more specific
2. Break large sections into smaller ones
3. Use section extraction instead of full files

### Memory Not Working
1. Ensure Mem0 is running
2. Check MEM0_API_KEY is set
3. Verify memories exist for the search term