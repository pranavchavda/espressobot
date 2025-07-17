/**
 * Direct MCP Agent Tools for EspressoBot1
 * Allows the orchestrator to directly execute MCP agent tasks without the spawn_mcp_agent middleman
 */

import { z } from 'zod';
import { tool } from '@openai/agents';
import { analyzeTaskForMCPRouting } from './mcp-agent-router.js';
import { executePythonToolsTaskV2 } from '../agents/python-tools-agent-v2.js';
import { executeExternalMCPTask } from '../agents/external-mcp-agent.js';
import { executeDocumentationQuery } from '../agents/documentation-mcp-agent.js';

/**
 * Create the Python Tools MCP agent tool
 */
export function createPythonToolsAgentTool() {
  return tool({
    name: 'python_tools_agent',
    description: 'Execute Shopify operations using Python Tools MCP agent',
    parameters: z.object({
      task: z.string().describe('The Shopify operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Python Tools Agent] Executing task: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executePythonToolsTaskV2(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || result.message || 'Unknown error'}`;
        }
        
        // Return the actual result content, not a wrapper object
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Python Tools Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Create the Documentation MCP agent tool
 */
export function createDocumentationAgentTool() {
  return tool({
    name: 'documentation_agent',
    description: 'Query Shopify API documentation and schema',
    parameters: z.object({
      query: z.string().describe('The documentation query or schema search')
    }),
    execute: async ({ query }) => {
      console.log(`[Documentation Agent] Querying: ${query.substring(0, 100)}...`);
      
      try {
        const result = await executeDocumentationQuery(query, {});
        
        if (result && result.success === false) {
          return `Error: ${result.error || result.message || 'Unknown error'}`;
        }
        
        // Return the actual result content, not a wrapper object
        return result.result || result || 'Query completed successfully';
        
      } catch (error) {
        console.error(`[Documentation Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Create the External MCP agent tool
 */
export function createExternalMCPAgentTool() {
  return tool({
    name: 'external_mcp_agent',
    description: 'Execute external MCP server operations',
    parameters: z.object({
      task: z.string().describe('The external operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[External MCP Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeExternalMCPTask(task, {});
        
        if (result && result.success === false) {
          return `Error: ${result.error || result.message || 'Unknown error'}`;
        }
        
        // Return the actual result content, not a wrapper object
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[External MCP Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Create smart MCP router tool that analyzes and routes to the best agent
 */
export function createSmartMCPRouterTool() {
  return tool({
    name: 'smart_mcp_execute',
    description: 'Intelligently route tasks to the appropriate MCP agent based on content analysis',
    parameters: z.object({
      task: z.string().describe('The task to execute'),
      preferred_agent: z.enum(['python', 'documentation', 'external', 'auto'])
        .default('auto')
        .describe('Optionally force a specific agent')
    }),
    execute: async ({ task, preferred_agent }) => {
      console.log(`[Smart MCP Router] Analyzing task: ${task.substring(0, 100)}...`);
      
      // Analyze the task if auto mode
      let agent = preferred_agent;
      if (agent === 'auto') {
        const routing = analyzeTaskForMCPRouting(task);
        console.log(`[Smart MCP Router] Analysis:`, routing);
        agent = routing.primaryAgent || 'python';
      }
      
      try {
        let result;
        
        switch (agent) {
          case 'python':
            console.log('[Smart MCP Router] Routing to Python Tools Agent');
            result = await executePythonToolsTaskV2(task, global.currentConversationId, {});
            break;
            
          case 'documentation':
            console.log('[Smart MCP Router] Routing to Documentation Agent');
            result = await executeDocumentationQuery(task, {});
            break;
            
          case 'external':
            console.log('[Smart MCP Router] Routing to External MCP Agent');
            result = await executeExternalMCPTask(task, {});
            break;
            
          default:
            // Fallback to Python tools
            console.log('[Smart MCP Router] Unknown agent, defaulting to Python Tools');
            result = await executePythonToolsTaskV2(task, global.currentConversationId, {});
        }
        
        if (result && result.success === false) {
          return `Error (${agent} agent): ${result.error || result.message || 'Unknown error'}`;
        }
        
        // Return the actual result content, not a wrapper object
        const response = result.result || result || 'Task completed successfully';
        return `[${agent} agent] ${response}`;
        
      } catch (error) {
        console.error(`[Smart MCP Router] Failed with ${agent} agent:`, error);
        return `Error (${agent} agent): ${error.message}`;
      }
    }
  });
}