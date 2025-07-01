import { Agent, MCPServerStdio, tool } from '@openai/agents';
import { z } from 'zod';
import fs from 'fs/promises';
import { executeBashCommand } from '../tools/bash-tool.js';

// Tool definitions (copied from main SWE agent since they're not exported)
const createAdHocTool = tool({
  name: 'create_adhoc_tool',
  description: 'Create a temporary Python tool for immediate use',
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

// Store MCP servers globally
let mcpServers = null;
let mcpInitialized = false;

/**
 * Initialize MCP servers with proper connection
 */
async function initializeMCPServers() {
  if (mcpInitialized) {
    return mcpServers;
  }
  
  // Get SSE emitter if available
  const sseEmitter = global.currentSseEmitter || null;
  
  console.log('[SWE Agent Connected] Initializing MCP servers...');
  if (sseEmitter) {
    sseEmitter('agent_processing', {
      agent: 'SWE_Agent_Connected',
      message: 'Initializing MCP servers...',
      status: 'initializing'
    });
  }
  
  try {
    const shopifyDevMCP = new MCPServerStdio({
      name: 'Shopify Dev Docs',
      fullCommand: 'npx -y @shopify/dev-mcp',
      cacheToolsList: true
    });
    
    // Connect to the server
    console.log('[SWE Agent Connected] Connecting to Shopify Dev MCP...');
    if (sseEmitter) {
      sseEmitter('agent_processing', {
        agent: 'SWE_Agent_Connected',
        message: 'Connecting to Shopify Dev MCP...',
        status: 'connecting'
      });
    }
    
    await shopifyDevMCP.connect();
    
    console.log('[SWE Agent Connected] ✓ Shopify Dev MCP connected');
    if (sseEmitter) {
      sseEmitter('agent_processing', {
        agent: 'SWE_Agent_Connected',
        message: '✓ Shopify Dev MCP connected',
        status: 'connected'
      });
    }
    
    mcpServers = [shopifyDevMCP];
    mcpInitialized = true;
    
    return mcpServers;
  } catch (error) {
    console.error('[SWE Agent Connected] Failed to initialize MCP:', error.message);
    if (sseEmitter) {
      sseEmitter('agent_processing', {
        agent: 'SWE_Agent_Connected',
        message: `Failed to initialize MCP: ${error.message}`,
        status: 'error'
      });
    }
    mcpServers = [];
    mcpInitialized = true;
    return [];
  }
}

/**
 * Create SWE Agent with connected MCP servers
 */
export async function createConnectedSWEAgent() {
  // Initialize MCP servers first
  const servers = await initializeMCPServers();
  
  // Create agent with connected servers
  const agent = new Agent({
    name: 'SWE_Agent_Connected',
    instructions: `You are a Software Engineering Agent with access to MCP servers.

You have access to Shopify Dev MCP which provides:
- introspect_admin_schema: Introspect GraphQL schema types
- search_dev_docs: Search Shopify documentation
- fetch_docs_by_path: Get specific documentation
- get_started: Get API overview

When creating tools that interact with Shopify APIs:
1. Use introspect_admin_schema to understand the GraphQL types
2. Use search_dev_docs to find best practices and examples
3. Create validation and helper tools based on actual schema

Your responsibilities:
1. Create new Python tools (both ad-hoc and permanent)
2. Use MCP tools to ensure accuracy with external APIs
3. Write comprehensive documentation
4. Ensure code quality and best practices`,
    tools: [
      webSearchTool(),
      createAdHocTool,
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
    mcpServers: servers,
    model: 'o3',
  });
  
  return agent;
}

// Export a function to clean up MCP connections
export async function cleanupMCPConnections() {
  if (mcpServers && mcpServers.length > 0) {
    console.log('[SWE Agent Connected] Cleaning up MCP connections...');
    for (const server of mcpServers) {
      try {
        await server.close();
      } catch (error) {
        console.error('[SWE Agent Connected] Error closing MCP server:', error.message);
      }
    }
    mcpServers = null;
    mcpInitialized = false;
  }
}
