/**
 * Direct Google Workspace Tools
 * 
 * These tools use the Google APIs directly with the user's stored OAuth tokens,
 * eliminating the need for a separate MCP authentication flow.
 */

import { google } from 'googleapis';
import { tool } from '@openai/agents';
import { z } from 'zod';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

/**
 * Get OAuth2 client with user's stored tokens
 */
async function getAuthClient(userId) {
  const user = await prisma.users.findUnique({
    where: { id: userId },
    select: {
      google_access_token: true,
      google_refresh_token: true,
      google_token_expiry: true
    }
  });
  
  if (!user?.google_access_token) {
    throw new Error('User has not authorized Google Workspace access');
  }
  
  const oauth2Client = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    process.env.GOOGLE_CALLBACK_URL
  );
  
  oauth2Client.setCredentials({
    access_token: user.google_access_token,
    refresh_token: user.google_refresh_token
  });
  
  // Handle token refresh if needed
  oauth2Client.on('tokens', async (tokens) => {
    await prisma.users.update({
      where: { id: userId },
      data: {
        google_access_token: tokens.access_token,
        google_token_expiry: new Date(Date.now() + (tokens.expiry_date || 3600000))
      }
    });
  });
  
  return oauth2Client;
}

/**
 * Gmail Tools
 */
