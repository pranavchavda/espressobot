/**
 * Documentation MCP Agent - Specialized for Shopify API documentation and schema introspection
 * Enhanced with Perplexity research and web search capabilities
 */

import { Agent, tool, webSearchTool } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { initializeTracing } from '../config/tracing-config.js';
import { z } from 'zod';
import { execSync } from 'child_process';

// Initialize tracing configuration for this agent
initializeTracing('Documentation MCP Agent');

let shopifyDevMCP = null;

// Cache for integrations MCP server connection
let integrationsMCP = null;

/**
 * Get or create connection to Integrations MCP server for Perplexity access
 */
async function getIntegrationsMCP() {
  if (!integrationsMCP) {
    const path = await import('path');
    const { fileURLToPath } = await import('url');
    const __dirname = path.dirname(fileURLToPath(import.meta.url));
    
    integrationsMCP = new MCPServerStdio({
      name: 'Integrations Server',
      command: 'python3',
      args: [path.join(__dirname, '../../python-tools/mcp-integrations-server.py')],
      env: {
        ...process.env,
        PYTHONPATH: path.join(__dirname, '../../python-tools')
      }
    });
    
    console.log('[Documentation Agent] Connecting to Integrations Server for Perplexity...');
    await integrationsMCP.connect();
    
    const tools = await integrationsMCP.listTools();
    console.log(`[Documentation Agent] Connected to Integrations Server! ${tools.length} tools available:`, 
      tools.map(t => t.name).join(', '));
  }
  
  return integrationsMCP;
}

/**
 * Create Perplexity research tool for documentation agent
 */
function createPerplexityTool() {
  return tool({
    name: 'perplexity_research',
    description: 'Research products, competitors, and industry information using Perplexity AI. Perfect for finding real-time information, technical specs, API updates, and best practices.',
    parameters: z.object({
      query: z.string().describe('Research query - be specific about what information you need'),
      model: z.enum(['sonar', 'sonar-pro']).default('sonar').describe('Perplexity model: sonar (fast) or sonar-pro (detailed)')
    }),
    execute: async ({ query, model }) => {
      try {
        console.log(`[Documentation Agent] Researching with Perplexity: ${query.substring(0, 100)}...`);
        
        // Get the integrations MCP server and call perplexity_research
        const mcpServer = await getIntegrationsMCP();
        const result = await mcpServer.callTool('perplexity_research', { query, model });
        
        return result.content?.[0]?.text || result;
        
      } catch (error) {
        console.error('[Documentation Agent] Perplexity research failed:', error.message);
        return `Perplexity research failed: ${error.message}`;
      }
    }
  });
}

/**
 * Create web search tool wrapper for documentation agent
 */
function createWebSearchTool() {
  return tool({
    name: 'web_search',
    description: 'Search the web for current information, documentation updates, API changes, and community discussions. Use for finding the latest information not in official docs.',
    parameters: z.object({
      query: z.string().describe('Web search query - be specific about what you\'re looking for')
    }),
    execute: async ({ query }) => {
      try {
        console.log(`[Documentation Agent] Web searching: ${query.substring(0, 100)}...`);
        
        const searchTool = webSearchTool();
        const result = await searchTool.execute({ query });
        
        return result;
        
      } catch (error) {
        console.error('[Documentation Agent] Web search failed:', error.message);
        return `Web search failed: ${error.message}`;
      }
    }
  });
}

/**
 * Get or create the Shopify Dev MCP server connection
 */
async function getShopifyDevMCP() {
  if (!shopifyDevMCP) {
    shopifyDevMCP = new MCPServerStdio({
      name: 'Shopify Dev Docs',
      fullCommand: 'npx -y @shopify/dev-mcp',
      cacheToolsList: true
    });
    
    console.log('[Documentation MCP Agent] Connecting to Shopify Dev MCP server...');
    await shopifyDevMCP.connect();
    
    const tools = await shopifyDevMCP.listTools();
    console.log(`[Documentation MCP Agent] Connected! ${tools.length} tools available:`, 
      tools.map(t => t.name).join(', '));
  }
  
  return shopifyDevMCP;
}

