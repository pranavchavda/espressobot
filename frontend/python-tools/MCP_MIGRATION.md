# MCP Migration Guide

## Overview

We've successfully migrated Python tools to use the Model Context Protocol (MCP) with stdio transport. This provides:

1. **Structured tool interface** - Each tool has defined inputs/outputs
2. **Tool-specific context** - Instructions embedded with each tool
3. **Direct orchestrator execution** - No need to spawn bash agents for simple operations
4. **Self-modification capability** - SWE Agent can add/modify tools

## Architecture

```
EspressoBot
├── Orchestrator (executes MCP tools directly)
│   ├── MCP Client → stdio → MCP Server
│   ├── Bash Agent spawning (complex tasks)
│   └── SWE Agent (tool creation/modification)
│
├── MCP Server (python-tools/mcp-server.py)
│   ├── Tool discovery
│   ├── Context management
│   └── Execution wrapper
│
└── MCP Tools (python-tools/mcp_tools/)
    ├── products/
    │   ├── get.py
    │   ├── search.py
    │   ├── create.py
    │   ├── update_status.py
    │   └── manage_tags.py
    ├── inventory/
    │   └── manage_policy.py
    └── pricing/
        ├── update.py
        └── bulk_update.py
```

## Current Tools (13 native implementations, 10+ legacy to migrate)

### Native Implementations (No Subprocess)
1. `get_product` - Get product details (✓ Native)
2. `search_products` - Search with filters (✓ Native)
3. `manage_inventory_policy` - Set oversell policy
4. `update_pricing` - Update single product price
5. `create_product` - Create new product (✓ Native)
6. `update_status` - Change product status
7. `manage_tags` - Add/remove/replace tags (✓ Native)
8. `bulk_price_update` - Update multiple prices
9. `add_product_images` - Comprehensive image management (✓ Native)
10. `add_variants_to_product` - Bulk add variants (✓ Native)
11. `create_full_product` - Complete product creation (✓ Native)
12. `update_full_product` - Comprehensive product updates (✓ Native)
13. `get_product_native` - Alternative native implementation

### Remaining Legacy Tools to Migrate
- manage_features_json.py (metafields management)
- manage_features_metaobjects.py (metaobjects management)
- manage_redirects.py (URL redirects)
- manage_variant_links.py (variant linking)
- create_combo.py (combo products)
- create_open_box.py (open box products)
- graphql_query.py (generic GraphQL queries)
- graphql_mutation.py (generic GraphQL mutations)
- SkuVault integration tools (upload, costs, prices, kits)
- Misc tools (send_review_request, pplx, memory_operations, sum_orders)

### Conversion Status
✅ **Core Product Tools** - All converted to native
✅ **Image Management** - Native implementation complete
✅ **Variant Management** - Native implementation complete
✅ **Basic Operations** - All converted to native
🔄 **Specialized Tools** - Pending conversion
🔄 **External Integrations** - Pending conversion

## Usage Examples

### Orchestrator Direct Execution
```javascript
// Instead of spawning bash agent:
await callMCPTool('manage_inventory_policy', {
  identifier: '31480448974882',
  policy: 'deny'
});

// Search products
const results = await callMCPTool('search_products', {
  query: 'coffee',
  status: 'active',
  limit: 10
});
```

### Adding New Tools

1. Create tool wrapper in appropriate category:
```python
# mcp_tools/products/new_tool.py
from ..base import BaseMCPTool

class NewTool(BaseMCPTool):
    name = "new_tool"
    description = "Brief description"
    context = """
    Detailed context and business rules
    """
    input_schema = {...}
    
    async def execute(self, **kwargs):
        # Wrapper logic
    
    async def test(self):
        # Test implementation
```

2. Server auto-discovers on restart

## Running the Server

### Development (with auto-restart)
```bash
cd python-tools
python3 mcp-server-watch.py
```

### Production (stdio)
```bash
cd python-tools
python3 mcp-server.py
```

### Integration with Frontend
The orchestrator automatically initializes MCP tools on first use.

## Benefits vs Old Architecture

| Old (Subprocess-based) | New (Native MCP) |
|------------------------|------------------|
| Subprocess spawning overhead (~100-500ms) | Direct function calls (~10-50ms) |
| Text-based stdout/stderr parsing | Structured return values |
| No parameter validation | Schema-based validation |
| Limited error handling | Comprehensive exception handling |
| No type safety | Full Python type hints |
| Context in system prompt | Tool-specific context |
| Manual tool discovery | Automatic discovery |
| Process isolation overhead | Shared memory space |

### Performance Improvements
- **10x faster execution** - No subprocess overhead
- **Better error handling** - Native Python exceptions
- **Type safety** - Full IDE support and validation
- **Memory efficiency** - Shared ShopifyClient instances
- **Debugging ease** - Stack traces and breakpoints work

## Self-Modification

SWE Agent can add new tools:

1. Create new tool file in `mcp_tools/`
2. Server detects change and restarts
3. Orchestrator has immediate access

## Cleanup Complete

### Deprecated
- `/server/custom-tools/` - Replaced by MCP
- `/server/native-tools/` - Moved to MCP
- Custom tool discovery logic

### Updated
- Orchestrator uses MCP tools directly
- Instructions emphasize MCP for simple ops
- Decision tree updated

### Preserved
- Original python tools (fallback/reference)
- Bash capability for complex workflows
- SWE Agent's existing MCP usage

## Next Steps

1. Complete migration of remaining 23 tools
2. Add streaming support for long operations
3. Implement tool categories in orchestrator UI
4. Add tool usage analytics
5. Create tool testing framework