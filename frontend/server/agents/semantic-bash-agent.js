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
export async function createSemanticBashAgent(name, task, conversationId = null) {
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
    return createBashAgent(name, task, conversationId);
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
  
  // Load task context if available
  let taskContext = '';
  if (conversationId) {
    try {
      const { readTasksForConversation, formatTasksForPrompt } = await import('../utils/task-reader.js');
      const { tasks } = await readTasksForConversation(conversationId);
      if (tasks && tasks.length > 0) {
        taskContext = '\n\n' + formatTasksForPrompt(tasks);
      }
    } catch (error) {
      console.log(`[SemanticBashAgent] Could not read tasks:`, error.message);
    }
  }
  
  // Create the agent
  return new Agent({
    name,
    instructions: `You are a bash-enabled agent with semantic search capabilities for EspressoBot Shell Agency.

## Your Capabilities:
1. **Bash Execution**: Full access to Python tools in /home/pranav/espressobot/frontend/python-tools/
2. **Semantic Search**: Use search_documentation to find relevant information about:
   - Tool usage and parameters
   - Business rules (preorders, pricing, etc.)
   - Product creation guidelines
   - Workflow examples
   
## How to Use Semantic Search:
When you need information about tools, business rules, or workflows, use the search_documentation tool first:
- Search for tool names: "update_pricing tool usage"
- Search for business rules: "preorder management rules"
- Search for workflows: "create combo product workflow"
- Search for specific features: "metafields product features"

## Best Practices:
1. Search documentation BEFORE attempting complex operations
2. Use semantic search when:
   - You need to understand tool parameters
   - You're unsure about business rules
   - You need workflow examples
   - Error messages reference specific requirements
3. Execute bash commands based on search results
4. Chain searches for complex queries

## Example Workflow:
1. User asks to "add product to preorder"
2. Search: "preorder management business rules"
3. Get rules about tags and inventory policy
4. Search: "manage_tags tool usage"
5. Execute the appropriate commands

Your specific task: ${task}${taskContext}

Remember: You have the power of semantic search - use it to ensure accuracy!`,
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