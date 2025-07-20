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
        cc: z.string().optional().describe('CC recipients (comma-separated)'),
        bcc: z.string().optional().describe('BCC recipients (comma-separated)')
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
        timeMin: z.string().optional().describe('Start time (ISO format, defaults to now)'),
        timeMax: z.string().optional().describe('End time (ISO format)'),
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
        description: z.string().optional().describe('Event description'),
        startTime: z.string().describe('Start time (ISO format)'),
        endTime: z.string().describe('End time (ISO format)'),
        location: z.string().optional().describe('Event location'),
        attendees: z.array(z.string()).optional().describe('Attendee email addresses')
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
        mimeType: z.string().optional().describe('Filter by MIME type (e.g., "application/vnd.google-apps.document")'),
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
 * Create all Google Workspace tools
 */
export function createGoogleWorkspaceTools() {
  return [
    ...createGmailTools(),
    ...createCalendarTools(),
    ...createDriveTools()
  ];
}