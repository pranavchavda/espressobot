import { Agent, tool } from '@openai/agents';
import { z } from 'zod';
import { spawn } from 'child_process';
import path from 'path';
import { learningTool } from './learning-tool.js';

/**
 * Build prompt from rich context object
 */
export function buildPromptFromRichContext(context) {
  let prompt = `You are a general-purpose bash agent - an instrument for the orchestrator to execute system tasks.

## YOUR PRIME DIRECTIVE: ACT IMMEDIATELY WHEN INSTRUCTIONS ARE CLEAR

When you receive a task with specific values, EXECUTE IMMEDIATELY without asking for confirmation.

## CRITICAL UNDERSTANDING:
**The orchestrator handles all Shopify operations directly via MCP tools. Your role is different:**

1. **File system operations** (git, file manipulation, directory operations)
2. **System administration tasks** (process management, environment setup)
3. **Complex multi-step workflows** requiring bash logic
4. **Legacy tools** not yet migrated to MCP
5. **Data processing tasks** that require custom scripting

## WHAT YOU SHOULD DO:
- Execute git commands, file operations, system tasks
- Run custom scripts for data processing
- Handle complex bash workflows with pipes, loops, conditionals
- Use non-MCP tools when specifically instructed

## WHAT YOU SHOULD NOT DO:
- ❌ Use Shopify MCP tools (orchestrator handles these directly)
- ❌ Create ad-hoc curl commands for Shopify APIs
- ❌ Try to replicate MCP tool functionality

Examples of CORRECT usage:
- git status && git add . && git commit -m "Update configuration"
- find . -name "*.py" -exec grep -l "old_pattern" {} \;
- python3 /path/to/custom-processing-script.py /tmp/data.csv
- chmod +x scripts/*.sh && ./scripts/deploy.sh

Examples of WRONG usage (DO NOT DO THIS):
- python3 /python-tools/manage_inventory.py (MCP tools should be used by orchestrator!)
- curl -X POST shopify-api-endpoint (Use MCP tools instead)
- Reimplementing MCP tool functionality`;


  // Add business logic warnings
  if (context.businessLogic && context.businessLogic.patterns.length > 0) {
    prompt += '\n\n## Business Logic Patterns Detected:\n';
    for (const pattern of context.businessLogic.patterns) {
      prompt += `\n### ${pattern.type}:\n`;
      prompt += `- Action: ${pattern.action}\n`;
      if (pattern.warning) prompt += `- WARNING: ${pattern.warning}\n`;
      if (pattern.reminder) prompt += `- Remember: ${pattern.reminder}\n`;
    }
  }

  // Add relevant memories
  if (context.relevantMemories && context.relevantMemories.length > 0) {
    prompt += '\n\n## Relevant Past Experiences:\n';
    for (const memory of context.relevantMemories) {
      prompt += `- ${memory.content}\n`;
    }
  }

  // Add conversation history
  if (context.conversationHistory) {
    prompt += '\n\n## Recent Conversation:\n' + context.conversationHistory;
  }

  // Add current tasks
  if (context.currentTasks && context.currentTasks.length > 0) {
    prompt += '\n\n## Current Tasks:\n';
    context.currentTasks.forEach((task, idx) => {
      const status = task.status === 'completed' ? '[x]' : 
                    task.status === 'in_progress' ? '[🔄]' : '[ ]';
      prompt += `${idx}. ${status} ${task.title || task.description}\n`;
    });
  }

  // Add relevant rules
  if (context.relevantRules && context.relevantRules.length > 0) {
    prompt += '\n\n## Relevant Business Rules:\n';
    prompt += context.relevantRules.join('\n');
  }

  // Add relevant tools
  if (context.relevantTools && context.relevantTools.length > 0) {
    prompt += '\n\n## Relevant Tools:\n';
    prompt += context.relevantTools.join('\n');
  }

  // Add conversation topic if present
  if (context.conversationTopic) {
    prompt += '\n\n' + context.conversationTopic;
  }

  // Add relevant prompt fragments if any
  if (context.promptFragments && context.promptFragments.length > 0) {
    prompt += '\n\n## Relevant Documentation:';
    context.promptFragments.forEach(fragment => {
      prompt += `\n\n### ${fragment.category || 'General'}:\n${fragment.content}`;
    });
  }

  return prompt;
}

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
    
    CRITICAL: For Shopify operations, ALWAYS use the python-tools, NEVER use curl!
    
    Examples:
    - git status && git log --oneline -10
    - find /tmp -name "*.csv" -mtime -1 | xargs ls -la
    - grep -r "error" /var/log/espressobot/ --include="*.log"
    - tar -czf backup.tar.gz ./data/ && mv backup.tar.gz /backups/
    
    Safety notes:
    - Always use absolute paths for tools
    - Be careful with quotes and escaping
    - Check command output for errors
    - NEVER use curl for Shopify API calls - use the python-tools instead`,
  parameters: z.object({
    command: z.string().describe('The bash command to execute'),
    cwd: z.string().nullable().default('/tmp').describe('Working directory (defaults to /tmp)'),
    timeout: z.number().optional().default(300000).describe('Command timeout in milliseconds (defaults to 5 minutes)')
  }),
  execute: async (params) => {
    try {
      // Debug logging
      console.log('[BASH TOOL] Execute called with params:', JSON.stringify(params, null, 2));
      
      // Validate params
      if (!params || typeof params !== 'object') {
        console.error('[BASH TOOL] Invalid params type:', typeof params);
        throw new Error('Invalid params: expected object, got ' + typeof params);
      }
      
      if (!params.command || typeof params.command !== 'string') {
        console.error('[BASH TOOL] Invalid command:', params.command);
        throw new Error('Invalid command: expected string, got ' + typeof params.command);
      }
      
      // Try to get SSE emitter from global context (if available)
      let sseEmitter = null;
      if (global.currentSseEmitter && typeof global.currentSseEmitter === 'function') {
        sseEmitter = global.currentSseEmitter;
      }
      
      return await executeBashCommand(params, sseEmitter);
    } catch (error) {
      console.error('[BASH TOOL] Error in execute:', error);
      console.error('[BASH TOOL] Error stack:', error.stack);
      
      // Return formatted error instead of throwing
      return `Error executing command: ${error.message}\n\nThis might be a system issue. Try using simpler commands or check the logs for more details.`;
    }
  }
});

/**
 * Create a bash-enabled agent
 */
export async function createBashAgent(name, task, conversationId = null, autonomyLevel = 'high', richContext) {
  // richContext is now REQUIRED - orchestrator must provide context
  if (!richContext) {
    throw new Error('[Bash Agent] richContext is required. Orchestrator must provide context.');
  }
  
  console.log(`[Bash Agent] Using orchestrator-provided rich context`);
  
  // Build prompt from rich context
  const contextualPrompt = buildPromptFromRichContext(richContext);
  
  // Create tools array with bash tool and learning tool
  const tools = [bashTool, learningTool];
  
  // Add conversation topic update tool
  const updateTopicTool = tool({
    name: 'update_conversation_topic',
    description: 'Update the topic title and details for the current conversation. Use this to set a clear, concise topic that summarizes what the conversation is about.',
    parameters: z.object({
      topic_title: z.string().describe('A concise topic title (max 200 characters) that summarizes the conversation'),
      topic_details: z.string().nullable().optional().describe('Optional detailed description of the topic, including key context, goals, or important information')
    }),
    execute: async ({ topic_title, topic_details }) => {
      try {
        const { updateConversationTopic } = await import('./update-conversation-topic.js');
        
        // Use the current conversation ID
        const convId = conversationId || global.currentConversationId;
        if (!convId) {
          return {
            success: false,
            error: 'No conversation ID available'
          };
        }
        
        const result = await updateConversationTopic({
          conversation_id: convId,
          topic_title,
          topic_details
        });
        
        console.log(`[Bash Agent] Updated conversation topic: ${topic_title}`);
        return result;
      } catch (error) {
        console.error(`[Bash Agent] Error updating conversation topic:`, error);
        return {
          success: false,
          error: error.message
        };
      }
    }
  });
  tools.push(updateTopicTool);
  
  // Add task update tool if conversationId is provided
  if (conversationId && Array.isArray(richContext?.currentTasks) && richContext.currentTasks.length > 0) {
    console.log(`[Bash Agent] Current conversation has ${richContext.currentTasks.length} tasks - enabling update_task_status tool`);
    const updateTaskTool = tool({
      name: 'update_task_status',
      description: 'Update the status of a task in the current conversation. Use this to mark tasks as in_progress or completed.',
      parameters: z.object({
        taskIndex: z.number().describe('The index of the task (0-based) from the task list'),
        status: z.enum(['pending', 'in_progress', 'completed']).describe('New status for the task')
      }),
      execute: async ({ taskIndex, status }) => {
        try {
          const { updateTaskStatus } = await import('../agents/task-planning-agent.js');
          const result = await updateTaskStatus(conversationId, taskIndex, status);
          console.log(`[Bash Agent] Updated task ${taskIndex} to ${status}`);
          
          // Send SSE event to update the frontend
          const sseEmitter = global.currentSseEmitter;
          if (sseEmitter) {
            // Get updated task list and send to frontend
            const { getCurrentTasks } = await import('../agents/task-planning-agent.js');
            const tasksData = await getCurrentTasks(conversationId);
            
            let tasks = tasksData.success ? tasksData.tasks : [];
            
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
              const planPath = path.join(path.dirname(new URL(import.meta.url).pathname), '../data/plans', `TODO-${conversationId}.md`);
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
  
  // Add autonomy level context
  const autonomyContext = autonomyLevel === 'high' 
    ? '\n\n## AUTONOMY MODE: HIGH\nYou have full autonomy. Execute all operations immediately without asking for confirmation. The user trusts you to complete the task.'
    : autonomyLevel === 'medium'
    ? '\n\n## AUTONOMY MODE: MEDIUM\nExecute most operations immediately. Only confirm genuinely risky operations (bulk deletes, operations affecting 50+ items).'
    : '\n\n## AUTONOMY MODE: LOW\nConfirm all write operations before executing. This is a careful mode for sensitive operations.';
  
  // Combine the contextual prompt with autonomy and task
  const finalPrompt = contextualPrompt + autonomyContext + `\n\nYour specific task: ${task}`;
  
  return new Agent({
    name,
    instructions: finalPrompt,
    tools,
    model: 'gpt-4.1-mini'
  });
}