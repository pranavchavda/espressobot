# Native JavaScript Tools for Shopify

This directory contains native JavaScript implementations of Shopify tools, replacing the Python subprocess-based tools for better performance and easier debugging.

## Overview

Native tools provide direct JavaScript implementations of Shopify operations, eliminating the overhead of spawning Python processes and providing better integration with the Node.js backend.

## Architecture

```
native-tools/
├── base-tool.js          # Base class for all native tools
├── index.js              # Tool registry and exports
├── search-products.js    # Product search implementation
├── get-product.js        # Get product details
├── update-pricing.js     # Update product/variant pricing
├── manage-tags.js        # Add/remove product tags
├── update-status.js      # Update product status
└── README.md            # This file
```

## Usage

### Enabling Native Tools

Set the environment variable to enable native tools:
```bash
USE_NATIVE_TOOLS=true
```

When enabled, native tools will replace their Python counterparts automatically.

### Testing Native Tools

Run the test script to compare native vs Python tool performance:
```bash
node test-native-tools.js
```

## Tool Implementations

### Core Tools

1. **search_products** - Search for products using Shopify's search syntax
   - Supports all Shopify search operators (tag:, vendor:, status:, etc.)
   - Configurable fields to return
   - ~100-500ms faster than Python version

2. **get_product** - Get detailed product information
   - Supports lookup by ID, handle, or SKU
   - Returns comprehensive product data including variants, images, metafields
   - Handles nested data transformation

3. **update_pricing** - Update product or variant pricing
   - Updates price, compare_at_price, and cost
   - Supports bulk variant updates when only product_id is provided
   - Handles inventory item cost updates separately

4. **manage_tags** - Add or remove tags from products
   - Intelligent tag deduplication
   - Case-insensitive tag matching
   - Returns detailed change information

5. **update_product_status** - Update product status
   - Supports ACTIVE, DRAFT, ARCHIVED statuses
   - Includes convenience methods for publish/unpublish/archive

### Benefits

1. **Performance**: 100-500ms faster per operation (no subprocess overhead)
2. **Debugging**: Direct JavaScript stack traces and error messages
3. **Integration**: Better integration with Node.js async/await patterns
4. **Type Safety**: Can add TypeScript support in the future
5. **Testing**: Easier to unit test with Jest or similar frameworks

### Migration Status

✅ **Migrated to Native:**
- search_products
- get_product
- update_pricing
- manage_tags (includes add_tags_to_product, remove_tags_from_product)
- update_product_status

🔄 **Planned for Migration:**
- create_full_product
- bulk_price_update
- manage_inventory_policy
- graphql_query / graphql_mutation

⏸️ **Keep in Python (Complex Dependencies):**
- create_combo (uses PIL for image processing)
- upload_to_skuvault (external API with complex auth)
- pplx (Perplexity AI integration)

## Development Guide

### Creating a New Native Tool

1. Create a new file in `native-tools/` directory
2. Extend the `BaseTool` class
3. Define metadata with name, description, and inputSchema
4. Implement the `execute` method
5. Export a singleton instance
6. Add to `index.js` exports

Example:
```javascript
import { BaseTool } from './base-tool.js';

export class MyNewTool extends BaseTool {
  get metadata() {
    return {
      name: 'my_new_tool',
      description: 'Description of what the tool does',
      inputSchema: {
        type: 'object',
        properties: {
          param1: { type: 'string', description: 'Parameter description' }
        },
        required: ['param1']
      }
    };
  }

  async execute(args) {
    // Implementation here
    return result;
  }
}

export const myNewTool = new MyNewTool();
```

### Error Handling

Native tools use the base class error handling which:
- Validates input arguments against schema
- Catches and formats errors consistently
- Provides debug logging when DEBUG=true
- Returns standardized success/error responses

### Testing

Each tool should have corresponding tests. Use the test pattern:
```javascript
// Test native tool
const result = await tool.run({ /* args */ });
console.assert(result.success === true);
```

## Environment Variables

Required:
- `SHOPIFY_SHOP_URL` - Your Shopify store URL
- `SHOPIFY_ACCESS_TOKEN` - Admin API access token

Optional:
- `USE_NATIVE_TOOLS=true` - Enable native tools
- `DEBUG=true` - Enable debug logging

## Performance Comparison

Typical performance improvements:
- **search_products**: ~300ms (Python) → ~50ms (Native)
- **get_product**: ~250ms (Python) → ~40ms (Native)
- **update_pricing**: ~400ms (Python) → ~80ms (Native)
- **manage_tags**: ~350ms (Python) → ~60ms (Native)

Times vary based on network latency and Shopify API response times.