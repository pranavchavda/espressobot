# Shopify Dev MCP Integration

## Overview

The EspressoBot multi-agent system now includes direct integration with Shopify's official MCP server for documentation and schema access. This uses the OpenAI agents SDK's built-in MCP support.

## Implementation

### Direct MCP Integration

The OpenAI agents SDK supports MCP servers natively. We use the `MCPServerStdio` class to connect to the Shopify Dev MCP server:

```javascript
import { Agent, MCPServerStdio } from '@openai/agents';

// Create Shopify Dev MCP Server
const shopifyDevMCP = new MCPServerStdio({
  name: 'Shopify Dev Docs',
  fullCommand: 'npx -y @shopify/dev-mcp',
  cacheToolsList: true  // Cache tools list for performance
});

// Connect to the server
await shopifyDevMCP.connect();

// Add to agent
const agent = new Agent({
  name: 'Product_Agent',
  instructions: '...',
  tools: [...customTools],
  mcpServers: [shopifyDevMCP]  // MCP tools available alongside custom tools
});
```

## Available MCP Tools

The Shopify Dev MCP server provides these tools automatically:

1. **`search_dev_docs`** - Search Shopify documentation
   - Query: Search term for documentation
   - Returns: Relevant documentation snippets

2. **`introspect_admin_schema`** - Explore GraphQL schema
   - Type: GraphQL type name to introspect
   - Returns: Fields, connections, and mutations for the type

3. **`fetch_docs_by_path`** - Get specific documentation
   - Path: Documentation path (e.g., '/admin/api/2024-01/graphql')
   - Returns: Full documentation content

4. **`get_started`** - Overview of Shopify APIs
   - No parameters
   - Returns: Getting started guide

## Agent Integration

Both Product Creation and Product Update agents have access to these tools:

### Product Creation Agent
- Uses `introspect_admin_schema` to verify field types before creating products
- Uses `search_dev_docs` for best practices on metafields and product structure

### Product Update Agent  
- Uses `search_dev_docs` to find proper mutation syntax
- Uses `fetch_docs_by_path` for specific API documentation
- Uses `introspect_admin_schema` to check field types before updates

## Benefits

1. **Real-time Documentation**: Always up-to-date with latest Shopify API changes
2. **Schema Verification**: Prevent errors by checking types before operations
3. **Best Practices**: Agents can look up recommended approaches
4. **No Maintenance**: Shopify maintains the MCP server and documentation

## Testing

Run the test script to verify MCP integration:

```bash
node test-mcp-direct.js
```

## Architecture

```
┌─────────────────────┐
│   OpenAI Agent      │
├─────────────────────┤
│  - Custom Tools     │ ← Python tools, native tools
│  - MCP Tools        │ ← Shopify Dev MCP server
└─────────────────────┘
          │
          ├── Custom tool execution
          │
          └── MCP protocol → Shopify Dev MCP Server
                               - Documentation index
                               - GraphQL schema
                               - API references
```

## Key Advantages of Direct Integration

1. **Native Support**: Uses SDK's built-in MCP support - no custom wrappers
2. **Automatic Tool Discovery**: Tools are discovered dynamically from the MCP server
3. **Parallel Access**: MCP tools work alongside custom tools seamlessly
4. **Error Handling**: SDK handles MCP connection issues gracefully
5. **Performance**: Tool list caching reduces overhead

## Troubleshooting

If MCP tools aren't available:
1. Check npm package is installed: `npm list @shopify/dev-mcp`
2. Verify connection in logs: "Shopify Dev MCP server connection failed"
3. Test with: `npx -y @shopify/dev-mcp --help`
4. Agents will continue working without MCP (just without doc access)