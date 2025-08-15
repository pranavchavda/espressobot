# Task Update Fixes - June 30, 2025

## Issues Fixed

### 1. Task Updates Not Emitting SSE Events
**Problem**: When tasks were updated (e.g., from pending to in_progress), the backend logs showed the update but no SSE events were sent to the frontend.

**Solution**: 
- Added SSE event emission in the task update tool (`bash-tool.js`)
- Made the SSE emitter globally accessible via `global.currentSseEmitter`
- After each task update, the tool now:
  1. Fetches the updated task list
  2. Sends a `task_summary` event with all tasks
  3. Sends a `task_plan_created` event with the markdown content

### 2. Memory Metadata Too Large
**Problem**: Memory storage was failing with "metadata exceeds 2000 character limit" error when storing large conversations.

**Solution**:
- Added truncation logic in `bash-orchestrator-api.js`
- User messages and assistant responses are now limited to 500 characters each in metadata
- The full conversation is still stored in the memory content, only metadata is truncated

### 3. Frontend Ignoring Task Updates
**Problem**: The frontend was receiving `task_summary` events but ignoring them with "no new tasks" message.

**Solution**:
- Updated the `task_summary` event handler in `StreamingChatPage.jsx`
- Changed from only adding new tasks to properly updating existing task statuses
- Both basic agent and multi-agent modes now handle task status updates correctly

## Code Changes

### 1. `/server/bash-orchestrator-api.js`
```javascript
// Added global SSE emitter
global.currentSseEmitter = sendEvent;
global.currentConversationId = conversationId;

// Added metadata truncation
const truncatedMessage = message.length > 500 ? message.substring(0, 500) + '...' : message;
const truncatedResponse = textResponse.length > 500 ? textResponse.substring(0, 500) + '...' : textResponse;
```

### 2. `/server/tools/bash-tool.js`
```javascript
// Added SSE event emission after task update
const sseEmitter = global.currentSseEmitter;
if (sseEmitter) {
  // Get updated task list
  const tasks = JSON.parse(tasksResult);
  
  // Send task_summary event
  sseEmitter('task_summary', {
    tasks: tasks.map((task, index) => ({
      id: `task_${conversationId}_${index}`,
      content: task.title || task,
      status: task.status || 'pending',
      conversation_id: conversationId
    })),
    conversation_id: conversationId
  });
}
```

### 3. `/src/features/chat/StreamingChatPage.jsx`
```javascript
// Updated task_summary handler to properly update task statuses
setCurrentTasks(prevTasks => {
  const existingTasksMap = new Map(prevTasks.map(t => [t.id, t]));
  
  const updatedTasks = actualEventPayload.tasks.map(newTask => {
    const existingTask = existingTasksMap.get(newTask.id);
    if (existingTask && existingTask.status !== newTask.status) {
      console.log(`Updating task ${newTask.id} status from ${existingTask.status} to ${newTask.status}`);
      return { ...existingTask, ...newTask };
    }
    return existingTask || newTask;
  });
  
  return updatedTasks;
});
```

## Testing

Created `/test-task-updates.js` to verify the fixes:
```bash
node test-task-updates.js
```

This script:
1. Sends a multi-step request that triggers task planning
2. Monitors SSE events for task updates
3. Logs all task-related events to verify they're being sent

## Expected Behavior

1. When a bash agent updates a task status, the frontend should immediately reflect the change
2. Memory storage should succeed even with large conversations
3. Task progress should update in real-time as agents work through the task list