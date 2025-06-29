import { Agent, MCPServerStdio, tool } from '@openai/agents';
import { z } from 'zod';
import fs from 'fs/promises';
import path from 'path';
import { executeBashCommand } from '../tools/bash-tool.js';

/**
 * Tool for creating ad-hoc Python tools in tmp/ directory
 */
const createAdHocTool = tool({
  name: 'create_ad_hoc_tool',
  description: 'Create a temporary Python tool in the tmp/ directory for quick tasks',
  parameters: z.object({
    toolName: z.string().describe('Name for the tool file (without .py extension)'),
    code: z.string().describe('Complete Python code for the tool'),
    description: z.string().describe('Brief description of what the tool does')
  }),
  execute: async ({ toolName, code, description }) => {
    const tmpDir = '/home/pranav/espressobot/frontend/tmp';
    await fs.mkdir(tmpDir, { recursive: true });
    
    const tmpPath = `${tmpDir}/${toolName}.py`;
    
    const fullCode = `#!/usr/bin/env python3
"""
${description}
Created: ${new Date().toISOString()}
Type: Ad-hoc tool
"""

${code}`;
    
    await fs.writeFile(tmpPath, fullCode);
    await fs.chmod(tmpPath, 0o755);
    
    return {
      path: tmpPath,
      message: `Created ad-hoc tool at ${tmpPath}`,
      usage: `python3 ${tmpPath} [args]`
    };
  }
});

/**
 * Create a test MCP tool that simulates introspection
 */
const testIntrospectTool = tool({
  name: 'test_introspect_shopify_schema',
  description: 'Test tool that simulates Shopify schema introspection',
  parameters: z.object({
    typeName: z.string().describe('GraphQL type to introspect (e.g., ProductInput)')
  }),
  execute: async ({ typeName }) => {
    // Simulate what the real MCP would return
    if (typeName === 'ProductInput') {
      return {
        type: 'ProductInput',
        description: 'Input for creating or updating a product',
        fields: [
          { name: 'title', type: 'String!', required: true },
          { name: 'vendor', type: 'String', required: false },
          { name: 'productType', type: 'String', required: false },
          { name: 'status', type: 'ProductStatus', required: false },
          { name: 'tags', type: '[String!]', required: false }
        ]
      };
    }
    return { error: `Type ${typeName} not found` };
  }
});

/**
 * SWE Agent with MCP Test Configuration
 */
export const sweAgentMCPTest = new Agent({
  name: 'SWE_Agent_MCP_Test',
  instructions: `You are a test version of the Software Engineering Agent.

For this test, you have a mock introspection tool called 'test_introspect_shopify_schema' that simulates MCP functionality.

When asked to create a validation tool:
1. Use test_introspect_shopify_schema to get the ProductInput schema
2. Create a Python tool that validates products based on the schema
3. Save it as an ad-hoc tool in tmp/

This is a test to verify the pattern works before enabling real MCP servers.`,
  tools: [
    createAdHocTool,
    testIntrospectTool,
    tool({
      name: 'bash',
      description: 'Execute bash commands for testing tools',
      parameters: z.object({
        command: z.string(),
        cwd: z.string().nullable().default('/home/pranav/espressobot/frontend/python-tools')
      }),
      execute: executeBashCommand
    })
  ],
  model: 'gpt-4.1'  // Using standard model for testing
});

// Also create a version with real MCP for comparison
let mcpServers = null;

function getOrCreateMCPServers() {
  if (!mcpServers) {
    console.log('[SWE Agent MCP Test] Initializing MCP servers on first use...');
    
    const shopifyDevMCP = new MCPServerStdio({
      name: 'Shopify Dev Docs',
      fullCommand: 'npx -y @shopify/dev-mcp',
      cacheToolsList: true
    });
    
    // Don't connect here - let the SDK handle it
    mcpServers = [shopifyDevMCP];
  }
  return mcpServers;
}

export const sweAgentWithRealMCP = new Agent({
  name: 'SWE_Agent_Real_MCP',
  instructions: `You are the Software Engineering Agent with real MCP access.

You have access to Shopify Dev MCP server which provides:
- introspect_admin_schema: Introspect GraphQL schema types
- search_dev_docs: Search Shopify documentation
- fetch_docs_by_path: Get specific documentation
- get_started: Get API overview

Use these MCP tools when you need API information or schema details.`,
  tools: [
    createAdHocTool,
    tool({
      name: 'bash',
      description: 'Execute bash commands',
      parameters: z.object({
        command: z.string(),
        cwd: z.string().nullable().default('/home/pranav/espressobot/frontend/python-tools')
      }),
      execute: executeBashCommand
    })
  ],
  mcpServers: getOrCreateMCPServers(),
  model: 'gpt-4.1'
});