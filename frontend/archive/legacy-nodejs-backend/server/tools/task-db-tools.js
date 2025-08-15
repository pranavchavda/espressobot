import { tool } from '@openai/agents';
import { z } from 'zod';
import PrismaClient from '@prisma/client';

const prisma = new PrismaClient();

// Tool to create a task plan with tasks
export const createTaskPlanDbTool = tool({
  name: 'create_task_plan',
  description: 'Create a task plan with tasks in the database',
  parameters: z.object({
    title: z.string().describe('Title of the task plan'),
    description: z.string().describe('Description of what needs to be accomplished'),
    tasks: z.array(z.object({
      id: z.string().describe('Unique task ID (e.g., t1, t2)'),
      description: z.string().describe('Task description'),
      priority: z.enum(['high', 'medium', 'low']).describe('Task priority'),
      dependencies: z.array(z.string()).nullable().default([]).describe('IDs of tasks this depends on'),
      assignTo: z.string().nullable().default(null).describe('Which agent should handle this task')
    })).describe('List of tasks to complete'),
    conversationId: z.string().describe('Conversation ID this plan belongs to')
  }),
  execute: async ({ title, description, tasks, conversationId }) => {
    try {
      const convId = parseInt(conversationId);
      
      // Create task plan
      const taskPlan = await prisma.task_plans.create({
        data: {
          conv_id: convId,
          title,
          description
        }
      });
      
      // Create tasks
      const createdTasks = await Promise.all(
        tasks.map(task => 
          prisma.tasks.create({
            data: {
              conv_id: convId,
              task_id: task.id,
              description: task.description,
              priority: task.priority,
              assigned_to: task.assignTo,
              dependencies: task.dependencies?.join(',') || null,
              status: 'pending'
            }
          })
        )
      );
      
      console.log(`[Task DB] Created task plan with ${tasks.length} tasks for conversation ${conversationId}`);
      
      return {
        success: true,
        planId: taskPlan.id,
        taskCount: createdTasks.length,
        tasks: createdTasks.map(t => ({
          id: t.task_id,
          description: t.description,
          status: t.status,
          priority: t.priority
        }))
      };
    } catch (error) {
      console.error('[Task DB] Error creating task plan:', error);
      return { success: false, error: error.message };
    }
  }
});

// Tool to update task status
export const updateTaskStatusDbTool = tool({
  name: 'update_task_status',
  description: 'Update the status of a task in the database',
  parameters: z.object({
    taskId: z.string().describe('ID of the task to update (e.g., t1, t2)'),
    status: z.enum(['pending', 'in_progress', 'completed', 'blocked']).describe('New status'),
    notes: z.string().nullable().default(null).describe('Optional notes about the status change'),
    conversationId: z.string().describe('Conversation ID')
  }),
  execute: async ({ taskId, status, notes, conversationId }) => {
    try {
      const convId = parseInt(conversationId);
      
      // Update task
      const updated = await prisma.tasks.updateMany({
        where: {
          conv_id: convId,
          task_id: taskId
        },
        data: {
          status,
          notes: notes || undefined,
          updated_at: new Date(),
          completed_at: status === 'completed' ? new Date() : undefined
        }
      });
      
      if (updated.count === 0) {
        return { success: false, error: `Task ${taskId} not found in conversation ${conversationId}` };
      }
      
      console.log(`[Task DB] Updated task ${taskId} to ${status} in conversation ${conversationId}`);
      
      return {
        success: true,
        taskId,
        newStatus: status,
        message: `Task ${taskId} updated to ${status}`
      };
    } catch (error) {
      console.error('[Task DB] Error updating task status:', error);
      return { success: false, error: error.message };
    }
  }
});

// Tool to get current tasks
export const getCurrentTasksDbTool = tool({
  name: 'get_current_tasks',
  description: 'Get the current task list from the database',
  parameters: z.object({
    conversationId: z.string().describe('Conversation ID to get tasks for'),
    includeCompleted: z.boolean().default(false).describe('Include completed tasks')
  }),
  execute: async ({ conversationId, includeCompleted }) => {
    try {
      const convId = parseInt(conversationId);
      
      // Build where clause
      const where = {
        conv_id: convId
      };
      
      if (!includeCompleted) {
        where.status = { not: 'completed' };
      }
      
      // Get tasks
      const tasks = await prisma.tasks.findMany({
        where,
        orderBy: [
          { priority: 'asc' },
          { task_id: 'asc' }
        ]
      });
      
      // Count by status
      const allTasks = await prisma.tasks.findMany({
        where: { conv_id: convId }
      });
      
      const pendingCount = allTasks.filter(t => t.status === 'pending').length;
      const inProgressCount = allTasks.filter(t => t.status === 'in_progress').length;
      const completedCount = allTasks.filter(t => t.status === 'completed').length;
      const blockedCount = allTasks.filter(t => t.status === 'blocked').length;
      
      return {
        success: true,
        tasks: tasks.map(t => ({
          id: t.task_id,
          description: t.description,
          status: t.status,
          priority: t.priority,
          assignedTo: t.assigned_to,
          dependencies: t.dependencies ? t.dependencies.split(',') : [],
          notes: t.notes,
          createdAt: t.created_at,
          updatedAt: t.updated_at
        })),
        totalCount: allTasks.length,
        pendingCount,
        inProgressCount,
        completedCount,
        blockedCount
      };
    } catch (error) {
      console.error('[Task DB] Error getting tasks:', error);
      return { success: false, error: error.message };
    }
  }
});

// Simplified tool for agents to report progress
export const reportTaskProgressDbTool = tool({
  name: 'report_task_progress',
  description: 'Report progress on a task. Use this when starting or completing a task.',
  parameters: z.object({
    taskId: z.string().describe('The task ID from the plan (e.g., t1, t2)'),
    status: z.enum(['in_progress', 'completed', 'blocked']).describe('Current status of the task'),
    message: z.string().describe('Brief message about what was done or any issues'),
    conversationId: z.string().describe('The conversation ID (extract from context)')
  }),
  execute: async ({ taskId, status, message, conversationId }) => {
    return updateTaskStatusDbTool.execute({ 
      taskId, 
      status, 
      notes: message, 
      conversationId 
    });
  }
});

// Tool to get tasks for SSE updates
export async function getTasksForConversation(conversationId) {
  try {
    const convId = parseInt(conversationId);
    const tasks = await prisma.tasks.findMany({
      where: { conv_id: convId },
      orderBy: [
        { priority: 'asc' },
        { task_id: 'asc' }
      ]
    });
    
    return tasks.map(t => ({
      id: t.task_id,
      description: t.description,
      status: t.status,
      priority: t.priority,
      assignedTo: t.assigned_to,
      notes: t.notes
    }));
  } catch (error) {
    console.error('[Task DB] Error getting tasks for SSE:', error);
    return [];
  }
}