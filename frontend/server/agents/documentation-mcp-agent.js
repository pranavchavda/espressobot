/**
 * Documentation MCP Agent - Specialized for Shopify API documentation and schema introspection
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';

let shopifyDevMCP = null;

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
export async function createDocumentationMCPAgent(task = '', richContext = null) {
  // Get the MCP server
  const mcpServer = await getShopifyDevMCP();
  
  // Build specialized instructions for documentation tasks
  let instructions = `You are a Documentation Agent specialized in Shopify API documentation and GraphQL schema introspection.

You have access to the following documentation tools:
- introspect_admin_schema: Search and explore the Shopify Admin API GraphQL schema
- search_dev_docs: Search Shopify developer documentation for guides and examples
- fetch_docs_by_path: Retrieve specific documentation pages by path
- get_started: Get overview information about Shopify APIs

Your role is to:
1. Help developers understand Shopify APIs and best practices
2. Find the correct GraphQL types, queries, and mutations
3. Provide code examples and implementation guidance
4. Explain API concepts and limitations

When answering questions:
- Be precise and reference specific documentation
- Provide relevant code examples when available
- Explain both the "what" and the "why"
- Mention any important caveats or limitations`;

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

  // Create the agent
  const agent = new Agent({
    name: 'Documentation MCP Agent',
    instructions: instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4o',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a documentation query
 */
export async function executeDocumentationQuery(query, richContext = null) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Documentation MCP Agent] Creating agent for query:', query.substring(0, 100) + '...');
    const agent = await createDocumentationMCPAgent(query, richContext);
    
    console.log('[Documentation MCP Agent] Executing query...');
    const result = await run(agent, query, { maxTurns: 10 });
    
    console.log('[Documentation MCP Agent] Query completed successfully');
    return result;
    
  } catch (error) {
    console.error('[Documentation MCP Agent] Query failed:', error);
    throw error;
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
 * Close the Shopify Dev MCP server connection
 */
export async function closeDocumentationMCP() {
  if (shopifyDevMCP) {
    console.log('[Documentation MCP Agent] Closing Shopify Dev MCP server...');
    await shopifyDevMCP.close();
    shopifyDevMCP = null;
  }
}