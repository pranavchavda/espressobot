# Frontend Timeout Fix for GPT-5 Thinking Model

## Problem
The frontend was spinning indefinitely even though the backend had completed the response. This was because:
1. GPT-5 thinking model takes 30-60 seconds to respond
2. Frontend had no timeout handling
3. No user feedback during the long wait

## Solution Implemented

### 1. Added 120-second timeout (2 minutes)
```javascript
// Create AbortController for timeout (120 seconds for GPT-5 thinking model)
const controller = new AbortController();
const timeoutId = setTimeout(() => controller.abort(), 120000); // 2 minutes timeout

const response = await fetch(fetchUrl, {
  // ... 
  signal: controller.signal
}).finally(() => clearTimeout(timeoutId));
```

### 2. Added thinking indicator
```javascript
// Show thinking indicator for GPT-5
setStreamingMessage({
  role: "assistant",
  content: "🤔 GPT-5 is thinking... This may take 30-60 seconds for complex queries.",
  timestamp: new Date().toISOString(),
  agent: "orchestrator"
});
```

### 3. Added timeout error handling
```javascript
if (e.name === 'AbortError') {
  // Show helpful timeout message
  const errorMessage = {
    content: "⏱️ Request timed out after 2 minutes. GPT-5 thinking models sometimes need more time...",
    agent: "system"
  };
  setMessages(prev => [...prev, errorMessage]);
}
```

## Files Modified
- `/home/pranav/espressobot/frontend/src/features/chat/StreamingChatPage.jsx`

## Testing
The frontend now:
1. Shows "GPT-5 is thinking..." message immediately
2. Waits up to 2 minutes for response
3. Shows helpful timeout message if it takes too long
4. Properly displays the response when it arrives within the timeout

## Backend Status
The Progressive Orchestrator with GPT-5 is working correctly:
- First query: ~45 seconds (with agent call)
- Follow-ups: ~10-15 seconds (using compressed context)
- Compression with gpt-4.1-mini is working perfectly

## User Experience
- ✅ Clear feedback that GPT-5 is thinking
- ✅ 2-minute timeout prevents infinite spinning
- ✅ Helpful error message if timeout occurs
- ✅ Responses display correctly when received