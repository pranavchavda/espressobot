import { tool } from '@openai/agents';
import { z } from 'zod';
import fs from 'fs/promises';
import path from 'path';

const SCRATCHPAD_FILE = path.join(process.cwd(), 'server', 'data', 'scratchpad.json');

// Ensure data directory exists
async function ensureDataDirectory() {
  const dataDir = path.dirname(SCRATCHPAD_FILE);
  try {
    await fs.access(dataDir);
  } catch {
    await fs.mkdir(dataDir, { recursive: true });
  }
}

// Load scratchpad data
async function loadScratchpad() {
  try {
    await ensureDataDirectory();
    const data = await fs.readFile(SCRATCHPAD_FILE, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    // Return empty scratchpad if file doesn't exist
    return {
      content: '',
      entries: [],
      last_updated: null,
      created_at: new Date().toISOString()
    };
  }
}

// Save scratchpad data
async function saveScratchpad(data) {
  await ensureDataDirectory();
  data.last_updated = new Date().toISOString();
  await fs.writeFile(SCRATCHPAD_FILE, JSON.stringify(data, null, 2));
}

// Helper function to format scratchpad content for display
function formatScratchpadContent(scratchpad) {
  if (!scratchpad.content && scratchpad.entries.length === 0) {
    return 'Scratchpad is empty';
  }
  
  let formatted = '';
  if (scratchpad.content) {
    formatted += `**Main Content:**\n${scratchpad.content}\n\n`;
  }
  
  if (scratchpad.entries.length > 0) {
    formatted += '**Recent Entries:**\n';
    scratchpad.entries.slice(-10).forEach((entry, index) => {
      const timestamp = new Date(entry.timestamp).toLocaleString();
      formatted += `${index + 1}. [${timestamp}] ${entry.author}: ${entry.content}\n`;
    });
  }
  
  return formatted;
}

export const scratchpadTool = tool({
  name: 'scratchpad',
  description: 'Persistent scratchpad visible to all agents. Use for temporary notes, task coordination, and shared context that should persist across conversations.',
  parameters: z.object({
    action: z.enum(['read', 'write', 'append', 'add_entry', 'clear']).describe('Action to perform'),
    content: z.string().nullable().default(null).describe('Content to write/append (required for write, append, add_entry)'),
    author: z.string().nullable().default(null).describe('Author of the entry (user/orchestrator/agent name - for add_entry action)')
  }),
  execute: async ({ action, content, author }) => {
    try {
      const scratchpad = await loadScratchpad();
      
      switch (action) {
        case 'read':
          if (!scratchpad.content && scratchpad.entries.length === 0) {
            return { success: true, message: 'Scratchpad is empty', data: scratchpad };
          }
          return { 
            success: true, 
            message: 'Scratchpad content retrieved', 
            data: scratchpad,
            formatted: formatScratchpadContent(scratchpad)
          };
          
        case 'write':
          if (!content) {
            return { success: false, message: 'Content is required for write action' };
          }
          scratchpad.content = content;
          await saveScratchpad(scratchpad);
          return { success: true, message: 'Scratchpad content updated', data: scratchpad };
          
        case 'append':
          if (!content) {
            return { success: false, message: 'Content is required for append action' };
          }
          scratchpad.content = (scratchpad.content || '') + '\n' + content;
          await saveScratchpad(scratchpad);
          return { success: true, message: 'Content appended to scratchpad', data: scratchpad };
          
        case 'add_entry':
          if (!content) {
            return { success: false, message: 'Content is required for add_entry action' };
          }
          if (!scratchpad.entries) scratchpad.entries = [];
          
          const entry = {
            content,
            author: author || 'unknown',
            timestamp: new Date().toISOString(),
            id: scratchpad.entries.length + 1
          };
          
          scratchpad.entries.push(entry);
          
          // Keep only last 50 entries to prevent unlimited growth
          if (scratchpad.entries.length > 50) {
            scratchpad.entries = scratchpad.entries.slice(-50);
          }
          
          await saveScratchpad(scratchpad);
          return { success: true, message: 'Entry added to scratchpad', data: scratchpad, entry };
          
        case 'clear':
          const clearedScratchpad = {
            content: '',
            entries: [],
            last_updated: new Date().toISOString(),
            created_at: scratchpad.created_at || new Date().toISOString()
          };
          await saveScratchpad(clearedScratchpad);
          return { success: true, message: 'Scratchpad cleared', data: clearedScratchpad };
          
        default:
          return { success: false, message: `Unknown action: ${action}` };
      }
    } catch (error) {
      console.error('Scratchpad tool error:', error);
      return { success: false, message: `Error: ${error.message}` };
    }
  }
});