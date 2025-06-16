import { Agent, run, tool } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { mcpToolDiscovery } from './mcp-tool-discovery.js';
import fs from 'node:fs';
import path from 'node:path';
import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { z } from 'zod';

// Debug logging for startup
console.log('======= TASK-GENERATOR-AGENT.JS INITIALIZATION =======');
console.log('OPENAI_API_KEY available:', !!process.env.OPENAI_API_KEY);
console.log('MCP_BEARER_TOKEN available:', !!process.env.MCP_BEARER_TOKEN);

// Ensure OpenAI key is set (required by agents SDK even if model selection differs)
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// MCP dependency removed – TaskGen now works entirely locally with markdown plans.

// Reuse previously discovered tools to embed all tool names into the prompt
let allToolNames = [];
try {
  if (!mcpToolDiscovery.allTools.length) {
    await mcpToolDiscovery.discoverTools();
  }
  allToolNames = mcpToolDiscovery.allTools.map(t => t.name);
} catch (err) {
  console.error('TaskGen: Failed to get tool names, using fallback:', err.message);
  const fallback = mcpToolDiscovery.getFallbackTools();
  allToolNames = fallback.allTools.map(t => t.name);
}

const toolNameList = allToolNames.join(', ');

const taskGeneratorPrompt = `You are TaskGen, an autonomous task-planning agent.

Return ONLY a JSON array of task titles (strings). No markdown, no additional keys.
Example valid output: ["Task 1", "Task 2"]

Guidelines:
1. Read the user's request.
2. Break it into clear, executable steps for EspressoBot.
3. Mention a suggested Shopify tool in the title if helpful.
4. Do not call any tools – just return the JSON.

AVAILABLE TOOLS for EspressoBot (you can reference these in task titles):
${toolNameList}

Additional built-in tools:
- generate_todos: Generate task list
- get_todos: Get current task list  
- update_task_status: Update task status
- search_dev_docs: Search Shopify documentation
- introspect_admin_schema: Get GraphQL schema details
- fetch_docs_by_path: Get specific documentation

IMPORTANT: Only suggest tools from the above list. Do not invent tool names.`;

export const taskGeneratorAgent = new Agent({
  name: 'TaskGen',
  instructions: taskGeneratorPrompt,
  model: process.env.TASKGEN_MODEL || 'o4-mini',
  // No external tool servers needed
});

export const generateTodosTool = tool({
  name: 'generate_todos',
  description: `Generate or update the todo task list for the current conversation. MUST include conversation_id in each create_task.`,
  parameters: z.object({
    conversation_id: z.string(),
    context: z.string().optional().default('')
  }),
  async execute({ conversation_id, context = '' }) {
    console.log(`[TaskGen] generate_todos called with conversation_id: ${conversation_id}`);
    console.log(`[TaskGen] Context length: ${context.length}`);
    
    const enforcedPrompt = `Return ONLY the array of task titles. Context for planning:\n${context}`;
    
    console.log(`[TaskGen] Running TaskGen agent...`);
    const result = await run(taskGeneratorAgent, enforcedPrompt, {});
    console.log(`[TaskGen] Full result object:`, JSON.stringify(result, null, 2));
    const output = result.finalOutput || result.result || result.output || '[]';
    console.log(`[TaskGen] Extracted output:`, output);
    let tasks;
    try {
      tasks = JSON.parse(output);
      if (!Array.isArray(tasks)) throw new Error('Not array');
    } catch {
      console.warn('generateTodosTool: output not valid JSON array, defaulting to empty');
      tasks = [];
    }

    // Write markdown plan immediately
    try {
      const filePath = path.resolve(plansDir, `TODO-${conversation_id}.md`);
      console.log(`[TaskGen] Attempting to write ${tasks.length} tasks to: ${filePath}`);
      console.log(`[TaskGen] Tasks to write:`, tasks);
      
      const lines = tasks.map(t => `- [ ] ${t}`);
      const content = lines.join('\n');
      
      fs.writeFileSync(filePath, content, 'utf-8');
      console.log(`[TaskGen] Successfully wrote plan markdown to ${filePath}`);
      console.log(`[TaskGen] File content: ${content}`);
      
      // Verify file was written
      if (fs.existsSync(filePath)) {
        const stats = fs.statSync(filePath);
        console.log(`[TaskGen] File verified - size: ${stats.size} bytes`);
      } else {
        console.error(`[TaskGen] ERROR: File was not created at ${filePath}`);
      }
    } catch (error) {
      console.error(`[TaskGen] ERROR writing markdown file:`, error);
      console.error(`[TaskGen] Error stack:`, error.stack);
    }

    return JSON.stringify(tasks);
  }
});

