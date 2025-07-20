# Google Workspace Single Sign-In Implementation

This document outlines how to modify EspressoBot to use a single Google sign-in for both authentication and Google Workspace API access.

## Current State
- Users sign in with Google OAuth
- Only basic profile/email scopes are requested
- Tokens are not persisted to database
- Google Workspace MCP requires separate authentication

## Proposed Solution

### 1. Database Schema Update
Add fields to store Google OAuth tokens:

```sql
-- Add to users table
ALTER TABLE users ADD COLUMN google_access_token TEXT;
ALTER TABLE users ADD COLUMN google_refresh_token TEXT;
ALTER TABLE users ADD COLUMN google_token_expiry DATETIME;
```

### 2. Extend OAuth Scopes
Update the Google authentication to request Workspace API scopes:

```javascript
// In server/auth.js
passport.authenticate('google', { 
  scope: [
    'profile', 
    'email',
    // Gmail
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    // Calendar
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    // Drive
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    // Tasks
    'https://www.googleapis.com/auth/tasks'
  ],
  accessType: 'offline',
  prompt: 'consent',
  state: state
})
```

### 3. Store Tokens in Database
Update the auth callback to persist tokens:

```javascript
// In server/config/auth.js
user = await prisma.users.update({
  where: { id: user.id },
  data: {
    google_access_token: accessToken,
    google_refresh_token: refreshToken,
    google_token_expiry: new Date(Date.now() + 3600 * 1000), // 1 hour
    profile_picture: profile.photos[0]?.value,
  },
});
```

### 4. Create Token Provider Service
Create a service to provide tokens to the Google Workspace MCP:

```javascript
// server/services/google-token-provider.js
export async function getGoogleTokensForUser(userId) {
  const user = await prisma.users.findUnique({
    where: { id: userId },
    select: {
      google_access_token: true,
      google_refresh_token: true,
      google_token_expiry: true
    }
  });
  
  // Check if token needs refresh
  if (new Date() > new Date(user.google_token_expiry)) {
    // Refresh token logic
    const newTokens = await refreshGoogleToken(user.google_refresh_token);
    await updateUserTokens(userId, newTokens);
    return newTokens;
  }
  
  return {
    access_token: user.google_access_token,
    refresh_token: user.google_refresh_token
  };
}
```

### 5. Modify Google Workspace Agent
Update the agent to use stored tokens instead of requiring separate auth:

```javascript
// In google-workspace-agent.js
export async function executeGoogleWorkspaceTask(task, conversationId, richContext = {}) {
  // Get user tokens
  const userId = global.currentUserId;
  const tokens = await getGoogleTokensForUser(userId);
  
  // Pass tokens to MCP server
  const mcpServer = new MCPServer({
    command: 'uvx',
    args: ['workspace-mcp'],
    env: {
      GOOGLE_OAUTH_ACCESS_TOKEN: tokens.access_token,
      GOOGLE_OAUTH_REFRESH_TOKEN: tokens.refresh_token,
      // OR use a custom auth mode that accepts pre-authorized tokens
    }
  });
  
  // Continue with agent execution...
}
```

## Alternative Approach: Custom Google Workspace Tools

Instead of using the MCP server, we could create direct tool implementations:

```javascript
// server/tools/google-workspace-direct.js
import { google } from 'googleapis';

export function createGmailTool(accessToken) {
  const auth = new google.auth.OAuth2();
  auth.setCredentials({ access_token: accessToken });
  
  const gmail = google.gmail({ version: 'v1', auth });
  
  return tool({
    name: 'gmail_send',
    description: 'Send an email via Gmail',
    parameters: z.object({
      to: z.string(),
      subject: z.string(),
      body: z.string()
    }),
    execute: async ({ to, subject, body }) => {
      const message = createMessage(to, subject, body);
      const result = await gmail.users.messages.send({
        userId: 'me',
        requestBody: { raw: message }
      });
      return result.data;
    }
  });
}
```

## Benefits
1. Single sign-in experience for users
2. No duplicate authentication prompts
3. Seamless Google Workspace integration
4. Better security (tokens stored encrypted)
5. Automatic token refresh

## Implementation Steps
1. Update database schema
2. Modify OAuth scope request
3. Update auth callback to store tokens
4. Create token provider service
5. Either:
   - Modify MCP integration to use stored tokens, OR
   - Create direct Google API tools

## Considerations
- Users will need to re-authenticate to grant additional scopes
- Consider gradual scope requests (only request what's needed)
- Implement proper token encryption before storing
- Add token refresh logic for expired tokens