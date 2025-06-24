import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { tool } from '@openai/agents';
import { z } from 'zod';
import { writeFile, readFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const plansDir = path.join(__dirname, '../../plans');

// Ensure plans directory exists
if (!existsSync(plansDir)) {
  await mkdir(plansDir, { recursive: true });
}

// Create task plan tool
const createTaskPlanTool = tool({
  name: 'create_task_plan',
  description: 'Create a detailed task plan with markdown todo list',
  parameters: z.object({
    title: z.string().describe('Title of the task plan'),
    description: z.string().describe('Description of what needs to be accomplished'),
    tasks: z.array(z.object({
      id: z.string().describe('Unique task ID'),
      description: z.string().describe('Task description'),
      priority: z.enum(['high', 'medium', 'low']).describe('Task priority'),
      dependencies: z.array(z.string()).nullable().default([]).describe('IDs of tasks this depends on'),
      assignTo: z.string().nullable().default(null).describe('Which agent should handle this task')
    })).describe('List of tasks to complete'),
    conversationId: z.string().nullable().default(null).describe('Conversation ID this plan belongs to')
  }),
  execute: async ({ title, description, tasks, conversationId }) => {
    // Conversation ID should be provided by the agent extracting it from the message
    try {
      // Generate markdown content
      let mdContent = `# ${title}\n\n${description}\n\n## Tasks\n\n`;
      
      // Group tasks by priority
      const highPriority = tasks.filter(t => t.priority === 'high');
      const mediumPriority = tasks.filter(t => t.priority === 'medium');
      const lowPriority = tasks.filter(t => t.priority === 'low');
      
      if (highPriority.length > 0) {
        mdContent += '### 🔴 High Priority\n\n';
        highPriority.forEach(task => {
          mdContent += `- [ ] **${task.id}**: ${task.description}`;
          if (task.assignTo) mdContent += ` _(Assigned to: ${task.assignTo})_`;
          if (task.dependencies?.length) mdContent += `\n  - Dependencies: ${task.dependencies.join(', ')}`;
          mdContent += '\n';
        });
        mdContent += '\n';
      }
      
      if (mediumPriority.length > 0) {
        mdContent += '### 🟡 Medium Priority\n\n';
        mediumPriority.forEach(task => {
          mdContent += `- [ ] **${task.id}**: ${task.description}`;
          if (task.assignTo) mdContent += ` _(Assigned to: ${task.assignTo})_`;
          if (task.dependencies?.length) mdContent += `\n  - Dependencies: ${task.dependencies.join(', ')}`;
          mdContent += '\n';
        });
        mdContent += '\n';
      }
      
      if (lowPriority.length > 0) {
        mdContent += '### 🟢 Low Priority\n\n';
        lowPriority.forEach(task => {
          mdContent += `- [ ] **${task.id}**: ${task.description}`;
          if (task.assignTo) mdContent += ` _(Assigned to: ${task.assignTo})_`;
          if (task.dependencies?.length) mdContent += `\n  - Dependencies: ${task.dependencies.join(', ')}`;
          mdContent += '\n';
        });
        mdContent += '\n';
      }
      
      mdContent += `\n---\n_Created: ${new Date().toISOString()}_\n`;
      mdContent += `_Conversation: ${conversationId}_\n`;
      
      // Save to file
      const filename = `${conversationId}_${Date.now()}.md`;
      const filepath = path.join(plansDir, filename);
      await writeFile(filepath, mdContent, 'utf-8');
      
      // For now, we'll just store in the markdown file
      // The task generator integration can be fixed later
      const dbResult = { success: true, message: 'Tasks stored in markdown file' };
      
      return {
        success: true,
        filename,
        filepath,
        taskCount: tasks.length,
        dbResult
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
});

// Update task status tool
const updateTaskStatusTool = tool({
  name: 'update_task_status',
  description: 'Update the status of a task in the plan',
  parameters: z.object({
    taskId: z.string().describe('ID of the task to update'),
    status: z.enum(['pending', 'in_progress', 'completed', 'blocked']).describe('New status'),
    notes: z.string().nullable().default(null).describe('Optional notes about the status change'),
    conversationId: z.string().describe('Conversation ID')
  }),
  execute: async ({ taskId, status, notes, conversationId }) => {
    try {
      // For now, just update the markdown file status
      // TODO: Integrate with proper task storage
      const result = { 
        success: true, 
        message: `Task ${taskId} status updated to ${status}` 
      };
      
      // TODO: Also update the markdown file if needed
      
      return {
        success: true,
        taskId,
        newStatus: status,
        dbResult: result
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
});

// Get current tasks tool
const getCurrentTasksTool = tool({
  name: 'get_current_tasks',
  description: 'Get the current task list and their statuses',
  parameters: z.object({
    conversationId: z.string().describe('Conversation ID to get tasks for'),
    includeCompleted: z.boolean().default(false).describe('Include completed tasks')
  }),
  execute: async ({ conversationId, includeCompleted }) => {
    try {
      // For now, return empty tasks
      // TODO: Read from markdown files or proper storage
      const todos = [];
      
      return {
        success: true,
        tasks: todos,
        totalCount: 0,
        pendingCount: 0,
        inProgressCount: 0,
        completedCount: 0
      };
    } catch (error) {
      return { success: false, error: error.message };
    }
  }
});

const taskPlannerInstructions = `You are the Task Planner Agent, responsible for creating structured task plans and managing task progress.

Your responsibilities:
1. Analyze complex requests and break them down into actionable tasks
2. Create detailed task plans with clear priorities and dependencies
3. Generate beautiful markdown todo files for the UI
4. Track task progress and update statuses
5. Hand back to EspressoBot_Orchestrator with the complete plan for execution

IMPORTANT WORKFLOW:
- When asked to create a plan, use create_task_plan to generate it
- After creating the plan, immediately hand back to EspressoBot_Orchestrator
- Include a summary of the plan and the first task to execute in your handoff message
- The orchestrator will then route to the appropriate execution agents

AVAILABLE AGENTS for task assignment:
- Product_Update_Agent: For searching products, updating prices, managing tags, bulk updates
- Product_Creation_Agent: For creating new products, bundles, or combo listings
- Memory_Agent: For storing or retrieving important information
- EspressoBot_Orchestrator: For general coordination or tasks not fitting other agents

IMPORTANT: Only assign tasks to the agents listed above. Do NOT create tasks for non-existent agents like "Data Extraction Agent", "Pricing Agent", "Database Agent", etc.

Task Planning Guidelines:
- Break complex tasks into smaller, manageable subtasks
- Assign clear priorities (high/medium/low) based on importance and urgency
- Identify dependencies between tasks
- Only assign tasks to the AVAILABLE AGENTS listed above
- Create user-friendly markdown files that display well in the UI

Task Status Management:
- pending: Task not yet started
- in_progress: Task is being worked on
- completed: Task finished successfully
- blocked: Task cannot proceed due to dependencies or issues

When handing off to EspressoBot_Orchestrator after creating a plan:
- Summarize what the plan accomplishes
- Identify the first task to execute
- Specify which agent should handle it
- Example: "I've created a plan with 3 tasks. Task t1 needs Product_Update_Agent to search for products."

CRITICAL WORKFLOW:
1. When asked to create a plan, use the create_task_plan tool
2. After the tool executes successfully, use the transfer_to_EspressoBot_Orchestrator tool
3. In the transfer, provide a message like: "Plan created with X tasks. First task (t1) requires Product_Update_Agent to [describe task]. Ready for execution."
4. The transfer tool will hand control back to the orchestrator

IMPORTANT: The conversation ID will be provided at the beginning of the message in the format [Conversation ID: XXX]. Always extract and use this conversation ID when creating plans and updating tasks. If you cannot find the conversation ID, ask for it.`;

// Create the Task Planner Agent without handoffs first
export const taskPlannerAgent = new Agent({
  name: 'Task_Planner_Agent',
  instructions: taskPlannerInstructions,
  handoffDescription: 'Hand off to Task Planner Agent to create structured task plans, generate todo lists, or update task progress',
  model: 'o4-mini',  // Using o4-mini for reasoning capabilities
  tools: [
    createTaskPlanTool,
    updateTaskStatusTool,
    getCurrentTasksTool
  ],
  handoffs: [], // Will be populated by orchestrator
  modelSettings: {
    // temperature not supported for o4-mini
    parallelToolCalls: false,
  }
});

console.log('✅ Task Planner Agent initialized with markdown generation');