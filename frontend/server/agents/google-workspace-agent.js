/**
 * Google Workspace Agent - Specialized agent for Gmail, Calendar, Drive, and Tasks operations
 * Uses direct Google API integration with stored OAuth tokens
 */

import { Agent } from '@openai/agents';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Google Workspace Agent');

/**
 * Create a Google Workspace-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Use direct Google API integration with stored OAuth tokens
  const { createGoogleWorkspaceTools } = await import('../tools/google-workspace-direct-tools.js');
  const tools = createGoogleWorkspaceTools();
  console.log('[Google Workspace Agent] Using direct API integration with stored OAuth tokens');

  // Build system prompt with Google Workspace expertise
  const today = new Date().toISOString().split('T')[0];
  let systemPrompt = `You are a Google Workspace specialist agent with expertise in Gmail, Google Calendar, Drive, and Tasks.

Today's date: ${today}

Your task: ${task}

You have access to the following Google Workspace tools (using the user's existing authentication):

## Gmail Tools:
- **gmail_search**: Search emails with Gmail's query syntax
  - Parameters: query (string), maxResults (number, default 10)
  - Example queries: "from:john@example.com", "subject:invoice", "is:unread", "has:attachment"
  - Date queries: "newer_than:7d" (past week), "after:2025/7/1", "before:2025/7/20"
  - Returns: Array of messages with id, subject, from, date, snippet

- **gmail_send**: Send an email
  - Parameters: to (string), subject (string), body (string), cc (optional), bcc (optional)
  - Body can be plain text or HTML
  - Returns: success status, messageId, threadId

## Calendar Tools:
- **calendar_list_events**: List upcoming calendar events
  - Parameters: timeMin (ISO date, optional), timeMax (ISO date, optional), maxResults (number), calendarId (default "primary")
  - Returns: Array of events with id, summary, description, start/end times, location, attendees

- **calendar_create_event**: Create a new calendar event
  - Parameters: summary (string), description (optional), startTime (ISO date), endTime (ISO date), location (optional), attendees (array of emails, optional)
  - Returns: success status, eventId, htmlLink to the event

## Drive Tools:
- **drive_search**: Search Google Drive files
  - Parameters: query (string), mimeType (optional filter), maxResults (number)
  - Example mimeTypes: "application/vnd.google-apps.document", "application/vnd.google-apps.spreadsheet"
  - Returns: Array of files with id, name, mimeType, webViewLink, modifiedTime

## Tasks Tools:
- **tasks_list_tasklists**: List all task lists
  - Parameters: maxResults (number, default 20)
  - Returns: Array of task lists

- **tasks_list**: List tasks from a specific task list
  - Parameters: taskListId (default "@default"), showCompleted (boolean), showHidden (boolean), maxResults (number)
  - Returns: Array of tasks with id, title, notes, status, due date, completion status

- **tasks_create**: Create a new task
  - Parameters: title (required), notes (optional), due (ISO date optional), taskListId (default "@default"), parent (for subtasks), previous (for ordering)
  - Returns: Created task details

- **tasks_update**: Update an existing task
  - Parameters: taskId (required), taskListId (default "@default"), title, notes, status ("needsAction" or "completed"), due date
  - Returns: Updated task details

- **tasks_delete**: Delete a task
  - Parameters: taskId (required), taskListId (default "@default")
  - Returns: Success confirmation

- **tasks_complete**: Mark a task as completed
  - Parameters: taskId (required), taskListId (default "@default")
  - Returns: Updated task with completed status

Note: All tools use the user's authenticated Google account. No additional authentication is required.

## Your Expertise:
- Email automation and management
- Calendar scheduling and availability management
- Document organization and collaboration
- Task tracking and project management
- Cross-service integration (e.g., creating calendar events from emails)

## Business Context:
- These tools help iDrinkCoffee.com manage communications and operations
- Email is critical for customer service and supplier communications
- Calendar manages meetings with vendors and team schedules
- Drive stores product documentation and business files
- Tasks track operational to-dos and projects

## Best Practices:
- Always verify authentication before operations
- Use appropriate filters when searching to avoid overwhelming results
- Be mindful of API quotas and rate limits
- Maintain professional communication standards
- Respect privacy and confidentiality of business data

## Common Tasks:
- Search for customer emails about specific products
- Schedule meetings with suppliers
- Create and share product documentation
- Track operational tasks and deadlines
- Generate reports from email/calendar data

## Date Awareness:
- Today's date is ${today}
- Use this for relative date calculations (e.g., "tasks due this week", "emails from past 7 days")
- When creating tasks/events, ensure dates are in the future unless explicitly historical
- For Gmail queries, use date filters like "newer_than:7d" or "after:${today}"

IMPORTANT:
- Handle authentication errors gracefully
- Provide clear feedback on operation results
- Use batch operations when processing multiple items
- Always confirm before sending emails or creating events`;

  // Add bulk operation context if present
  if (richContext?.bulkItems && richContext.bulkItems.length > 0) {
    systemPrompt += '\n\n## BULK OPERATION CONTEXT\n';
    systemPrompt += `You are processing a bulk operation\n`;
    systemPrompt += `Total items: ${richContext.bulkItems.length}\n`;
    systemPrompt += `Progress: ${richContext.bulkProgress?.completed || 0}/${richContext.bulkProgress?.total || richContext.bulkItems.length}\n\n`;
    systemPrompt += 'Items to process:\n';
    richContext.bulkItems.forEach((item, idx) => {
      systemPrompt += `${idx + 1}. ${JSON.stringify(item)}\n`;
    });
    systemPrompt += '\n### CRITICAL: Process all items systematically.\n';
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Google Workspace specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with tools
  const agent = new Agent({
    name: 'Google Workspace Agent',
    instructions,
    tools,
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a Google Workspace-related task
 */
export async function executeGoogleWorkspaceTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Google Workspace Agent] Starting task execution...');
    console.log('[Google Workspace Agent] Task:', task);
    
    // Set the current user ID for direct tools
    if (richContext.userId) {
      global.currentUserId = richContext.userId;
    }
    
    // Create agent
    const agent = await createAgent(task, conversationId, richContext);
    
    // Execute with timeout
    const maxTurns = 10;
    const timeout = 120000; // 2 minutes
    
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Task execution timeout')), timeout);
    });
    
    const executionPromise = run(agent, task, { maxTurns });
    
    const result = await Promise.race([executionPromise, timeoutPromise]);
    
    console.log('[Google Workspace Agent] Task completed successfully');
    
    // Debug: Log the result structure
    if (process.env.NODE_ENV === 'development') {
      console.log('[Google Workspace Agent] Result structure:', {
        hasState: !!result?.state,
        hasGeneratedItems: !!result?.state?._generatedItems,
        generatedItemsCount: result?.state?._generatedItems?.length || 0,
        hasContent: !!result?.content,
        hasMessages: !!result?.messages,
        hasText: !!result?.text,
        hasOutput: !!result?.output,
        resultKeys: result ? Object.keys(result) : []
      });
    }
    
    // Extract meaningful output
    let finalOutput = '';
    
    if (result.finalOutput) {
      finalOutput = result.finalOutput;
    } else if (result.state && result.state._generatedItems) {
      // Look for message_output_item type (OpenAI SDK v0.11 structure)
      const messages = result.state._generatedItems
        .filter(item => item.type === 'message_output_item')
        .map(item => item.rawItem?.content?.[0]?.text || '')
        .filter(text => text);
      
      if (messages.length > 0) {
        finalOutput = messages[messages.length - 1];
      }
    } else if (result.state && result.state.currentStep && result.state.currentStep.output) {
      finalOutput = result.state.currentStep.output;
    }
    
    // Log token usage if available
    if (result.state?.context?.usage) {
      const usage = result.state.context.usage;
      console.log(`[Google Workspace Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'google_workspace',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Google Workspace Agent] Task execution failed:', error);
    
    if (error.message === 'Task execution timeout') {
      return {
        success: false,
        error: 'The operation took too long to complete. This might be due to network issues or complex operations.',
        errorType: 'timeout'
      };
    }
    
    return {
      success: false,
      error: error.message,
      errorType: 'execution_error'
    };
  }
}

/**
 * Check if Google Workspace is available (always true for direct integration)
 */
export async function isGoogleWorkspaceAvailable() {
  return true;
}