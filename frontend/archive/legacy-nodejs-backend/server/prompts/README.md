# Product Guidelines to System Prompts

This directory contains system prompts generated from product documentation, specifically for Shopify product creation tasks.

## Generated Files

- **`productCreation-system-prompt.txt`** - General product creation guidelines
- **`coffeeProducts-system-prompt.txt`** - Coffee-specific product guidelines  
- **`technical-system-prompt.txt`** - Technical API reference prompt
- **`combined-system-prompt.txt`** - All prompts combined
- **`product-guidelines-structured.json`** - Structured data for programmatic use

## Usage

### 1. Direct Integration in Agents

```javascript
import fs from 'fs/promises';

// Load a prompt
const productPrompt = await fs.readFile('./server/prompts/productCreation-system-prompt.txt', 'utf-8');

// Add to agent instructions
const agent = new Agent({
  instructions: baseInstructions + '\n\n' + productPrompt,
  // ... other config
});
```

### 2. Context-Aware Selection

```javascript
import { selectPromptForTask, loadPrompt } from '../tools/use-product-prompts-example.js';

// Automatically select the right prompt
const promptType = selectPromptForTask(userQuery);
const prompt = await loadPrompt(promptType);
```

### 3. RAG System Integration

```javascript
import { integrateWithRAG } from '../tools/use-product-prompts-example.js';

// Generate searchable fragments
const fragments = await integrateWithRAG();
// Add to your RAG system...
```

### 4. Structured Data Access

```javascript
import { loadStructuredData } from '../tools/use-product-prompts-example.js';

const data = await loadStructuredData();
// Access metafields, tags, principles, etc.
console.log(data.metafields);
console.log(data.tags);
```

## Regenerating Prompts

To regenerate prompts after updating product guidelines:

```bash
# JavaScript version
node server/tools/product-guidelines-to-prompt.js

# Python version  
python python-tools/product_guidelines_to_prompt.py
```

## Prompt Types

### Product Creation
- Complete guidelines for creating any product
- Includes all metafields, tags, and workflow steps
- Best for general product creation tasks

### Coffee Products
- Specialized for Escarpment Coffee Roasters products
- Includes coffee-specific tags and simplified requirements
- Skip certain sections (Buy Box, FAQs, etc.)

### Technical
- Focused on API implementation details
- Complete metafield reference
- GraphQL best practices

## Integration with SWE Agent

The SWE Agent can be enhanced with product guidelines:

```javascript
// In swe-agent-connected.js
const productContext = await ragSystemPromptManager.getSystemPrompt(
  "shopify product creation guidelines",
  { 
    basePrompt: baseInstructions + '\n\n' + productPrompt,
    // ... other options
  }
);
```

## Best Practices

1. **Select the right prompt** - Use coffee-specific prompts for coffee products
2. **Keep prompts updated** - Regenerate when guidelines change
3. **Use structured data** - For dynamic prompt generation
4. **Combine with RAG** - For better context retrieval
5. **Test with examples** - Verify prompts produce correct behavior

## Customization

To add new prompt types:

1. Update `PROMPT_SECTIONS` in the converter
2. Add new case in `createSystemPrompt()`
3. Implement section selection logic
4. Regenerate prompts

## Examples

See `server/tools/use-product-prompts-example.js` for complete integration examples.