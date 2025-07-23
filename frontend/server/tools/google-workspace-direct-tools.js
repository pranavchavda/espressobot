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
import fs from 'fs';
import path from 'path';

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
 * Extract folder ID from Google Drive URL
 */
function extractFolderIdFromUrl(url) {
  if (!url) return null;
  
  // Handle various Google Drive folder URL formats
  const patterns = [
    /\/folders\/([a-zA-Z0-9-_]+)/,  // https://drive.google.com/drive/folders/FOLDER_ID
    /\/drive\/u\/\d+\/folders\/([a-zA-Z0-9-_]+)/, // https://drive.google.com/drive/u/0/folders/FOLDER_ID
    /id=([a-zA-Z0-9-_]+)/, // https://drive.google.com/drive/folders/FOLDER_ID?id=FOLDER_ID
  ];
  
  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match) return match[1];
  }
  
  return null;
}

/**
 * Drive Tools  
 */
export function createDriveTools() {
  return [
    tool({
      name: 'drive_search',
      description: 'Search Google Drive files, optionally within a specific folder',
      parameters: z.object({
        query: z.string().describe('Search query'),
        mimeType: z.string().nullable().default(null).describe('Filter by MIME type (e.g., "application/vnd.google-apps.document")'),
        maxResults: z.number().default(10).describe('Maximum results'),
        folderUrl: z.string().nullable().default(null).describe('Google Drive folder URL to search within (optional)'),
        folderId: z.string().nullable().default(null).describe('Google Drive folder ID to search within (optional)')
      }),
      execute: async ({ query, mimeType, maxResults, folderUrl, folderId }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const drive = google.drive({ version: 'v3', auth });
        
        // Extract folder ID from URL if provided
        const targetFolderId = folderId || extractFolderIdFromUrl(folderUrl);
        
        let q = `name contains '${query}'`;
        if (mimeType) {
          q += ` and mimeType='${mimeType}'`;
        }
        if (targetFolderId) {
          q += ` and '${targetFolderId}' in parents`;
        }
        
        const response = await drive.files.list({
          q,
          pageSize: maxResults,
          fields: 'files(id, name, mimeType, webViewLink, modifiedTime, parents)'
        });
        
        return { 
          files: response.data.files,
          searchedInFolder: targetFolderId ? { id: targetFolderId, url: folderUrl } : null
        };
      }
    }),

    tool({
      name: 'drive_list_folder',
      description: 'List all files in a specific Google Drive folder',
      parameters: z.object({
        folderUrl: z.string().nullable().default(null).describe('Google Drive folder URL'),
        folderId: z.string().nullable().default(null).describe('Google Drive folder ID'),
        maxResults: z.number().default(50).describe('Maximum results'),
        includeSubfolders: z.boolean().default(false).describe('Include files from subfolders')
      }),
      execute: async ({ folderUrl, folderId, maxResults, includeSubfolders }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const drive = google.drive({ version: 'v3', auth });
        
        // Extract folder ID from URL if provided
        const targetFolderId = folderId || extractFolderIdFromUrl(folderUrl);
        
        if (!targetFolderId) {
          return {
            success: false,
            error: 'No valid folder ID or URL provided'
          };
        }
        
        try {
          // Get folder information first
          const folderInfo = await drive.files.get({
            fileId: targetFolderId,
            fields: 'id, name, mimeType, webViewLink'
          });
          
          // Build query
          let q = `'${targetFolderId}' in parents and trashed=false`;
          
          const response = await drive.files.list({
            q,
            pageSize: maxResults,
            fields: 'files(id, name, mimeType, webViewLink, modifiedTime, size, parents), nextPageToken',
            orderBy: 'name'
          });
          
          const files = response.data.files || [];
          
          // Separate folders and files
          const folders = files.filter(f => f.mimeType === 'application/vnd.google-apps.folder');
          const regularFiles = files.filter(f => f.mimeType !== 'application/vnd.google-apps.folder');
          
          return {
            success: true,
            folder: {
              id: folderInfo.data.id,
              name: folderInfo.data.name,
              webViewLink: folderInfo.data.webViewLink
            },
            totalFiles: files.length,
            folders: folders.map(f => ({
              id: f.id,
              name: f.name,
              webViewLink: f.webViewLink,
              modifiedTime: f.modifiedTime
            })),
            files: regularFiles.map(f => ({
              id: f.id,
              name: f.name,
              mimeType: f.mimeType,
              webViewLink: f.webViewLink,
              modifiedTime: f.modifiedTime,
              size: f.size
            })),
            hasMore: !!response.data.nextPageToken
          };
          
        } catch (error) {
          return {
            success: false,
            error: error.message,
            message: `Failed to list folder contents for ID: ${targetFolderId}`
          };
        }
      }
    }),

    tool({
      name: 'drive_download',
      description: 'Download a Google Drive file to local filesystem',
      parameters: z.object({
        fileId: z.string().describe('Google Drive file ID'),
        fileName: z.string().nullable().default(null).describe('Optional custom filename (will use original name if not provided)'),
        downloadPath: z.string().default('./downloads').describe('Local directory to save file (default: ./downloads)')
      }),
      execute: async ({ fileId, fileName, downloadPath }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const drive = google.drive({ version: 'v3', auth });
        
        try {
          // Get file metadata first
          const fileMetadata = await drive.files.get({
            fileId,
            fields: 'id, name, mimeType, size'
          });
          
          const originalName = fileMetadata.data.name;
          const mimeType = fileMetadata.data.mimeType;
          const finalFileName = fileName || originalName;
          
          // Ensure download directory exists
          if (!fs.existsSync(downloadPath)) {
            fs.mkdirSync(downloadPath, { recursive: true });
          }
          
          const filePath = path.join(downloadPath, finalFileName);
          
          // Handle Google Workspace files (need to export to different format)
          if (mimeType.startsWith('application/vnd.google-apps.')) {
            let exportMimeType;
            let extension = '';
            
            switch (mimeType) {
              case 'application/vnd.google-apps.document':
                exportMimeType = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
                extension = '.docx';
                break;
              case 'application/vnd.google-apps.spreadsheet':
                exportMimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
                extension = '.xlsx';
                break;
              case 'application/vnd.google-apps.presentation':
                exportMimeType = 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
                extension = '.pptx';
                break;
              case 'application/vnd.google-apps.drawing':
                exportMimeType = 'image/png';
                extension = '.png';
                break;
              default:
                // For other Google Apps formats, try PDF
                exportMimeType = 'application/pdf';
                extension = '.pdf';
            }
            
            // Add extension if not already present
            const finalFileNameWithExt = finalFileName.includes('.') ? finalFileName : finalFileName + extension;
            const finalFilePath = path.join(downloadPath, finalFileNameWithExt);
            
            const response = await drive.files.export({
              fileId,
              mimeType: exportMimeType
            }, { responseType: 'stream' });
            
            const writer = fs.createWriteStream(finalFilePath);
            response.data.pipe(writer);
            
            return new Promise((resolve, reject) => {
              writer.on('finish', () => {
                resolve({
                  success: true,
                  fileName: finalFileNameWithExt,
                  filePath: finalFilePath,
                  originalName,
                  mimeType,
                  exportFormat: exportMimeType,
                  message: `Google Workspace file "${originalName}" exported and downloaded as ${finalFileNameWithExt}`
                });
              });
              writer.on('error', reject);
            });
            
          } else {
            // Handle regular files (images, PDFs, etc.)
            const response = await drive.files.get({
              fileId,
              alt: 'media'
            }, { responseType: 'stream' });
            
            const writer = fs.createWriteStream(filePath);
            response.data.pipe(writer);
            
            return new Promise((resolve, reject) => {
              writer.on('finish', () => {
                resolve({
                  success: true,
                  fileName: finalFileName,
                  filePath,
                  originalName,
                  mimeType,
                  size: fileMetadata.data.size,
                  message: `File "${originalName}" downloaded successfully`
                });
              });
              writer.on('error', reject);
            });
          }
          
        } catch (error) {
          return {
            success: false,
            error: error.message,
            message: `Failed to download file with ID: ${fileId}`
          };
        }
      }
    }),

    tool({
      name: 'drive_get_file_info',
      description: 'Get detailed information about a Google Drive file including download URL',
      parameters: z.object({
        fileId: z.string().describe('Google Drive file ID')
      }),
      execute: async ({ fileId }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const drive = google.drive({ version: 'v3', auth });
        
        try {
          const response = await drive.files.get({
            fileId,
            fields: 'id, name, mimeType, size, webViewLink, webContentLink, downloadUrl, parents, createdTime, modifiedTime, owners, permissions'
          });
          
          const file = response.data;
          
          return {
            success: true,
            file: {
              id: file.id,
              name: file.name,
              mimeType: file.mimeType,
              size: file.size,
              webViewLink: file.webViewLink,
              webContentLink: file.webContentLink,
              downloadUrl: file.downloadUrl,
              parents: file.parents,
              createdTime: file.createdTime,
              modifiedTime: file.modifiedTime,
              owners: file.owners,
              isGoogleWorkspaceFile: file.mimeType?.startsWith('application/vnd.google-apps.'),
              canDownloadDirectly: !file.mimeType?.startsWith('application/vnd.google-apps.')
            }
          };
        } catch (error) {
          return {
            success: false,
            error: error.message,
            message: `Failed to get file info for ID: ${fileId}`
          };
        }
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
        maxResults: z.number().default(100).describe('Maximum number of tasks to return'),
        pageToken: z.string().nullable().default(null).describe('Page token for pagination')
      }),
      execute: async ({ taskListId, showCompleted, showHidden, maxResults, pageToken }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const tasks = google.tasks({ version: 'v1', auth });
        
        let allTasks = [];
        let nextPageToken = pageToken;
        
        // Fetch all pages to ensure we don't miss any tasks
        do {
          const response = await tasks.tasks.list({
            tasklist: taskListId,
            showCompleted,
            showHidden,
            maxResults: Math.min(maxResults, 100), // API max is 100
            pageToken: nextPageToken,
            showDeleted: false
          });
          
          if (response.data.items) {
            allTasks = allTasks.concat(response.data.items);
          }
          
          nextPageToken = response.data.nextPageToken;
          
          // Stop if we've reached the requested maxResults
          if (allTasks.length >= maxResults) {
            allTasks = allTasks.slice(0, maxResults);
            break;
          }
        } while (nextPageToken);
        
        const taskItems = allTasks.map(task => ({
          id: task.id,
          title: task.title,
          notes: task.notes,
          status: task.status,
          due: task.due,
          completed: task.completed,
          position: task.position,
          parent: task.parent,
          links: task.links,
          updated: task.updated,
          selfLink: task.selfLink,
          etag: task.etag,
          hidden: task.hidden
        }));
        
        return { 
          tasks: taskItems,
          totalTasks: taskItems.length,
          hasMore: !!nextPageToken
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
    }),
    
    tool({
      name: 'tasks_list_all',
      description: 'List ALL tasks including hidden and deleted ones (for debugging)',
      parameters: z.object({
        taskListId: z.string().default('@default').describe('Task list ID')
      }),
      execute: async ({ taskListId }) => {
        const userId = global.currentUserId;
        const auth = await getAuthClient(userId);
        const tasks = google.tasks({ version: 'v1', auth });
        
        let allTasks = [];
        let nextPageToken = null;
        
        // Fetch ALL tasks without any filters
        do {
          const response = await tasks.tasks.list({
            tasklist: taskListId,
            maxResults: 100,
            pageToken: nextPageToken,
            showCompleted: true,
            showHidden: true,
            showDeleted: true
          });
          
          if (response.data.items) {
            allTasks = allTasks.concat(response.data.items);
          }
          
          nextPageToken = response.data.nextPageToken;
        } while (nextPageToken);
        
        // Group tasks by status
        const tasksByStatus = {
          needsAction: allTasks.filter(t => t.status === 'needsAction'),
          completed: allTasks.filter(t => t.status === 'completed'),
          deleted: allTasks.filter(t => t.deleted),
          hidden: allTasks.filter(t => t.hidden)
        };
        
        return { 
          summary: {
            total: allTasks.length,
            needsAction: tasksByStatus.needsAction.length,
            completed: tasksByStatus.completed.length,
            deleted: tasksByStatus.deleted.length,
            hidden: tasksByStatus.hidden.length
          },
          tasksByStatus,
          allTasks: allTasks.map(task => ({
            id: task.id,
            title: task.title,
            notes: task.notes,
            status: task.status,
            due: task.due,
            completed: task.completed,
            position: task.position,
            parent: task.parent,
            hidden: task.hidden,
            deleted: task.deleted,
            updated: task.updated
          }))
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