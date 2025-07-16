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
- Mention any important caveats or limitations

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
      return result;
      
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
 * Close the Shopify Dev MCP server connection
 */
export async function closeDocumentationMCP() {
  if (shopifyDevMCP) {
    console.log('[Documentation MCP Agent] Closing Shopify Dev MCP server...');
    await shopifyDevMCP.close();
    shopifyDevMCP = null;
  }
}