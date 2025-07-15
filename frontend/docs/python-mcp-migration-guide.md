# Python MCP Tools Migration Guide

## Overview

This guide explains how to migrate from the current wrapped MCP tools pattern to the proper OpenAI SDK pattern where MCP servers are passed to agents.

## Current Architecture (Wrapped Tools)

Currently, Python MCP tools are wrapped as individual tools in the orchestrator:

```javascript
// Current pattern - tools are wrapped
const mcpTools = toolDefs.map(createMCPToolWrapper);
const orchestrator = new Agent({
  tools: [...mcpTools, ...otherTools]
});
```

## New Architecture (MCP Servers)

The proper OpenAI SDK pattern passes MCP servers directly to agents:

```javascript
// New pattern - MCP servers passed to agents
const pythonAgent = new Agent({
  mcpServers: [pythonMCPServer],
  instructions: 'You have access to Python tools...'
});
```

## Migration Options

### Option 1: Full Migration (Recommended)

Replace all wrapped MCP tools with dedicated agents:

1. **Python Tools Agent** (`python-tools-agent.js`)
   - Handles all Shopify operations
   - Proper MCP server integration
   - Rich context support

2. **External MCP Agents**
   - Create agents for each external MCP server
   - Pass servers via `mcpServers` array

### Option 2: Hybrid Approach

Use the Python Tools Executor as a bridge:

```javascript
import { executePythonTool, isPythonMCPTool } from './tools/python-tools-executor.js';

// In orchestrator tool execution
if (isPythonMCPTool(toolName)) {
  // Use agent pattern for Python tools
  return await executePythonTool(toolName, args, { conversationId, richContext });
} else {
  // Use existing pattern for other tools
  return await existingToolExecution(toolName, args);
}
```

## Benefits of Migration

1. **Better Compatibility**: Aligns with OpenAI SDK best practices
2. **Automatic Tool Discovery**: SDK handles tool schemas automatically
3. **Improved Error Handling**: Better integration with agent error handling
4. **Simplified Code**: No need for complex Zod schema conversions
5. **Future Proof**: Ready for SDK updates and new features

## Implementation Examples

### Using Python Tools Agent Directly

```javascript
import { executePythonToolsTask } from './agents/python-tools-agent.js';

// Search for products
const result = await executePythonToolsTask(
  'Search for coffee products with price under $50',
  conversationId,
  richContext
);

// Update product
const updateResult = await executePythonToolsTask(
  'Update product SKU-123 price to $29.99',
  conversationId,
  richContext
);
```

### Creating Custom MCP Agent

```javascript
import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';

// Create MCP server
const customServer = new MCPServerStdio({
  name: 'Custom MCP Server',
  command: 'uvx',
  args: ['mcp-server-custom'],
  cacheToolsList: true
});

// Connect and create agent
await customServer.connect();
const customAgent = new Agent({
  name: 'Custom Agent',
  mcpServers: [customServer],
  instructions: 'You have access to custom tools...'
});
```

## Testing the Migration

1. **Test Python Tools Agent**:
   ```bash
   node test-python-agent.js
   ```

2. **Test External MCP Servers**:
   ```bash
   node test-mcp-proper.js
   ```

## Rollback Plan

If issues arise, the wrapped tool pattern can coexist with the new pattern:
- Keep existing wrapped tools for stability
- Gradually migrate tools to agent pattern
- Test thoroughly before removing old code

## Next Steps

1. Test the Python tools agent in production scenarios
2. Monitor performance and error rates
3. Gradually migrate orchestrator to use agents
4. Update documentation and training materials
5. Remove deprecated wrapper code once stable

## Performance Considerations

- Agent pattern may have slightly higher latency for single tool calls
- Better for complex multi-tool operations
- Consider batching related operations
- Use tool result caching where appropriate

---

*This migration aligns EspressoBot with OpenAI SDK best practices and ensures compatibility with future updates.*