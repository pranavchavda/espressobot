// This file now just re-exports tools from the merged task-planning-agent.js
// Kept for backward compatibility with existing imports

// Import everything first
import { 
  generateTodosTool, 
  getTodosTool, 
  updateTaskStatusTool,
  taskPlanningAgent
} from './agents/task-planning-agent.js';

// Re-export with proper names
export { 
  generateTodosTool, 
  getTodosTool, 
  updateTaskStatusTool,
  taskPlanningAgent as taskGeneratorAgent
};

// Legacy exports for compatibility
export { generateTodosTool as writePlanMdTool };
export { getTodosTool as readPlanMdTool };

console.log('[TaskGen] Re-exporting from merged task-planning-agent.js for backward compatibility');