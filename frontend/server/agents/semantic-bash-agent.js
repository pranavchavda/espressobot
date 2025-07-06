/**
 * Semantic Bash Agent with File Search
 * 
 * This agent has access to both bash tools and semantic search through
 * OpenAI's file search, providing the best of both worlds.
 */

import { Agent } from '@openai/agents';
import { fileSearchTool } from '@openai/agents-openai';
import { bashTool } from '../tools/bash-tool.js';
import { getVectorStoreId } from '../context-loader/vector-store-manager.js';

/**
 * Create a bash agent with semantic search capabilities
 */
export async function createSemanticBashAgent(name, task, conversationId = null, autonomyLevel = 'high', richContext) {
  // richContext is now REQUIRED - orchestrator must provide context
  if (!richContext) {
    throw new Error('[SemanticBashAgent] richContext is required. Orchestrator must provide context.');
  }
  
  console.log(`[SemanticBashAgent] Creating agent for task: ${task}`);
  
  // Get vector store ID for file search
  let vectorStoreId;
  try {
    vectorStoreId = await getVectorStoreId();
    console.log(`[SemanticBashAgent] Using vector store: ${vectorStoreId}`);
  } catch (error) {
    console.error('[SemanticBashAgent] Could not get vector store:', error.message);
    // Fall back to regular bash agent
    const { createBashAgent } = await import('../tools/bash-tool.js');
    return createBashAgent(name, task, conversationId, autonomyLevel, richContext);
  }
  
  // Create tools array
  const tools = [
    // Bash tool for executing commands
    bashTool,
    
    // File search tool for semantic documentation search
    fileSearchTool(vectorStoreId, {
      name: 'search_documentation',
      maxNumResults: 5,
      includeSearchResults: true
    })
  ];
  
  // Add task update tool if conversationId is provided
  if (conversationId) {
    try {
      const { tool } = await import('@openai/agents');
      const { z } = await import('zod');
      
      const updateTaskTool = tool({
        name: 'update_task_status',
        description: 'Update the status of a task in the current task list',
        parameters: z.object({
          taskIndex: z.number().describe('The index of the task to update (0-based)'),
          newStatus: z.enum(['pending', 'in_progress', 'completed']).describe('The new status for the task')
        }),
        execute: async ({ taskIndex, newStatus }) => {
          try {
            const { updateTaskStatus } = await import('../utils/task-reader.js');
            const result = await updateTaskStatus(conversationId, taskIndex, newStatus);
            
            // Emit task update event if SSE emitter is available
            if (global.currentSseEmitter) {
              global.currentSseEmitter('task_update', {
                conversationId,
                taskIndex,
                newStatus,
                timestamp: new Date().toISOString()
              });
            }
            
            return result;
          } catch (error) {
            console.error(`[SemanticBashAgent] Error updating task status:`, error);
            return JSON.stringify({
              success: false,
              error: error.message,
              message: `Failed to update task status: ${error.message}`
            });
          }
        }
      });
      
      tools.push(updateTaskTool);
    } catch (error) {
      console.log(`[SemanticBashAgent] Could not add task tool:`, error.message);
    }
  }
  
  // Build prompt from rich context
  console.log(`[SemanticBashAgent] Using orchestrator-provided rich context`);
  
  // Import the prompt builder from bash-tool
  const { buildPromptFromRichContext } = await import('../tools/bash-tool.js');
  const contextualPrompt = buildPromptFromRichContext(richContext);
  
  // Add autonomy level
  const autonomyContext = autonomyLevel === 'high' 
    ? '\n\n## AUTONOMY MODE: HIGH\nYou have full autonomy. Execute all operations immediately without asking for confirmation. The user trusts you to complete the task.'
    : autonomyLevel === 'medium'
    ? '\n\n## AUTONOMY MODE: MEDIUM\nExecute most operations immediately. Only confirm genuinely risky operations (bulk deletes, operations affecting 50+ items).'
    : '\n\n## AUTONOMY MODE: LOW\nConfirm all write operations before executing. This is a careful mode for sensitive operations.';
  
  const instructions = contextualPrompt + `

## Additional Capability: Semantic Search
You also have access to semantic search through the search_documentation tool:
- Use it when you need information about tools, business rules, or workflows
- Search for tool names: "update_pricing tool usage"
- Search for business rules: "preorder management rules"
- Search for workflows: "create combo product workflow"

IMPORTANT: The orchestrator has already provided relevant context above. Only use search_documentation if you need additional information not included in the context.` + autonomyContext + `\n\nYour specific task: ${task}`;
  
  // Create the agent
  return new Agent({
    name,
    instructions,
    tools,
    model: 'gpt-4.1-mini'
  });
}

/**
 * Spawn a semantic bash agent
 */
export async function spawnSemanticBashAgent(config) {
  const { agentName, task, conversationId, sseEmitter } = config;
  
  console.log(`\n[SPAWNING SEMANTIC BASH AGENT: ${agentName}]`);
  console.log(`Task: ${task}`);
  
  // Set SSE emitter for real-time updates
  if (sseEmitter) {
    global.currentSseEmitter = sseEmitter;
  }
  
  try {
    // Create the semantic bash agent
    const agent = await createSemanticBashAgent(agentName, task, conversationId);
    
    // Import run function
    const { run } = await import('@openai/agents');
    
    // Run the agent
    const result = await run(agent, task, { maxTurns: 30 });
    
    console.log(`[${agentName}] Completed`);
    return {
      success: true,
      agent: agentName,
      result: result
    };
  } catch (error) {
    console.error(`[${agentName}] Error:`, error);
    return {
      success: false,
      agent: agentName,
      error: error.message
    };
  }
}