# Homepage Navigation Fix - Complete Solution

## Problem
When sending a message from the homepage (/), the app would:
1. Navigate to /chat and send the request
2. Get a conversation ID and navigate to /chat/{id}
3. Component would remount and lose all state
4. Async polling task would be lost
5. User sees empty chat page

## Solution
Pass the async task ID through navigation state so polling can continue after navigation.

## Changes Made

### 1. Navigation with Task State (lines 1207-1214)
```javascript
navigate(`/chat/${result.conversation_id}`, { 
  replace: true,
  state: {
    taskId: result.task_id,
    fromHomepage: true,
    userMessage: textToSend
  }
});
```

### 2. Task Continuation After Navigation (lines 2464-2483)
```javascript
// Handle task continuation after navigation
if (taskId && convId && fromHomepage) {
  console.log('[DEBUG] Continuing async task after navigation:', taskId);
  
  // Add the user message to the conversation
  if (userMessage) {
    setMessages([{
      role: "user",
      content: userMessage,
      timestamp: new Date().toISOString()
    }]);
  }
  
  // Continue polling the task
  pollAsyncTask(taskId, convId);
  
  // Clear the state to prevent re-processing
  window.history.replaceState({}, document.title, window.location.pathname);
  return;
}
```

### 3. Prevent Duplicate Polling (lines 900-905)
```javascript
// Prevent multiple polling for the same task
if (window.currentPollingTask === taskId) {
  console.log('[DEBUG] Already polling task:', taskId);
  return;
}
window.currentPollingTask = taskId;
```

## How It Works Now

1. User sends message from homepage (/)
2. Navigate to /chat with initial message
3. Send request to backend
4. Get conversation_id and task_id
5. Navigate to /chat/{id} WITH task_id in state
6. Component remounts at new URL
7. useEffect detects task_id in state and continues polling
8. User message is preserved and shown
9. Async response appears when ready

## Testing

1. Go to homepage http://localhost:5173/
2. Type a message and send
3. Should see:
   - Navigation to /chat briefly
   - Then navigation to /chat/{conversation_id}
   - User message appears in chat
   - "Processing with async agents..." message
   - Final response when ready

## Debug Messages to Watch

- `[DEBUG] New conversation created, navigating to:` - Confirms navigation with state
- `[DEBUG] Continuing async task after navigation:` - Confirms polling continues
- `[DEBUG] Already polling task:` - Prevents duplicate polling

## Key Improvements

1. **State Preservation**: User message and task ID survive navigation
2. **Continuous Polling**: Async task continues after component remount
3. **No Duplicate Polling**: Global flag prevents multiple polls
4. **Better UX**: User sees their message and processing status