/**
 * Create a Documentation MCP Agent
 */
export async function createDocumentationMCPAgent(task = '', conversationId = null, richContext = null) {
  // Get the MCP server
  const mcpServer = await getShopifyDevMCP();
  
  // Build specialized instructions for documentation tasks
  let instructions = `You are a Documentation Agent specialized in Shopify API documentation, schema introspection, and real-time research.

You have access to the following tools:

**Official Documentation Tools:**
- introspect_admin_schema: Search and explore the Shopify Admin API GraphQL schema
- search_dev_docs: Search Shopify developer documentation for guides and examples
- fetch_docs_by_path: Retrieve specific documentation pages by path
- get_started: Get overview information about Shopify APIs

**Research & Discovery Tools:**
- perplexity_research: Research real-time information using Perplexity AI (best for technical specs, API updates, best practices)
- web_search: Search the web for current information, community discussions, and recent changes

Your enhanced role is to:
1. Help developers understand Shopify APIs and best practices
2. Find the correct GraphQL types, queries, and mutations
3. Provide code examples and implementation guidance
4. Research real-time information about API changes, community solutions, and best practices
5. Discover technical specifications and industry standards
6. Find current pricing, features, and competitor information when relevant
7. Explain API concepts and limitations with up-to-date context

**Tool Selection Strategy:**
- Use official documentation tools first for established APIs and concepts
- Use Perplexity for technical research, API updates, and best practices
- Use web search for community discussions, troubleshooting, and recent changes
- Combine multiple sources for comprehensive answers

When answering questions:
- Be precise and reference specific documentation
- Provide relevant code examples when available
- Include real-time context when helpful
- Explain both the "what" and the "why"
- Mention any important caveats or limitations
- Cross-reference official docs with current community knowledge

## AUTONOMOUS EXECUTION MODE
- Execute documentation queries immediately without asking for confirmation
- Use tools directly when you have clear questions
- Only ask questions if the request is unclear
- Provide comprehensive answers, not progress updates`;

  // Add context if provided
  if (richContext) {
    if (richContext.currentTask) {
      instructions += `\n\nCurrent Development Task: ${richContext.currentTask}`;
    }
    if (richContext.recentErrors) {
      instructions += `\n\nRecent Errors to Consider:\n${richContext.recentErrors.join('\n')}`;
    }
  }

  // Add the specific task
  if (task) {
    instructions += `\n\nDocumentation Request: ${task}`;
  }

  // Build final instructions with agency context
  const finalInstructions = await buildAgentInstructions(instructions, {
    agentRole: 'Documentation specialist',
    conversationId,
    taskDescription: task
  });

  // Create the enhanced tools
  const perplexityTool = createPerplexityTool();
  const webSearchTool = createWebSearchTool();

  // Create the agent with MCP server and additional tools
  const agent = new Agent({
    name: 'Documentation MCP Agent',
    instructions: finalInstructions,
    mcpServers: [mcpServer],
    tools: [perplexityTool, webSearchTool],
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a query with timeout and retry logic
 */
async function executeWithTimeout(agent, query, options = {}) {
  const { run } = await import('@openai/agents');
  const { maxTurns = 10, timeout = 120000, retries = 3 } = options; // 2 minute timeout, 3 retries
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(`[Documentation MCP Agent] Attempt ${attempt}/${retries} - Executing query with ${timeout/1000}s timeout...`);
      
      // Create a timeout promise
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error(`Query execution timed out after ${timeout/1000} seconds`));
        }, timeout);
      });
      
      // Race between the actual execution and timeout
      const executionPromise = run(agent, query, { maxTurns });
      const result = await Promise.race([executionPromise, timeoutPromise]);
      
      console.log('[Documentation MCP Agent] Query completed successfully');
      
      // Extract meaningful output instead of returning entire state
      let finalOutput = '';
      
      // Check for final output first
      if (result.finalOutput) {
        finalOutput = result.finalOutput;
      } 
      // Check for message outputs in generated items
      else if (result.state && result.state._generatedItems) {
        const messages = result.state._generatedItems
          .filter(item => item.type === 'message_output_item')
          .map(item => item.rawItem?.content?.[0]?.text || '')
          .filter(text => text);
        
        if (messages.length > 0) {
          finalOutput = messages[messages.length - 1];
        }
      }
      // Check for the new structure based on the example
      else if (result.state && result.state.currentStep && result.state.currentStep.output) {
        finalOutput = result.state.currentStep.output;
      }
      
      // Log token usage if available
      if (result.state?.context?.usage) {
        const usage = result.state.context.usage;
        console.log(`[Documentation MCP Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
      }
      
      return {
        success: true,
        result: finalOutput || 'Query completed but no output generated',
        agent: 'documentation',
        tokenUsage: result.state?.context?.usage || null
      };
      
    } catch (error) {
      const isTimeoutError = error.message.includes('timeout') || 
                           error.message.includes('terminated') || 
                           error.message.includes('ECONNRESET');
      
      console.log(`[Documentation MCP Agent] Attempt ${attempt} failed:`, error.message);
      
      if (isTimeoutError && attempt < retries) {
        const delay = Math.min(1000 * Math.pow(2, attempt - 1), 5000); // Exponential backoff, max 5s
        console.log(`[Documentation MCP Agent] Network/timeout error, retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      
      // If it's the last attempt or not a timeout error, throw it
      throw error;
    }
  }
}

