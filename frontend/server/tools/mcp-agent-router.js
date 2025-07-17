/**
 * MCP Agent Router - Intelligently routes tasks to appropriate MCP agents
 */

import { executePythonToolsTaskV2 } from '../agents/python-tools-agent-v2.js';
import { executeExternalMCPTask, hasExternalMCPTool } from '../agents/external-mcp-agent.js';
import { executeDocumentationQuery } from '../agents/documentation-mcp-agent.js';

/**
 * Analyze a task to determine which MCP agent(s) should handle it
 */
export function analyzeTaskForMCPRouting(task) {
  const taskLower = task.toLowerCase();
  
  // Keywords for different agent types
  const pythonKeywords = [
    'product', 'price', 'pricing', 'inventory', 'tag', 'image', 'variant',
    'shopify', 'sku', 'vendor', 'collection', 'metafield', 'feature',
    'sale', 'discount', 'miele', 'breville', 'map', 'redirect',
    'skuvault', 'open box', 'combo', 'bundle', 'memory', 'remember'
  ];
  
  const documentationKeywords = [
    'api', 'graphql', 'schema', 'documentation', 'docs', 'guide',
    'how to', 'what is', 'explain', 'mutation', 'query', 'type',
    'field', 'argument', 'example', 'reference', 'tutorial'
  ];
  
  const externalKeywords = [
    'fetch', 'website', 'web page', 'url', 'http', 'github',
    'repository', 'external', 'online', 'internet'
  ];
  
  // Score each agent type
  const scores = {
    python: 0,
    documentation: 0,
    external: 0
  };
  
  // Calculate scores based on keyword matches
  pythonKeywords.forEach(keyword => {
    if (taskLower.includes(keyword)) scores.python += 2;
  });
  
  documentationKeywords.forEach(keyword => {
    if (taskLower.includes(keyword)) scores.documentation += 2;
  });
  
  externalKeywords.forEach(keyword => {
    if (taskLower.includes(keyword)) scores.external += 2;
  });
  
  // Special patterns
  if (taskLower.match(/sku[- ]?\d+/i)) scores.python += 3;
  if (taskLower.includes('graphql') && taskLower.includes('schema')) scores.documentation += 3;
  if (taskLower.match(/https?:\/\//)) scores.external += 3;
  
  // Determine primary agent
  const maxScore = Math.max(scores.python, scores.documentation, scores.external);
  let primaryAgent = null;
  
  if (maxScore > 0) {
    if (scores.python === maxScore) primaryAgent = 'python';
    else if (scores.documentation === maxScore) primaryAgent = 'documentation';
    else if (scores.external === maxScore) primaryAgent = 'external';
  }
  
  // Check if multiple agents might be needed
  const significantScores = Object.values(scores).filter(s => s >= 2).length;
  const needsMultipleAgents = significantScores > 1;
  
  return {
    primaryAgent,
    scores,
    needsMultipleAgents,
    confidence: maxScore > 4 ? 'high' : maxScore > 2 ? 'medium' : 'low'
  };
}

/**
 * Route a task to the appropriate MCP agent(s)
 */
export async function routeToMCPAgent(task, context = {}) {
  const routing = analyzeTaskForMCPRouting(task);
  
  console.log('[MCP Router] Task analysis:', {
    task: task.substring(0, 100) + '...',
    routing
  });
  
  try {
    let result;
    
    // High confidence single agent routing
    if (routing.confidence === 'high' && !routing.needsMultipleAgents) {
      switch (routing.primaryAgent) {
        case 'python':
          console.log('[MCP Router] Routing to Python Tools Agent');
          result = await executePythonToolsTaskV2(task, context.conversationId, context.richContext);
          break;
          
        case 'documentation':
          console.log('[MCP Router] Routing to Documentation Agent');
          result = await executeDocumentationQuery(task, context.richContext);
          break;
          
        case 'external':
          console.log('[MCP Router] Routing to External MCP Agent');
          result = await executeExternalMCPTask(task, context.richContext);
          break;
      }
    }
    
    // Complex task that might need multiple agents
    if (!result && routing.needsMultipleAgents) {
      console.log('[MCP Router] Complex task detected, may need multiple agents');
      
      // For now, route to primary agent
      // Future: implement parallel execution or agent chaining
      if (routing.primaryAgent) {
        result = await routeToSpecificAgent(routing.primaryAgent, task, context);
      }
    }
    
    // Low confidence or no clear match
    if (!result) {
      // Check if any external tools might handle it
      if (await checkExternalToolAvailability(task)) {
        console.log('[MCP Router] Found matching external tool');
        result = await executeExternalMCPTask(task, context.richContext);
      } else {
        // Default to Python tools for Shopify-related tasks
        console.log('[MCP Router] No clear match, defaulting to Python Tools Agent');
        result = await executePythonToolsTaskV2(task, context.conversationId, context.richContext);
      }
    }
    
    // Check if the result indicates an error (graceful failure)
    if (result && result.success === false) {
      console.log('[MCP Router] Agent returned graceful error:', result.message);
      
      // If it was a timeout error, log additional info
      if (result.errorType === 'timeout') {
        console.log('[MCP Router] Timeout error detected - network issues or long-running task');
      }
      
      // Return the error result rather than throwing
      return result;
    }
    
    return result;
    
  } catch (error) {
    console.error('[MCP Router] Routing failed with unhandled error:', error);
    
    // Return a graceful error response instead of throwing
    return {
      success: false,
      error: error.message,
      errorType: 'routing',
      message: `MCP Router failed: ${error.message}`
    };
  }
}

/**
 * Route to a specific agent
 */
async function routeToSpecificAgent(agentType, task, context) {
  switch (agentType) {
    case 'python':
      return await executePythonToolsTaskV2(task, context.conversationId, context.richContext);
    case 'documentation':
      return await executeDocumentationQuery(task, context.richContext);
    case 'external':
      return await executeExternalMCPTask(task, context.richContext);
    default:
      throw new Error(`Unknown agent type: ${agentType}`);
  }
}

/**
 * Check if external tools can handle the task
 */
async function checkExternalToolAvailability(task) {
  // Extract potential tool names from task
  const toolPatterns = [
    /fetch\s+(?:from\s+)?(\S+)/i,
    /get\s+content\s+from\s+(\S+)/i,
    /read\s+(\S+)\s+website/i
  ];
  
  for (const pattern of toolPatterns) {
    if (pattern.test(task)) {
      // Check if fetch tool is available
      if (await hasExternalMCPTool('fetch')) {
        return true;
      }
    }
  }
  
  return false;
}

/**
 * Execute parallel MCP tasks
 */
export async function executeParallelMCPTasks(tasks, context = {}) {
  console.log(`[MCP Router] Executing ${tasks.length} tasks in parallel`);
  
  const taskPromises = tasks.map(async (task) => {
    try {
      const result = await routeToMCPAgent(task, context);
      return { task, result, success: true };
    } catch (error) {
      console.error(`[MCP Router] Task failed: ${task}`, error);
      return { task, error: error.message, success: false };
    }
  });
  
  return await Promise.all(taskPromises);
}