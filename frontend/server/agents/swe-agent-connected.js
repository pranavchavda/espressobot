import { Agent, MCPServerStdio, tool, webSearchTool } from '@openai/agents';
import { z } from 'zod';
import { setTracingDisabled } from '@openai/agents-core';
import fs from 'fs/promises';

// Disable tracing to prevent 7MB span output errors
setTracingDisabled(true);
import { executeBashCommand } from '../tools/bash-tool.js';
import { learningTool, reflectAndLearnTool } from '../tools/learning-tool.js';

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
export async function createConnectedSWEAgent(task = '', conversationId = null, richContext) {
  // richContext is now REQUIRED - orchestrator must provide context
  if (!richContext) {
    throw new Error('[SWE Agent Connected] richContext is required. Orchestrator must provide context.');
  }
  
  // Initialize MCP servers first
  const servers = await initializeMCPServers();
  
  console.log(`[SWE Agent Connected] Using orchestrator-provided rich context`);
  
  // Import the prompt builder from bash-tool
  const { buildPromptFromRichContext } = await import('../tools/bash-tool.js');
  const contextualPrompt = buildPromptFromRichContext(richContext);
  
  const instructions = contextualPrompt + `

## Software Engineering Agent Capabilities

You are the SWE agent for EspressoBot with access to MCP servers for real-time API information.

### MCP Access:
You have access to Shopify Dev MCP which provides:
- **introspect_admin_schema**: Introspect GraphQL schema types
- **search_dev_docs**: Search Shopify documentation
- **fetch_docs_by_path**: Get specific documentation
- **get_started**: Get API overview 

### Your Responsibilities:
1. Create new Python tools (both ad-hoc and permanent)
2. Use MCP tools to ensure accuracy with external APIs
3. Write comprehensive documentation
4. Ensure code quality and best practices
5. Validate GraphQL queries against live schema before execution

### Best Practices:
- Before executing any GraphQL queries, perform live schema validation
- If validation errors occur, report clear error messages with actionable suggestions
- Use introspect_admin_schema to understand GraphQL types
- Use search_dev_docs to find best practices and examples
- Create validation and helper tools based on actual schema
- All schema validation and query execution should be logged

Your specific task: ${task}`;
  
  // Create agent with connected servers
  const agent = new Agent({
    name: 'SWE_Agent_Connected',
    instructions: instructions,
    tools: [
      tool({
        name: 'web_search',
        description: 'Search the web for information',
        parameters: z.object({
          query: z.string().describe('Search query')
        }),
        execute: async (args) => {
          try {
            const tool = webSearchTool();
            return await tool.execute(args);
          } catch (error) {
            return JSON.stringify({ error: `Web search failed: ${error.message}` });
          }
        }
      }),
      createAdHocTool,
      tool({
        name: 'bash',
        description: 'Execute bash commands for testing tools',
        parameters: z.object({
          command: z.string(),
          cwd: z.string().nullable().default('/home/pranav/espressobot/frontend/python-tools')
        }),
        execute: executeBashCommand
      }),
      learningTool,
      reflectAndLearnTool
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