/**
 * Execute a documentation query
 */
export async function executeDocumentationQuery(query, richContext = null) {
  try {
    console.log('[Documentation MCP Agent] Creating agent for query:', query.substring(0, 100) + '...');
    const agent = await createDocumentationMCPAgent(query, richContext);
    
    // Execute with timeout and retry logic
    return await executeWithTimeout(agent, query, {
      maxTurns: 10,
      timeout: 120000, // 2 minutes
      retries: 3
    });
    
  } catch (error) {
    console.error('[Documentation MCP Agent] Query failed after all retries:', error);
    
    // Return a graceful error response instead of throwing
    return {
      success: false,
      error: error.message,
      errorType: error.message.includes('timeout') ? 'timeout' : 'execution',
      message: `Documentation MCP Agent failed: ${error.message}`
    };
  }
}

/**
 * Quick schema introspection
 */
export async function introspectSchema(schemaQuery) {
  return executeDocumentationQuery(
    `Use introspect_admin_schema to find information about: ${schemaQuery}`
  );
}

/**
 * Search developer documentation
 */
export async function searchDocs(searchQuery) {
  return executeDocumentationQuery(
    `Search the Shopify developer documentation for: ${searchQuery}`
  );
}

/**
 * Get API overview for a specific area
 */
export async function getAPIOverview(api) {
  const validAPIs = ['admin', 'functions', 'hydrogen', 'storefront-web-components'];
  
  if (!validAPIs.includes(api)) {
    throw new Error(`Invalid API. Choose from: ${validAPIs.join(', ')}`);
  }
  
  return executeDocumentationQuery(
    `Use get_started to provide an overview of the ${api} API`
  );
}

/**
 * Close the MCP server connections
 */
export async function closeDocumentationMCP() {
  if (shopifyDevMCP) {
    console.log('[Documentation MCP Agent] Closing Shopify Dev MCP server...');
    await shopifyDevMCP.close();
    shopifyDevMCP = null;
  }
  
  if (integrationsMCP) {
    console.log('[Documentation MCP Agent] Closing Integrations MCP server...');
    await integrationsMCP.close();
    integrationsMCP = null;
  }
}