# Navigation Fix Test Plan

## Issue Fixed
When starting a new chat from the homepage (/), the app would stay at /chat with no conversation ID, causing a blank/spinning page after the request is sent.

## Solution Implemented
Added navigation to the conversation URL immediately after receiving the conversation_id from the backend in both:
1. Async endpoint response handling (line 1201-1209)
2. SSE conversation_id event handling (line 1568-1577)

## Test Steps

### Test 1: Async Endpoint (Default)
1. Open http://localhost:5173/ in browser
2. Type a message like "Hello, test conversation"
3. Click Send or press Enter
4. **Expected**: Should navigate from / → /chat → /chat/{conversation_id} automatically
5. **Verify**: URL should change to /chat/{id} and conversation should load properly

### Test 2: SSE Endpoint (If enabled)
1. Add `?orchestrator=1` to URL or set localStorage.setItem('orchestrator', '1')
2. Go to homepage http://localhost:5173/
3. Send a message
4. **Expected**: Same navigation behavior as Test 1

### Test 3: Quick Prompts
1. Go to homepage http://localhost:5173/
2. Click one of the quick prompt buttons
3. **Expected**: Should navigate properly to /chat/{id}

### Test 4: With Attachments
1. Go to homepage
2. Add an image or file attachment
3. Send with message
4. **Expected**: Should navigate properly with attachment preserved

## Debug Console Messages
Watch browser console for these messages:
- `[DEBUG] Async response received:` - Shows when async endpoint responds
- `[DEBUG] New conversation created, navigating to:` - Shows navigation happening
- `[DEBUG] Received conversation_id event:` - For SSE mode
- `[DEBUG] Navigating to new conversation:` - Confirms navigation

## Success Criteria
✅ No more blank/spinning page at /chat
✅ URL changes to /chat/{conversation_id} immediately
✅ Conversation loads and displays properly
✅ Sidebar updates with new conversation
✅ Can continue chatting normally

## Changes Made
- **File**: `/home/pranav/espressobot/frontend/src/features/chat/StreamingChatPage.jsx`
- **Lines Modified**: 
  - 1201-1209: Added navigation after async response
  - 1568-1577: Added navigation after SSE conversation_id event
  - 906-907: Removed duplicate navigation from pollAsyncTask