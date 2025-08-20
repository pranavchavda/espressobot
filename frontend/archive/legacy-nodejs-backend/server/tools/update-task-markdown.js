import { readFile, writeFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const plansDir = path.join(__dirname, '../../plans');

/**
 * Updates a task's status in the markdown file
 * @param {string} conversationId - The conversation ID
 * @param {string} taskId - The task ID to update (e.g., 't1', 't2')
 * @param {string} status - The new status ('pending', 'in_progress', 'completed', 'blocked')
 * @param {string} notes - Optional notes about the update
 * @returns {Promise<{success: boolean, message: string, updatedContent?: string}>}
 */
export async function updateTaskInMarkdown(conversationId, taskId, status, notes = null) {
  try {
    // Find the latest markdown file for this conversation
    const files = await readdir(plansDir);
    const convFiles = files
      .filter(f => f.startsWith(`${conversationId}_`) && f.endsWith('.md'))
      .sort((a, b) => {
        const timeA = parseInt(a.split('_')[1].split('.')[0]);
        const timeB = parseInt(b.split('_')[1].split('.')[0]);
        return timeB - timeA; // Latest first
      });
    
    if (convFiles.length === 0) {
      return { success: false, message: `No task plan found for conversation ${conversationId}` };
    }
    
    const latestFile = convFiles[0];
    const filepath = path.join(plansDir, latestFile);
    let content = await readFile(filepath, 'utf-8');
    
    // Find and update the task
    const lines = content.split('\n');
    let taskFound = false;
    let updatedLines = lines.map(line => {
      // Match task lines like: - [ ] **t1**: Description
      const taskMatch = line.match(/^(\s*)-\s*\[([ x])\]\s*\*\*([^*]+)\*\*:(.*)/);
      if (taskMatch && taskMatch[3] === taskId) {
        taskFound = true;
        const indent = taskMatch[1];
        const taskDesc = taskMatch[4];
        
        // Update checkbox based on status
        let checkbox = ' ';
        let statusEmoji = '';
        if (status === 'completed') {
          checkbox = 'x';
          statusEmoji = ' ✅';
        } else if (status === 'in_progress') {
          checkbox = ' ';
          statusEmoji = ' 🔄';
        } else if (status === 'blocked') {
          checkbox = ' ';
          statusEmoji = ' 🚫';
        }
        
        // Reconstruct the line
        let newLine = `${indent}- [${checkbox}] **${taskId}**:${taskDesc}${statusEmoji}`;
        
        // Add notes if provided
        if (notes) {
          newLine += `\n${indent}  - _Note: ${notes}_`;
        }
        
        return newLine;
      }
      return line;
    });
    
    if (!taskFound) {
      return { success: false, message: `Task ${taskId} not found in plan` };
    }
    
    // Write updated content back to file
    const updatedContent = updatedLines.join('\n');
    await writeFile(filepath, updatedContent, 'utf-8');
    
    return {
      success: true,
      message: `Task ${taskId} updated to ${status}`,
      updatedContent
    };
  } catch (error) {
    console.error('Error updating task in markdown:', error);
    return { success: false, message: error.message };
  }
}

/**
 * Get all tasks from a conversation's markdown file
 * @param {string} conversationId - The conversation ID
 * @returns {Promise<{success: boolean, tasks?: Array, message?: string}>}
 */
export async function getTasksFromMarkdown(conversationId) {
  try {
    // Find the latest markdown file for this conversation
    const files = await readdir(plansDir);
    const convFiles = files
      .filter(f => f.startsWith(`${conversationId}_`) && f.endsWith('.md'))
      .sort((a, b) => {
        const timeA = parseInt(a.split('_')[1].split('.')[0]);
        const timeB = parseInt(b.split('_')[1].split('.')[0]);
        return timeB - timeA; // Latest first
      });
    
    if (convFiles.length === 0) {
      return { success: false, message: `No task plan found for conversation ${conversationId}` };
    }
    
    const latestFile = convFiles[0];
    const filepath = path.join(plansDir, latestFile);
    const content = await readFile(filepath, 'utf-8');
    
    // Parse tasks from markdown
    const tasks = [];
    const lines = content.split('\n');
    
    for (const line of lines) {
      const taskMatch = line.match(/^(\s*)-\s*\[([ x])\]\s*\*\*([^*]+)\*\*:(.*)/);
      if (taskMatch) {
        const isCompleted = taskMatch[2] === 'x';
        const taskId = taskMatch[3];
        const description = taskMatch[4].trim();
        
        // Determine status based on content
        let status = 'pending';
        if (isCompleted || description.includes('✅')) {
          status = 'completed';
        } else if (description.includes('🔄')) {
          status = 'in_progress';
        } else if (description.includes('🚫')) {
          status = 'blocked';
        }
        
        tasks.push({
          id: taskId,
          description: description.replace(/[✅🔄🚫]/g, '').trim(),
          status,
          completed: isCompleted
        });
      }
    }
    
    return {
      success: true,
      tasks,
      filename: latestFile,
      content
    };
  } catch (error) {
    console.error('Error reading tasks from markdown:', error);
    return { success: false, message: error.message };
  }
}