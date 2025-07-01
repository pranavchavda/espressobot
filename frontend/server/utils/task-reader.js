import fs from 'fs/promises';
import path from 'path';
import { dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Define PLANS_DIR at module level
const PLANS_DIR = path.resolve(__dirname, '../plans');

/**
 * Reads tasks from a TODO markdown file for a given conversation
 * @param {string} conversationId - The conversation ID
 * @returns {Promise<{success: boolean, tasks: Array, markdown: string}>}
 */
export async function readTasksForConversation(conversationId) {
  try {
    const filePath = path.resolve(PLANS_DIR, `TODO-${conversationId}.md`);
    
    // Check if file exists
    try {
      await fs.access(filePath);
    } catch {
      // No task file exists for this conversation
      return {
        success: true,
        tasks: [],
        markdown: '',
        exists: false
      };
    }
    
    // Read the file content
    const content = await fs.readFile(filePath, 'utf-8');
    
    // Parse tasks from markdown
    const tasks = [];
    const lines = content.split(/\r?\n/);
    
    for (const line of lines) {
      // Match task format: - [ ] Task description or - [x] Task description
      const match = line.match(/^\s*-\s*\[( |x)\]\s*(.+)$/i);
      if (match) {
        const isCompleted = match[1].toLowerCase() === 'x';
        const description = match[2].trim();
        
        // Check if task is in progress (has 🔄 prefix)
        const inProgress = description.startsWith('🔄 ');
        const cleanDescription = inProgress ? description.substring(3).trim() : description;
        
        tasks.push({
          description: cleanDescription,
          status: isCompleted ? 'completed' : (inProgress ? 'in_progress' : 'pending'),
          originalLine: line
        });
      }
    }
    
    return {
      success: true,
      tasks,
      markdown: content,
      exists: true
    };
  } catch (error) {
    console.error('[TaskReader] Error reading tasks:', error);
    return {
      success: false,
      tasks: [],
      markdown: '',
      error: error.message
    };
  }
}

/**
 * Formats tasks into a readable string for system prompt injection
 * @param {Array} tasks - Array of task objects
 * @returns {string} Formatted task string
 */
export function formatTasksForPrompt(tasks) {
  if (!tasks || tasks.length === 0) {
    return '';
  }
  
  const taskLines = tasks.map((task, index) => {
    const statusEmoji = {
      'completed': '✅',
      'in_progress': '🔄',
      'pending': '⏳'
    }[task.status] || '❓';
    
    return `${index + 1}. ${statusEmoji} ${task.description} (${task.status})`;
  });
  
  return `Current Tasks for this conversation:
${taskLines.join('\n')}

You can see the current status of each task above. When working on tasks:
- Focus on pending (⏳) and in-progress (🔄) tasks
- Completed tasks (✅) are already done
- If you complete a task, you can mark it as completed using the update_task_status tool
`;
}

/**
 * Gets a summary of task completion status
 * @param {Array} tasks - Array of task objects
 * @returns {Object} Summary object with counts
 */
export function getTaskSummary(tasks) {
  const summary = {
    total: tasks.length,
    completed: 0,
    in_progress: 0,
    pending: 0
  };
  
  for (const task of tasks) {
    if (task.status === 'completed') summary.completed++;
    else if (task.status === 'in_progress') summary.in_progress++;
    else if (task.status === 'pending') summary.pending++;
  }
  
  summary.completionPercentage = summary.total > 0 
    ? Math.round((summary.completed / summary.total) * 100)
    : 0;
    
  return summary;
}

/**
 * Updates the status of a specific task in the TODO file
 * @param {string} conversationId - The conversation ID
 * @param {number} taskIndex - Zero-based index of the task
 * @param {string} newStatus - New status ('pending', 'in_progress', 'completed')
 * @returns {Promise<Object>} Result object
 */
export async function updateTaskStatus(conversationId, taskIndex, newStatus) {
  try {
    const todoPath = path.join(PLANS_DIR, `TODO-${conversationId}.md`);
    
    // Read current tasks
    const result = await readTasksForConversation(conversationId);
    if (!result.success || !result.exists) {
      return { success: false, error: 'No tasks found for this conversation' };
    }
    
    // Validate task index
    if (taskIndex < 0 || taskIndex >= result.tasks.length) {
      return { success: false, error: `Invalid task index: ${taskIndex}` };
    }
    
    // Update the task status
    result.tasks[taskIndex].status = newStatus;
    
    // Rebuild the markdown content
    const lines = result.markdown.split('\n');
    const updatedLines = [];
    let taskCounter = 0;
    
    for (const line of lines) {
      if (line.match(/^-\s*\[[\sx]\]/)) {
        if (taskCounter === taskIndex) {
          // Update this task's checkbox based on status
          const checkbox = newStatus === 'completed' ? '[x]' : '[ ]';
          const taskText = line.replace(/^-\s*\[[\sx]\]\s*/, '');
          updatedLines.push(`- ${checkbox} ${taskText}`);
        } else {
          updatedLines.push(line);
        }
        taskCounter++;
      } else {
        updatedLines.push(line);
      }
    }
    
    // Write the updated content back
    const updatedContent = updatedLines.join('\n');
    await fs.writeFile(todoPath, updatedContent, 'utf8');
    
    console.log(`[TaskReader] Updated task ${taskIndex} in conversation ${conversationId} to ${newStatus}`);
    
    return {
      success: true,
      message: `Task ${taskIndex + 1} updated to ${newStatus}`,
      task: result.tasks[taskIndex],
      updatedTasks: result.tasks
    };
  } catch (error) {
    console.error('[TaskReader] Error updating task status:', error);
    return {
      success: false,
      error: error.message
    };
  }
}