import { Agent, tool } from '@openai/agents';
import { z } from 'zod';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs/promises';

/**
 * Core bash execution function
 */
export const executeBashCommand = async ({ command, cwd = '/tmp', timeout = 300000 }, sseEmitter = null) => {
  return new Promise((resolve) => {
    console.log(`[BASH] Executing: ${command}`);
    console.log(`[BASH] Working directory: ${cwd}`);
    
    // Send real-time progress if SSE emitter is available
    if (sseEmitter && typeof sseEmitter === 'function') {
      sseEmitter('agent_processing', {
        agent: 'Bash_Executor',
        message: `Executing: ${command}`,
        status: 'executing'
      });
    }
    
    // Safety checks
    const dangerousPatterns = [
      /rm\s+-rf\s+\//,  // rm -rf /
      /:\(\)\{.*\|:&\};:/,  // Fork bomb
      /mkfs/,  // Formatting commands
      /dd\s+if=.*of=\/dev/,  // Direct disk writes
    ];
    
    for (const pattern of dangerousPatterns) {
      if (pattern.test(command)) {
        resolve({
          success: false,
          error: 'Command blocked for safety reasons',
          stdout: '',
          stderr: 'This command pattern is not allowed'
        });
        return;
      }
    }
    
    // Execute command
    const proc = spawn('bash', ['-c', command], {
      cwd,
      env: {
        ...process.env,
        // Ensure Python tools have access to Shopify credentials
        SHOPIFY_SHOP_URL: process.env.SHOPIFY_SHOP_URL,
        SHOPIFY_ACCESS_TOKEN: process.env.SHOPIFY_ACCESS_TOKEN,
        OPENAI_API_KEY: process.env.OPENAI_API_KEY,
        PERPLEXITY_API_KEY: process.env.PERPLEXITY_API_KEY,
        // Pass user and conversation IDs for memory operations
        ESPRESSOBOT_USER_ID: global.currentUserId || process.env.ESPRESSOBOT_USER_ID || '2',
        ESPRESSOBOT_CONVERSATION_ID: global.currentConversationId || process.env.ESPRESSOBOT_CONVERSATION_ID || '',
      },
      // Capture output
      shell: false
    });
    
    let stdout = '';
    let stderr = '';
    
    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    proc.on('close', (code) => {
      const result = {
        success: code === 0,
        exitCode: code,
        stdout: stdout.trim(),
        stderr: stderr.trim()
      };
      
      console.log(`[BASH] Exit code: ${code}`);
      if (stdout) console.log(`[BASH] stdout: ${stdout.substring(0, 200)}${stdout.length > 200 ? '...' : ''}`);
      
      // Send completion status
      if (sseEmitter && typeof sseEmitter === 'function') {
        if (code === 0) {
          sseEmitter('agent_processing', {
            agent: 'Bash_Executor',
            message: `Command completed successfully`,
            status: 'completed'
          });
        } else {
          sseEmitter('agent_processing', {
            agent: 'Bash_Executor',
            message: `Command failed with exit code ${code}`,
            status: 'error'
          });
        }
      }
      if (stderr) console.log(`[BASH] stderr: ${stderr.substring(0, 200)}${stderr.length > 200 ? '...' : ''}`);
      
      // Format result for agent
      if (code === 0) {
        resolve(stdout || 'Command executed successfully (no output)');
      } else {
        resolve(`Command failed with exit code ${code}\n${stderr || stdout || 'No error output'}`);
      }
    });
    
    proc.on('error', (err) => {
      console.error(`[BASH] Process error:`, err);
      resolve(`Failed to execute command: ${err.message}`);
    });
    
    // Timeout after specified duration (default 5 minutes)
    const timeoutMs = timeout || 300000;
    const timeoutHandle = setTimeout(() => {
      proc.kill();
      if (sseEmitter) {
        sseEmitter('agent_processing', {
          agent: 'Bash_Executor',
          message: `Command timed out after ${timeoutMs/1000} seconds`,
          status: 'error'
        });
      }
      resolve(`Command timed out after ${timeoutMs/1000} seconds`);
    }, timeoutMs);
    
    // Clear timeout if process completes before timeout
    proc.on('exit', () => {
      clearTimeout(timeoutHandle);
    });
  });
};

/**
 * Bash tool for agents - provides controlled command line access
 */
export const bashTool = tool({
  name: 'bash',
  description: `Execute bash commands. You have access to:
    - Python tools in /home/pranav/espressobot/frontend/python-tools/
    - Standard Unix utilities (grep, awk, sed, jq, etc.)
    - Python 3 with all Shopify/e-commerce libraries installed
    - Can read/write temporary files in /tmp/
    
    Examples:
    - python3 /home/pranav/espressobot/frontend/python-tools/search_products.py "coffee" --status active
    - python3 /home/pranav/espressobot/frontend/python-tools/get_product.py SKU123 | jq '.price'
    - echo "SKU123,49.99" > /tmp/price_updates.csv && python3 /home/pranav/espressobot/frontend/python-tools/bulk_price_update.py /tmp/price_updates.csv
    
    Safety notes:
    - Always use absolute paths for tools
    - Be careful with quotes and escaping
    - Check command output for errors`,
  parameters: z.object({
    command: z.string().describe('The bash command to execute'),
    cwd: z.string().nullable().default('/tmp').describe('Working directory (defaults to /tmp)'),
    timeout: z.number().optional().default(300000).describe('Command timeout in milliseconds (defaults to 5 minutes)')
  }),
  execute: async (params) => {
    // Try to get SSE emitter from global context (if available)
    let sseEmitter = null;
    if (global.currentSseEmitter && typeof global.currentSseEmitter === 'function') {
      sseEmitter = global.currentSseEmitter;
    }
    return executeBashCommand(params, sseEmitter);
  }
});

