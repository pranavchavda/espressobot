/**
 * Spawn MCP Agent Tool - Allows orchestrator to delegate tasks to specialized MCP agents
 */

import { z } from 'zod';
import { tool } from '@openai/agents';
import { routeToMCPAgent, analyzeTaskForMCPRouting } from './mcp-agent-router.js';

/**
 * Create the spawn MCP agent tool for the orchestrator
 */
export function createSpawnMCPAgentTool() {
  return tool({
    name: 'spawn_mcp_agent',
    description: `Spawn a specialized MCP agent to handle tasks requiring Model Context Protocol tools.

Use this tool for:
- Shopify operations (products, pricing, inventory, etc.) - routes to Python Tools Agent
- API documentation queries - routes to Documentation Agent  
- External tool operations (fetch, GitHub, etc.) - routes to External MCP Agent

The MCP agent router will automatically determine the best agent based on the task.

This is preferred over direct tool usage for:
- Complex multi-step operations
- Tasks requiring specialized context
- Operations that benefit from agent-level error handling`,
    
    parameters: z.object({
      task: z.string().describe('The task for the MCP agent to complete'),
      context: z.object({
        conversation_id: z.string().nullable().default(null).describe('Conversation ID for context'),
        user_profile: z.string().nullable().default(null).describe('User profile information'),
        relevant_memories: z.array(z.string()).nullable().default(null).describe('Relevant context from memory'),
        recent_products: z.array(z.object({
          title: z.string(),
          sku: z.string()
        })).nullable().default(null).describe('Recently accessed products'),
        current_task: z.string().nullable().default(null).describe('Current development task for documentation queries'),
        bulk_items: z.array(z.union([z.string(), z.object({
          name: z.string().nullable().default(null),
          type: z.string().nullable().default(null),
          vendor: z.string().nullable().default(null),
          sku: z.string().nullable().default(null),
          title: z.string().nullable().default(null),
          description: z.string().nullable().default(null)
        }).strict()])).nullable().default(null).describe('Items to process in bulk operations (strings or objects)'),
        bulk_operation_type: z.string().nullable().default(null).describe('Type of bulk operation (create, update, etc.)'),
        bulk_progress: z.object({
          total: z.number(),
          completed: z.number(),
          current_index: z.number()
        }).nullable().default(null).describe('Progress tracking for bulk operations')
      }).nullable().default(null).describe('Optional context for the agent')
    }),
    
    execute: async ({ task, context }) => {
      console.log(`[Spawn MCP Agent] Delegating task to MCP agent: ${task.substring(0, 100)}...`);
      
      // Analyze the task first
      const routing = analyzeTaskForMCPRouting(task);
      console.log(`[Spawn MCP Agent] Routing analysis:`, routing);
      
      try {
        // Build rich context from the input
        const richContext = context ? {
          userProfile: context.user_profile,
          relevantMemories: context.relevant_memories || [],
          recentProducts: context.recent_products || [],
          currentTask: context.current_task,
          currentTasks: null, // Will be populated if available
          bulkItems: context.bulk_items || null,
          bulkOperationType: context.bulk_operation_type || null,
          bulkProgress: context.bulk_progress || null
        } : {};
        
        // Add current tasks if conversation ID is provided
        if (context?.conversation_id) {
          try {
            const { getCurrentTasks } = await import('../agents/task-planning-agent.js');
            const tasksResult = await getCurrentTasks(context.conversation_id);
            if (tasksResult.success) {
              richContext.currentTasks = tasksResult.tasks;
            }
          } catch (error) {
            console.log(`[Spawn MCP Agent] Could not get current tasks:`, error.message);
          }
        }
        
        // Route to appropriate MCP agent
        const result = await routeToMCPAgent(task, {
          conversationId: context?.conversation_id,
          richContext
        });
        
        // Check if the result indicates a graceful failure
        if (result && result.success === false) {
          console.log(`[Spawn MCP Agent] Agent returned graceful error: ${result.message}`);
          return {
            success: false,
            error: result.error,
            errorType: result.errorType,
            message: result.message,
            agent: routing.primaryAgent || 'unknown'
          };
        }
        
        // Extract meaningful response from agent result
        if (result && result.state && result.state._generatedItems) {
          // Look for message outputs
          const messages = result.state._generatedItems.filter(
            item => item.type === 'message_output'
          );
          
          if (messages.length > 0) {
            // Return the last message content
            const lastMessage = messages[messages.length - 1];
            return {
              success: true,
              agent: routing.primaryAgent || 'unknown',
              response: lastMessage.content,
              confidence: routing.confidence
            };
          }
          
          // Look for tool outputs as fallback
          const toolOutputs = result.state._generatedItems.filter(
            item => item.type === 'tool_call_output'
          );
          
          if (toolOutputs.length > 0) {
            return {
              success: true,
              agent: routing.primaryAgent || 'unknown',
              response: toolOutputs[toolOutputs.length - 1].output,
              confidence: routing.confidence
            };
          }
        }
        
        // Fallback: return the full result
        return {
          success: true,
          agent: routing.primaryAgent || 'unknown',
          response: result,
          confidence: routing.confidence
        };
        
      } catch (error) {
        console.error(`[Spawn MCP Agent] Failed to execute task:`, error);
        return {
          success: false,
          error: error.message,
          errorType: 'execution',
          agent: routing.primaryAgent || 'unknown'
        };
      }
    }
  });
}