// --- NEW: getTodosTool wrapper -----------------------------------------
export const getTodosTool = tool({
  name: 'get_todos',
  description: 'Fetch the current todo task list for the specified conversation.',
  parameters: z.object({
    conversation_id: z.string()
  }),
  async execute({ conversation_id }) {
    const filePath = path.resolve(plansDir, `TODO-${conversation_id}.md`);
    if (!fs.existsSync(filePath)) return '[]';
    const content = fs.readFileSync(filePath, 'utf-8');
    const tasks = [];
    for (const line of content.split(/\r?\n/)) {
      const match = line.match(/^\s*-\s*\[( |x)\]\s*(.+)$/i);
      if (match) {
        tasks.push({
          title: match[2].trim(),
          status: match[1].toLowerCase() === 'x' ? 'completed' : 'pending'
        });
      }
    }
    return JSON.stringify(tasks);
  }
});

// Initialize plans directory
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const plansDir = path.resolve(__dirname, 'plans');
if (!fs.existsSync(plansDir)) fs.mkdirSync(plansDir, { recursive: true });

// --- NEW: updateTaskStatusTool -----------------------------------------
export const updateTaskStatusTool = tool({
  name: 'update_task_status',
  description: 'Update the status of a task in the todo list. Use this after completing a task.',
  parameters: z.object({
    conversation_id: z.string(),
    task_index: z.number().describe('The index of the task (0-based)'),
    status: z.enum(['completed', 'in_progress', 'pending'])
  }),
  async execute({ conversation_id, task_index, status }) {
    console.log(`[TaskGen] Updating task ${task_index} to ${status} for conversation ${conversation_id}`);
    
    const filePath = path.resolve(plansDir, `TODO-${conversation_id}.md`);
    if (!fs.existsSync(filePath)) {
      console.error(`[TaskGen] No task file found for conversation ${conversation_id}`);
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
          return `- [${checkbox}] ${prefix}${match[2]}`;
        }
        taskCount++;
      }
      return line;
    });
    
    if (updated) {
      fs.writeFileSync(filePath, updatedLines.join('\n'), 'utf-8');
      console.log(`[TaskGen] Updated task ${task_index} to ${status}`);
      return `Task ${task_index} updated to ${status}`;
    } else {
      console.error(`[TaskGen] Task index ${task_index} not found`);
      return `Task index ${task_index} not found`;
    }
  }
});

// --- TaskPlan tools: write and read TODO markdown ---
export const writePlanMdTool = {
  ...taskGeneratorAgent.asTool({ name: 'write_plan_md', description: 'Write TODO markdown file for the specified conversation.' }),
  inputSchema: {
    type: 'object',
    properties: {
      conversation_id: { type: 'string' },
      tasks: { type: 'array', items: { type: 'string' } }
    },
    required: ['conversation_id', 'tasks']
  },
  async call({ conversation_id, tasks }) {
    const filePath = path.resolve(plansDir, `TODO-${conversation_id}.md`);
    const lines = tasks.map(task => `- [ ] ${task}`);
    fs.writeFileSync(filePath, lines.join('\n'), 'utf-8');
    return filePath;
  }
};

export const readPlanMdTool = {
  ...taskGeneratorAgent.asTool({ name: 'read_plan_md', description: 'Read the TODO markdown file for the specified conversation.' }),
  inputSchema: {
    type: 'object',
    properties: {
      conversation_id: { type: 'string' }
    },
    required: ['conversation_id']
  },
  async call({ conversation_id }) {
    const filePath = path.resolve(plansDir, `TODO-${conversation_id}.md`);
    if (!fs.existsSync(filePath)) return '';
    return fs.readFileSync(filePath, 'utf-8');
  }
};

console.log('TaskGen agent initialised');
console.log('TaskGen tools exported');
console.log('generateTodosTool wrapped with enforced conversation_id');
console.log('getTodosTool wrapped with enforced conversation_id');