/**
 * Create a bash-enabled agent
 */
export async function createBashAgent(name, task, conversationId = null) {
  // Load the enhanced bash agent prompt template
  let bashAgentPrompt;
  try {
    const promptPath = path.join(path.dirname(new URL(import.meta.url).pathname), '../prompts/bash-agent-enhanced.md');
    bashAgentPrompt = await fs.readFile(promptPath, 'utf-8');
  } catch (error) {
    // Try fallback to basic prompt
    try {
      const fallbackPath = path.join(path.dirname(new URL(import.meta.url).pathname), '../prompts/bash-agent.md');
      bashAgentPrompt = await fs.readFile(fallbackPath, 'utf-8');
    } catch (fallbackError) {
      // Final fallback to inline prompt
      bashAgentPrompt = `You are a bash-enabled agent with full access to Python tools in /home/pranav/espressobot/frontend/python-tools/.
    
Best practices: Check tool existence, use --help, handle errors, use absolute paths, chain commands with &&.`;
    }
  }
  
  // Load smart context based on the task
  let smartContext = '';
  try {
    const { getSmartContext } = await import('../context-loader/context-manager.js');
    smartContext = await getSmartContext(task, {
      taskDescription: task,
      includeMemory: true
    });
    console.log(`[Bash Agent] Loaded smart context (${smartContext.length} chars) for task: ${task.substring(0, 50)}...`);
  } catch (error) {
    console.log(`[Bash Agent] Could not load smart context:`, error.message);
  }
  
  // If conversationId is provided, read tasks and inject them
  let taskContext = '';
  if (conversationId) {
    try {
      const { readTasksForConversation, formatTasksForPrompt } = await import('../utils/task-reader.js');
      const { tasks } = await readTasksForConversation(conversationId);
      if (tasks && tasks.length > 0) {
        taskContext = '\n\n' + formatTasksForPrompt(tasks);
      }
    } catch (error) {
      console.log(`[Bash Agent] Could not read tasks for conversation ${conversationId}:`, error.message);
    }
  }
  
  // Create tools array with bash tool
  const tools = [bashTool];
  
  // Add task update tool if conversationId is provided
  if (conversationId && taskContext) {
    const updateTaskTool = tool({
      name: 'update_task_status',
      description: 'Update the status of a task in the current conversation. Use this to mark tasks as in_progress or completed.',
      parameters: z.object({
        taskIndex: z.number().describe('The index of the task (0-based) from the task list'),
        status: z.enum(['pending', 'in_progress', 'completed']).describe('New status for the task')
      }),
      execute: async ({ taskIndex, status }) => {
        try {
          const { updateTaskStatusTool } = await import('../task-generator-agent.js');
          const result = await updateTaskStatusTool.invoke(null, JSON.stringify({
            conversation_id: conversationId,
            task_index: taskIndex,
            status
          }));
          console.log(`[Bash Agent] Updated task ${taskIndex} to ${status}`);
          
          // Send SSE event to update the frontend
          const sseEmitter = global.currentSseEmitter;
          if (sseEmitter) {
            // Get updated task list and send to frontend
            const { getTodosTool } = await import('../task-generator-agent.js');
            const tasksResult = await getTodosTool.invoke(null, JSON.stringify({ conversation_id: conversationId }));
            
            let tasks = [];
            try {
              tasks = JSON.parse(tasksResult);
            } catch (parseError) {
              console.error('[Bash Tool] Error parsing tasks result:', tasksResult);
              // If parsing fails, try to read tasks directly
              const { readTasksForConversation } = await import('../utils/task-reader.js');
              const taskData = await readTasksForConversation(conversationId);
              if (taskData.success) {
                tasks = taskData.tasks.map(t => ({
                  title: t.description,
                  status: t.status
                }));
              }
            }
            
            // Send task_summary event with updated tasks
            sseEmitter('task_summary', {
              tasks: tasks.map((task, index) => ({
                id: `task_${conversationId}_${index}`,
                content: task.title || task,
                status: task.status || 'pending',
                conversation_id: conversationId
              })),
              conversation_id: conversationId
            });
            
            // Also send the markdown update
            try {
              const planPath = path.join(path.dirname(new URL(import.meta.url).pathname), '../plans', `TODO-${conversationId}.md`);
              const planContent = await fs.readFile(planPath, 'utf-8');
              sseEmitter('task_plan_created', {
                markdown: planContent,
                filename: `TODO-${conversationId}.md`,
                taskCount: tasks.length,
                conversation_id: conversationId
              });
            } catch (err) {
              // Ignore if file doesn't exist
            }
          }
          
          return result;
        } catch (error) {
          console.error(`[Bash Agent] Error updating task status:`, error);
          // Return a JSON-compatible error response
          return JSON.stringify({
            success: false,
            error: error.message,
            message: `Failed to update task status: ${error.message}`
          });
        }
      }
    });
    tools.push(updateTaskTool);
  }
  
  return new Agent({
    name,
    instructions: `${bashAgentPrompt}
    
Your specific task: ${task}${taskContext}

${smartContext ? '\n## Additional Context\n' + smartContext : ''}`,
    tools,
    model: 'gpt-4.1-mini'
  });
}