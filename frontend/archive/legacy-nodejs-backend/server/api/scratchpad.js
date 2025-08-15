import { Router } from 'express';
import { authenticateToken } from '../auth.js';
import fs from 'fs/promises';
import path from 'path';

const router = Router();

// Path to the scratchpad file
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

/**
 * POST /api/scratchpad
 * Handle scratchpad operations
 */
router.post('/', authenticateToken, async (req, res) => {
  try {
    const { action, content, author } = req.body;
    
    if (!action) {
      return res.status(400).json({ 
        success: false, 
        message: 'Action is required' 
      });
    }

    const scratchpad = await loadScratchpad();
    
    switch (action) {
      case 'read':
        if (!scratchpad.content && scratchpad.entries.length === 0) {
          return res.json({ 
            success: true, 
            message: 'Scratchpad is empty', 
            data: scratchpad 
          });
        }
        return res.json({ 
          success: true, 
          message: 'Scratchpad content retrieved', 
          data: scratchpad
        });
        
      case 'write':
        if (!content) {
          return res.status(400).json({ 
            success: false, 
            message: 'Content is required for write action' 
          });
        }
        scratchpad.content = content;
        await saveScratchpad(scratchpad);
        return res.json({ 
          success: true, 
          message: 'Scratchpad content updated', 
          data: scratchpad 
        });
        
      case 'append':
        if (!content) {
          return res.status(400).json({ 
            success: false, 
            message: 'Content is required for append action' 
          });
        }
        scratchpad.content = (scratchpad.content || '') + '\n' + content;
        await saveScratchpad(scratchpad);
        return res.json({ 
          success: true, 
          message: 'Content appended to scratchpad', 
          data: scratchpad 
        });
        
      case 'add_entry':
        if (!content) {
          return res.status(400).json({ 
            success: false, 
            message: 'Content is required for add_entry action' 
          });
        }
        if (!scratchpad.entries) scratchpad.entries = [];
        
        const entry = {
          content,
          author: author || 'User',
          timestamp: new Date().toISOString(),
          id: scratchpad.entries.length + 1
        };
        
        scratchpad.entries.push(entry);
        
        // Keep only last 50 entries to prevent unlimited growth
        if (scratchpad.entries.length > 50) {
          scratchpad.entries = scratchpad.entries.slice(-50);
        }
        
        await saveScratchpad(scratchpad);
        return res.json({ 
          success: true, 
          message: 'Entry added to scratchpad', 
          data: scratchpad, 
          entry 
        });
        
      case 'clear':
        const clearedScratchpad = {
          content: '',
          entries: [],
          last_updated: new Date().toISOString(),
          created_at: scratchpad.created_at || new Date().toISOString()
        };
        await saveScratchpad(clearedScratchpad);
        return res.json({ 
          success: true, 
          message: 'Scratchpad cleared', 
          data: clearedScratchpad 
        });
        
      default:
        return res.status(400).json({ 
          success: false, 
          message: `Unknown action: ${action}` 
        });
    }
  } catch (error) {
    console.error('Scratchpad API error:', error);
    return res.status(500).json({ 
      success: false, 
      message: `Error: ${error.message}` 
    });
  }
});

export default router;