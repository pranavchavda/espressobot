import { Agent, run, tool } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { z } from 'zod';
import fs from 'node:fs';
import fsSync from 'node:fs';
import path from 'node:path';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { customToolDiscovery } from '../custom-tool-discovery.js';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Initialize plans directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const plansDir = path.resolve(__dirname, '../plans');
if (!fs.existsSync(plansDir)) fs.mkdirSync(plansDir, { recursive: true });

// Get all available tool names for context
let allToolNames = [];
try {
  if (!customToolDiscovery.allTools.length) {
    await customToolDiscovery.discoverTools();
  }
  allToolNames = customToolDiscovery.allTools.map(t => t.name);
} catch (err) {
  console.error('[Task Planning] Failed to get tool names:', err.message);
  allToolNames = [];
}

// Core task management tools
export const generateTodosTool = tool({
  name: 'generate_todos',
  description: 'Generate or update the todo task list for the current conversation',
  parameters: z.object({
    conversation_id: z.string(),
    tasks: z.array(z.string()).describe('Array of task descriptions')
  }),
  execute: async ({ conversation_id, tasks }) => {
    console.log(`[Task Planning] Generating ${tasks.length} tasks for conversation ${conversation_id}`);
    
    try {
      const filePath = path.resolve(plansDir, `TODO-${conversation_id}.md`);
      const lines = tasks.map(t => `- [ ] ${t}`);
      const content = lines.join('\n');
      
      fs.writeFileSync(filePath, content, 'utf-8');
      console.log(`[Task Planning] Successfully wrote tasks to ${filePath}`);
      
      return JSON.stringify(tasks);
    } catch (error) {
      console.error(`[Task Planning] Error writing tasks:`, error);
      throw error;
    }
  }
});

export const getTodosTool = tool({
  name: 'get_todos',
  description: 'Fetch the current todo task list for the specified conversation',
  parameters: z.object({
    conversation_id: z.string()
  }),
  execute: async ({ conversation_id }) => {
    const filePath = path.resolve(plansDir, `TODO-${conversation_id}.md`);
    if (!fs.existsSync(filePath)) return '[]';
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const tasks = [];
    
    for (const line of content.split(/\r?\n/)) {
      const match = line.match(/^\s*-\s*\[( |x)\]\s*(.+)$/i);
      if (match) {
        const isCompleted = match[1].toLowerCase() === 'x';
        const description = match[2].trim();
        const inProgress = description.startsWith('🔄 ');
        const cleanDescription = inProgress ? description.substring(3).trim() : description;
        
        tasks.push({
          description: cleanDescription,
          status: isCompleted ? 'completed' : (inProgress ? 'in_progress' : 'pending')
        });
      }
    }
    
    return JSON.stringify(tasks);
  }
});

export const updateTaskStatusTool = tool({
  name: 'update_task_status',
  description: 'Update the status of a task in the todo list',
  parameters: z.object({
    conversation_id: z.string(),
    task_index: z.number().describe('The index of the task (0-based)'),
    status: z.enum(['completed', 'in_progress', 'pending'])
  }),
  execute: async ({ conversation_id, task_index, status }) => {
    console.log(`[Task Planning] Updating task ${task_index} to ${status}`);
    
    const filePath = path.resolve(plansDir, `TODO-${conversation_id}.md`);
    if (!fs.existsSync(filePath)) {
      return 'No task list found';
    }
    
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split(/\r?\n/);
    let taskCount = 0;
    let updated = false;
    
    const updatedLines = lines.map(line => {
      const match = line.match(/^\s*-\s*\[( |x)\]\s*(.+)$/i);
      if (match) {
        if (taskCount === task_index) {
          updated = true;
          const checkbox = status === 'completed' ? 'x' : ' ';
          const prefix = status === 'in_progress' ? '🔄 ' : '';
          const cleanText = match[2].replace(/^🔄 /, '').trim();
          return `- [${checkbox}] ${prefix}${cleanText}`;
        }
        taskCount++;
      }
      return line;
    });
    
    if (updated) {
      fs.writeFileSync(filePath, updatedLines.join('\n'), 'utf-8');
      return `Task ${task_index} updated to ${status}`;
    } else {
      return `Task index ${task_index} not found`;
    }
  }
});

