# User Profile Injection Implementation

## Overview
This document describes the implementation of user profile data injection into system prompts and orchestrator configurations for EspressoBot.

## Changes Made

### 1. System Prompt Updates

#### File: `/server/prompts/orchestrator-system-prompt.js`
- Modified `buildOrchestratorSystemPrompt()` to accept an optional `userProfile` parameter
- Added user profile section to the prompt that includes:
  - User name, email, bio
  - Account creation date
  - Admin status
  - Special instructions for VIP users (e.g., Pranav)

```javascript
export function buildOrchestratorSystemPrompt(userProfile = null) {
  // ... existing code ...
  
  // Build user-specific context
  let userContext = '';
  if (userProfile) {
    userContext = `\n## User Profile
Name: ${userProfile.name || 'Unknown'}
Email: ${userProfile.email || 'Unknown'}
Bio: ${userProfile.bio || 'No bio provided'}
Account Created: ${userProfile.created_at ? new Date(userProfile.created_at).toLocaleDateString() : 'Unknown'}
Admin: ${userProfile.is_admin ? 'Yes' : 'No'}`;
    
    // Add special instructions based on user
    if (userProfile.name === 'Pranav' || userProfile.email?.includes('pranav')) {
      userContext += '\n\n**Special Instructions**: This is Pranav - the developer of EspressoBot and digital operations manager. Treat as VIP with full system access and highest priority support.';
    } else if (userProfile.is_admin) {
      userContext += '\n\n**Special Instructions**: Admin user - provide detailed technical information and full access to all features.';
    }
  }
  
  // ... rest of prompt ...
}
```

### 2. Tiered Prompt Updates

#### File: `/server/prompts/tiered-orchestrator-prompt.js`
- Updated `buildTieredOrchestratorPrompt()` to accept `userProfile` parameter
- Passes user profile to `buildOrchestratorSystemPrompt()`
- Removed hardcoded reference to Pranav in extended prompt

### 3. Context Builder Updates

#### File: `/server/context/tiered-context-builder.js`
- Modified both `buildCoreContext()` and `buildFullContext()` to accept `userProfile` parameter
- User profile is now included in the context object passed to agents

### 4. Dynamic Orchestrator Updates

#### File: `/server/dynamic-bash-orchestrator.js`
- Added user profile fetching in `runDynamicOrchestrator()`:
  ```javascript
  // Fetch user profile if userId is provided
  let userProfile = null;
  if (userId) {
    try {
      const { PrismaClient } = await import('@prisma/client');
      const prisma = new PrismaClient();
      userProfile = await prisma.users.findUnique({
        where: { id: userId },
        select: {
          id: true,
          email: true,
          name: true,
          bio: true,
          is_admin: true,
          created_at: true
        }
      });
      await prisma.$disconnect();
      
      if (userProfile) {
        console.log(`[Orchestrator] Loaded profile for user: ${userProfile.name || userProfile.email}`);
        // Store globally for access by spawned agents
        global.currentUserProfile = userProfile;
      }
    } catch (error) {
      console.log(`[Orchestrator] Could not load user profile:`, error.message);
    }
  }
  ```
- Updated `buildAgentContext()` to accept and pass `userProfile`
- Modified `createOrchestratorAgent()` to accept and use `userProfile`
- Updated all spawn functions to include user profile in agent context
- Added cleanup of `global.currentUserProfile` in finally block

### 5. Bash Tool Updates

#### File: `/server/tools/bash-tool.js`
- Modified `buildPromptFromRichContext()` to include user profile section:
  ```javascript
  // Add user profile context if available
  if (context.userProfile) {
    prompt += `\n\n## Current User Profile:
- Name: ${context.userProfile.name || 'Unknown'}
- Email: ${context.userProfile.email || 'Unknown'}
- Admin: ${context.userProfile.is_admin ? 'Yes' : 'No'}`;
    
    if (context.userProfile.name === 'Pranav' || context.userProfile.email?.includes('pranav')) {
      prompt += '\n- **VIP Status**: Developer & Digital Operations Manager - full system access';
    }
  }
  ```

### 6. Agent Context Updates
All spawned agents (bash agents, SWE agent, parallel executors) now receive user profile in their context:
- Regular bash agents via `spawn_bash_agent`
- Parallel bash agents via `spawn_parallel_bash_agents`
- SWE agent via `spawn_swe_agent`
- Parallel executors via `spawn_parallel_executors`

## User Profile Structure

The user profile object contains:
```typescript
interface UserProfile {
  id: number;
  email: string;
  name: string | null;
  bio: string | null;
  is_admin: boolean;
  created_at: Date;
}
```

## Special User Handling

### VIP Users (Pranav)
- Identified by name "Pranav" or email containing "pranav"
- Receives special instructions in prompts
- Full system access
- Highest priority support

### Admin Users
- Identified by `is_admin: true`
- Receives detailed technical information
- Full access to all features

### Regular Users
- Standard access and support
- No special instructions

## Testing

A test script has been created at `/tests/test-user-profile-injection.js` that verifies:
1. Orchestrator prompt without user profile
2. Orchestrator prompt with regular user
3. Orchestrator prompt with VIP user (Pranav)
4. Tiered prompt with user profile
5. Bash agent prompt with user profile
6. Admin user handling

## Future Enhancements

1. **User Preferences**: Store and use user-specific preferences (e.g., autonomy level, preferred tools)
2. **Role-Based Access**: Implement fine-grained permissions based on user roles
3. **User History**: Track user interaction patterns for better personalization
4. **Team Management**: Support for team hierarchies and permissions
5. **Custom Instructions**: Allow users to set their own custom instructions

## Usage

The user profile is automatically loaded when:
1. A request comes through the API with authentication
2. The `userId` is provided to `runDynamicOrchestrator()`
3. The profile is fetched from the database and injected into all prompts

No additional configuration is needed - the system automatically personalizes responses based on the authenticated user.