export function createGmailTools() {
  return [
    tool({
      name: 'gmail_search',
      description: 'Search Gmail messages',
      parameters: z.object({
        query: z.string().describe('Gmail search query (e.g., "from:example@gmail.com subject:invoice")'),
        maxResults: z.number().default(10).describe('Maximum number of results')
      }),
      execute: async ({ query, maxResults }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const gmail = google.gmail({ version: 'v1', auth });
        
        const response = await gmail.users.messages.list({
          userId: 'me',
          q: query,
          maxResults
        });
        
        // Fetch full message details for each result
        const messages = await Promise.all(
          (response.data.messages || []).map(async (msg) => {
            const detail = await gmail.users.messages.get({
              userId: 'me',
              id: msg.id
            });
            
            const headers = detail.data.payload.headers;
            return {
              id: msg.id,
              subject: headers.find(h => h.name === 'Subject')?.value,
              from: headers.find(h => h.name === 'From')?.value,
              date: headers.find(h => h.name === 'Date')?.value,
              snippet: detail.data.snippet
            };
          })
        );
        
        return { messages };
      }
    }),
    
    tool({
      name: 'gmail_send',
      description: 'Send an email via Gmail',
      parameters: z.object({
        to: z.string().describe('Recipient email address'),
        subject: z.string().describe('Email subject'),
        body: z.string().describe('Email body (plain text or HTML)'),
        cc: z.string().nullable().default(null).describe('CC recipients (comma-separated)'),
        bcc: z.string().nullable().default(null).describe('BCC recipients (comma-separated)')
      }),
      execute: async ({ to, subject, body, cc, bcc }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const gmail = google.gmail({ version: 'v1', auth });
        
        // Create email message
        const messageParts = [
          `To: ${to}`,
          `Subject: ${subject}`
        ];
        
        if (cc) messageParts.push(`Cc: ${cc}`);
        if (bcc) messageParts.push(`Bcc: ${bcc}`);
        
        messageParts.push('', body); // Empty line before body
        
        const message = messageParts.join('\n');
        const encodedMessage = Buffer.from(message).toString('base64').replace(/\+/g, '-').replace(/\//g, '_');
        
        const result = await gmail.users.messages.send({
          userId: 'me',
          requestBody: {
            raw: encodedMessage
          }
        });
        
        return { 
          success: true, 
          messageId: result.data.id,
          threadId: result.data.threadId
        };
      }
    })
  ];
}

/**
 * Calendar Tools
 */
export function createCalendarTools() {
  return [
    tool({
      name: 'calendar_list_events',
      description: 'List upcoming calendar events',
      parameters: z.object({
        timeMin: z.string().nullable().default(null).describe('Start time (ISO format, defaults to now)'),
        timeMax: z.string().nullable().default(null).describe('End time (ISO format)'),
        maxResults: z.number().default(10).describe('Maximum number of events'),
        calendarId: z.string().default('primary').describe('Calendar ID (default: primary)')
      }),
      execute: async ({ timeMin, timeMax, maxResults, calendarId }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const calendar = google.calendar({ version: 'v3', auth });
        
        const response = await calendar.events.list({
          calendarId,
          timeMin: timeMin || new Date().toISOString(),
          timeMax,
          maxResults,
          singleEvents: true,
          orderBy: 'startTime'
        });
        
        const events = response.data.items.map(event => ({
          id: event.id,
          summary: event.summary,
          description: event.description,
          start: event.start?.dateTime || event.start?.date,
          end: event.end?.dateTime || event.end?.date,
          location: event.location,
          attendees: event.attendees?.map(a => ({ email: a.email, responseStatus: a.responseStatus }))
        }));
        
        return { events };
      }
    }),
    
    tool({
      name: 'calendar_create_event',
      description: 'Create a new calendar event',
      parameters: z.object({
        summary: z.string().describe('Event title'),
        description: z.string().nullable().default(null).describe('Event description'),
        startTime: z.string().describe('Start time (ISO format)'),
        endTime: z.string().describe('End time (ISO format)'),
        location: z.string().nullable().default(null).describe('Event location'),
        attendees: z.array(z.string()).nullable().default(null).describe('Attendee email addresses')
      }),
      execute: async ({ summary, description, startTime, endTime, location, attendees }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const calendar = google.calendar({ version: 'v3', auth });
        
        const event = {
          summary,
          description,
          location,
          start: { dateTime: startTime },
          end: { dateTime: endTime },
          attendees: attendees?.map(email => ({ email }))
        };
        
        const result = await calendar.events.insert({
          calendarId: 'primary',
          requestBody: event
        });
        
        return {
          success: true,
          eventId: result.data.id,
          htmlLink: result.data.htmlLink
        };
      }
    })
  ];
}

/**
 * Drive Tools  
 */
export function createDriveTools() {
  return [
    tool({
      name: 'drive_search',
      description: 'Search Google Drive files',
      parameters: z.object({
        query: z.string().describe('Search query'),
        mimeType: z.string().nullable().default(null).describe('Filter by MIME type (e.g., "application/vnd.google-apps.document")'),
        maxResults: z.number().default(10).describe('Maximum results')
      }),
      execute: async ({ query, mimeType, maxResults }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const drive = google.drive({ version: 'v3', auth });
        
        let q = `name contains '${query}'`;
        if (mimeType) {
          q += ` and mimeType='${mimeType}'`;
        }
        
        const response = await drive.files.list({
          q,
          pageSize: maxResults,
          fields: 'files(id, name, mimeType, webViewLink, modifiedTime)'
        });
        
        return { files: response.data.files };
      }
    })
  ];
}

/**
 * Tasks Tools
 */
export function createTasksTools() {
  return [
    tool({
      name: 'tasks_list_tasklists',
      description: 'List all task lists',
      parameters: z.object({
        maxResults: z.number().default(20).describe('Maximum number of task lists to return')
      }),
      execute: async ({ maxResults }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const tasks = google.tasks({ version: 'v1', auth });
        
        const response = await tasks.tasklists.list({
          maxResults
        });
        
        return { 
          taskLists: response.data.items || []
        };
      }
    }),
    
    tool({
      name: 'tasks_list',
      description: 'List tasks from a specific task list',
      parameters: z.object({
        taskListId: z.string().default('@default').describe('Task list ID (default: @default for primary list)'),
        showCompleted: z.boolean().default(false).describe('Include completed tasks'),
        showHidden: z.boolean().default(false).describe('Include hidden tasks'),
        maxResults: z.number().default(20).describe('Maximum number of tasks to return')
      }),
      execute: async ({ taskListId, showCompleted, showHidden, maxResults }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const tasks = google.tasks({ version: 'v1', auth });
        
        const response = await tasks.tasks.list({
          tasklist: taskListId,
          showCompleted,
          showHidden,
          maxResults
        });
        
        const taskItems = (response.data.items || []).map(task => ({
          id: task.id,
          title: task.title,
          notes: task.notes,
          status: task.status,
          due: task.due,
          completed: task.completed,
          position: task.position,
          parent: task.parent,
          links: task.links
        }));
        
        return { 
          tasks: taskItems
        };
      }
    }),
    
    tool({
      name: 'tasks_create',
      description: 'Create a new task',
      parameters: z.object({
        title: z.string().describe('Task title'),
        notes: z.string().nullable().default(null).describe('Task notes/description'),
        due: z.string().nullable().default(null).describe('Due date (RFC 3339 timestamp)'),
        taskListId: z.string().default('@default').describe('Task list ID (default: @default)'),
        parent: z.string().nullable().default(null).describe('Parent task ID for subtasks'),
        previous: z.string().nullable().default(null).describe('Previous task ID for ordering')
      }),
      execute: async ({ title, notes, due, taskListId, parent, previous }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const tasks = google.tasks({ version: 'v1', auth });
        
        const task = {
          title,
          ...(notes && { notes }),
          ...(due && { due }),
          ...(parent && { parent })
        };
        
        const result = await tasks.tasks.insert({
          tasklist: taskListId,
          requestBody: task,
          ...(previous && { previous })
        });
        
        return {
          success: true,
          task: {
            id: result.data.id,
            title: result.data.title,
            notes: result.data.notes,
            status: result.data.status,
            due: result.data.due,
            position: result.data.position
          }
        };
      }
    }),
    
    tool({
      name: 'tasks_update',
      description: 'Update an existing task',
      parameters: z.object({
        taskId: z.string().describe('Task ID to update'),
        taskListId: z.string().default('@default').describe('Task list ID'),
        title: z.string().nullable().default(null).describe('New title'),
        notes: z.string().nullable().default(null).describe('New notes'),
        status: z.enum(['needsAction', 'completed']).nullable().default(null).describe('Task status'),
        due: z.string().nullable().default(null).describe('New due date (RFC 3339 timestamp)')
      }),
      execute: async ({ taskId, taskListId, title, notes, status, due }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const tasks = google.tasks({ version: 'v1', auth });
        
        // First get the current task
        const current = await tasks.tasks.get({
          tasklist: taskListId,
          task: taskId
        });
        
        // Merge updates
        const updatedTask = {
          ...current.data,
          ...(title !== null && { title }),
          ...(notes !== null && { notes }),
          ...(status !== null && { status }),
          ...(due !== null && { due })
        };
        
        const result = await tasks.tasks.update({
          tasklist: taskListId,
          task: taskId,
          requestBody: updatedTask
        });
        
        return {
          success: true,
          task: {
            id: result.data.id,
            title: result.data.title,
            notes: result.data.notes,
            status: result.data.status,
            due: result.data.due,
            completed: result.data.completed
          }
        };
      }
    }),
    
    tool({
      name: 'tasks_delete',
      description: 'Delete a task',
      parameters: z.object({
        taskId: z.string().describe('Task ID to delete'),
        taskListId: z.string().default('@default').describe('Task list ID')
      }),
      execute: async ({ taskId, taskListId }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const tasks = google.tasks({ version: 'v1', auth });
        
        await tasks.tasks.delete({
          tasklist: taskListId,
          task: taskId
        });
        
        return {
          success: true,
          message: `Task ${taskId} deleted successfully`
        };
      }
    }),
    
    tool({
      name: 'tasks_complete',
      description: 'Mark a task as completed',
      parameters: z.object({
        taskId: z.string().describe('Task ID to complete'),
        taskListId: z.string().default('@default').describe('Task list ID')
      }),
      execute: async ({ taskId, taskListId }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const tasks = google.tasks({ version: 'v1', auth });
        
        const result = await tasks.tasks.update({
          tasklist: taskListId,
          task: taskId,
          requestBody: {
            status: 'completed'
          }
        });
        
        return {
          success: true,
          task: {
            id: result.data.id,
            title: result.data.title,
            status: result.data.status,
            completed: result.data.completed
          }
        };
      }
    })
  ];
}

/**
 * Create all Google Workspace tools
 */
export function createGoogleWorkspaceTools() {
  return [
    ...createGmailTools(),
    ...createCalendarTools(),
    ...createDriveTools(),
    ...createTasksTools()
  ];
}