// Task Planning Agent - combines the best of Planning Agent and TaskGen
export const taskPlanningAgent = new Agent({
  name: 'Task_Planning_Agent',
  instructions: `You are a task planning specialist that analyzes user requests and creates structured task plans.

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
- Always pass the conversation_id to the tools

AVAILABLE TOOLS for reference in task descriptions:
${allToolNames.join(', ')}

Additional tools available to bash agents:
- search_dev_docs, introspect_admin_schema, fetch_docs_by_path (documentation)
- All Python tools in /home/pranav/idc/tools/

Examples:
- User: "Update prices for all coffee products by 10%"
  Tasks: ["Search for all coffee products (search_products)", "Calculate new prices with 10% increase", "Update pricing for each product (update_pricing)", "Verify price updates (get_product)"]
  
- User: "Create a bundle with espresso machine and coffee beans"
  Tasks: ["Find espresso machine products (search_products)", "Find coffee bean products (search_products)", "Create bundle configuration", "Create combo listing (create_combo)"]

IMPORTANT: When generating tasks, call the generate_todos tool with the array of task descriptions.`,
  
  model: process.env.PLANNING_MODEL || 'o3',
  modelSettings: { 
    parallelToolCalls: false
    
  },
  tools: [generateTodosTool, getTodosTool, updateTaskStatusTool]
});

// Main function to create a task plan
export async function createTaskPlan(userRequest, conversationId) {
  try {
    console.log('[Task Planning] Creating task plan for conversation:', conversationId);
    
    const prompt = `
Analyze this user request and create a structured task plan:

"${userRequest}"

Remember to:
1. Break it down into clear, actionable steps
2. Include relevant tool names in task descriptions
3. Order tasks logically
4. Use the generate_todos tool with conversation_id: "${conversationId}"
`;

    const result = await run(taskPlanningAgent, prompt, { maxTurns: 30 });
    console.log('[Task Planning] Task plan created');
    
    // Also return the tasks for immediate use
    try {
      const todoResult = await getTodosTool.execute({ conversation_id: conversationId });
      const tasks = JSON.parse(todoResult);
      
      return {
        success: true,
        tasks,
        agentResponse: result
      };
    } catch (toolError) {
      console.log('[Task Planning] Could not retrieve tasks immediately:', toolError.message);
      return {
        success: true,
        tasks: [],
        agentResponse: result
      };
    }
  } catch (error) {
    console.error('[Task Planning] Error creating task plan:', error);
    return {
      success: false,
      error: error.message,
      tasks: []
    };
  }
}

// Utility functions for direct task management
export async function updateTaskStatus(conversationId, taskIndex, status) {
  try {
    const result = await updateTaskStatusTool.invoke(null, JSON.stringify({
      conversation_id: conversationId,
      task_index: taskIndex,
      status
    }));
    
    return {
      success: true,
      result
    };
  } catch (error) {
    console.error('[Task Planning] Error updating task status:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

export async function getCurrentTasks(conversationId) {
  try {
    // Check if getTodosTool is properly initialized
    if (!getTodosTool || typeof getTodosTool.execute !== 'function') {
      console.error('[Task Planning] getTodosTool not properly initialized');
      // Fallback to direct file reading
      const filePath = path.resolve(plansDir, `TODO-${conversationId}.md`);
      if (!fsSync.existsSync(filePath)) {
        return { success: true, tasks: [] };
      }
      
      const content = fsSync.readFileSync(filePath, 'utf-8');
      const tasks = [];
      
      for (const line of content.split(/\r?\n/)) {
        const match = line.match(/^\s*-\s*\[( |x)\]\s*(.+)$/i);
        if (match) {
          const isCompleted = match[1].toLowerCase() === 'x';
          const description = match[2].trim();
          const inProgress = description.startsWith('🔄 ');
          const cleanDescription = inProgress ? description.substring(3).trim() : description;
          
          tasks.push({
            title: cleanDescription,
            description: cleanDescription,
            status: isCompleted ? 'completed' : (inProgress ? 'in_progress' : 'pending')
          });
        }
      }
      
      return { success: true, tasks };
    }
    
    // Call the tool's execute function directly
    const result = await getTodosTool.execute({ conversation_id: conversationId });
    const tasks = JSON.parse(result);
    
    return {
      success: true,
      tasks
    };
  } catch (error) {
    console.error('[Task Planning] Error getting tasks:', error);
    return {
      success: false,
      error: error.message,
      tasks: []
    };
  }
}

console.log('[Task Planning] Agent initialized with merged functionality');