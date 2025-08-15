import { tool } from '@openai/agents';
import { z } from 'zod';
import { updateTaskInMarkdown } from './update-task-markdown.js';

// Tool for agents to report task progress
export const reportTaskProgressTool = tool({
  name: 'report_task_progress',
  description: 'Report progress on a task from the task plan. Use this when starting or completing a task.',
  parameters: z.object({
    taskId: z.string().describe('The task ID from the plan (e.g., t1, t2)'),
    status: z.enum(['in_progress', 'completed', 'blocked']).describe('Current status of the task'),
    message: z.string().describe('Brief message about what was done or any issues'),
    conversationId: z.string().describe('The conversation ID (extract from context)')
  }),
  execute: async ({ taskId, status, message, conversationId }) => {
    try {
      console.log(`[Task Progress] Task ${taskId} -> ${status}: ${message}`);
      
      // Update the markdown file
      const result = await updateTaskInMarkdown(conversationId, taskId, status, message);
      
      if (!result.success) {
        console.error(`[Task Progress] Failed to update task: ${result.message}`);
        return {
          success: false,
          message: `Could not update task status: ${result.message}`
        };
      }
      
      return {
        success: true,
        message: `Task ${taskId} marked as ${status}`,
        details: message
      };
    } catch (error) {
      console.error('[Task Progress] Error:', error);
      return {
        success: false,
        message: `Error updating task: ${error.message}`
      };
    }
  }
});

// Simplified version for just marking completion
export const markTaskCompleteTool = tool({
  name: 'mark_task_complete',
  description: 'Mark a task as completed. Use this after successfully completing a task from the plan.',
  parameters: z.object({
    taskId: z.string().describe('The task ID from the plan (e.g., t1, t2)'),
    result: z.string().describe('Brief summary of what was accomplished'),
    conversationId: z.string().describe('The conversation ID (extract from context)')
  }),
  execute: async ({ taskId, result, conversationId }) => {
    try {
      console.log(`[Task Complete] Task ${taskId} completed: ${result}`);
      
      // Update the markdown file
      const updateResult = await updateTaskInMarkdown(conversationId, taskId, 'completed', result);
      
      if (!updateResult.success) {
        console.error(`[Task Complete] Failed to mark task complete: ${updateResult.message}`);
        return {
          success: false,
          message: `Could not mark task complete: ${updateResult.message}`
        };
      }
      
      return {
        success: true,
        message: `Task ${taskId} completed successfully`,
        result
      };
    } catch (error) {
      console.error('[Task Complete] Error:', error);
      return {
        success: false,
        message: `Error marking task complete: ${error.message}`
      };
    }
  }
});