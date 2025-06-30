import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { 
  generateTodosTool, 
  getTodosTool, 
  updateTaskStatusTool 
} from '../task-generator-agent.js';
import { z } from 'zod';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Planning agent that analyzes requests and creates structured task plans
export const planningAgent = new Agent({
  name: 'Planning_Agent',
  instructions: `You are a planning specialist that analyzes user requests and creates structured task plans.

Your responsibilities:
1. Analyze the user's request to understand what needs to be done
2. Break down complex requests into clear, actionable tasks
3. Use the generate_todos tool to create a task list
4. Organize tasks in logical order of execution
5. Include relevant Shopify tools in task descriptions when applicable

Guidelines:
- Each task should be specific and actionable
- Include the suggested tool name in parentheses if relevant (e.g., "Search for coffee products (search_products)")
- Consider dependencies between tasks
- For simple requests, create 1-3 tasks
- For complex requests, create 4-8 tasks
- Always pass the conversation_id to the generate_todos tool

Examples:
- User: "Update prices for all coffee products by 10%"
  Tasks: ["Search for all coffee products (search_products)", "Calculate new prices with 10% increase", "Update pricing for each product (update_pricing)", "Verify price updates (get_product)"]
  
- User: "Create a bundle with espresso machine and coffee beans"
  Tasks: ["Find espresso machine products (search_products)", "Find coffee bean products (search_products)", "Create bundle configuration", "Create combo listing (create_combo)"]`,
  
  model: process.env.PLANNING_MODEL || 'gpt-4o',
  modelSettings: { 
    temperature: 0.3,
    parallelToolCalls: false
  },
  tools: [generateTodosTool, getTodosTool, updateTaskStatusTool]
});

// Function to analyze a request and create a task plan
export async function createTaskPlan(userRequest, conversationId) {
  try {
    console.log('[Planning Agent] Creating task plan for conversation:', conversationId);
    
    const prompt = `
Analyze this user request and create a structured task plan:

"${userRequest}"

Remember to:
1. Break it down into clear, actionable steps
2. Include relevant tool names in task descriptions
3. Order tasks logically
4. Use the generate_todos tool with conversation_id: "${conversationId}"
`;

    const result = await run(planningAgent, prompt);
    console.log('[Planning Agent] Task plan created');
    
    // Also return the tasks for immediate use
    const todoResult = await getTodosTool.execute({ conversation_id: conversationId });
    const tasks = JSON.parse(todoResult);
    
    return {
      success: true,
      tasks,
      agentResponse: result
    };
  } catch (error) {
    console.error('[Planning Agent] Error creating task plan:', error);
    return {
      success: false,
      error: error.message,
      tasks: []
    };
  }
}

// Function to update task status
export async function updateTaskStatus(conversationId, taskIndex, status) {
  try {
    const result = await updateTaskStatusTool.execute({
      conversation_id: conversationId,
      task_index: taskIndex,
      status
    });
    
    return {
      success: true,
      result
    };
  } catch (error) {
    console.error('[Planning Agent] Error updating task status:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Function to get current tasks
export async function getCurrentTasks(conversationId) {
  try {
    const result = await getTodosTool.execute({ conversation_id: conversationId });
    const tasks = JSON.parse(result);
    
    return {
      success: true,
      tasks
    };
  } catch (error) {
    console.error('[Planning Agent] Error getting tasks:', error);
    return {
      success: false,
      error: error.message,
      tasks: []
    };
  }
}