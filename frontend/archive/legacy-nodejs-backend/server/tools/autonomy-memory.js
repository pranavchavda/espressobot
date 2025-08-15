import { tool } from '@openai/agents';
import { z } from 'zod';

// Simple in-memory store for conversation preferences
const conversationPreferences = new Map();

/**
 * Track user preferences for autonomy within a conversation
 */
export const trackAutonomyPreference = (conversationId, preference) => {
  if (!conversationPreferences.has(conversationId)) {
    conversationPreferences.set(conversationId, {
      confirmationCount: 0,
      executionCount: 0,
      preferredAutonomy: 'high',
      lastUpdate: new Date()
    });
  }
  
  const prefs = conversationPreferences.get(conversationId);
  
  if (preference === 'confirmed') {
    prefs.confirmationCount++;
  } else if (preference === 'executed') {
    prefs.executionCount++;
  }
  
  // Adjust preferred autonomy based on patterns
  if (prefs.executionCount > prefs.confirmationCount * 2) {
    prefs.preferredAutonomy = 'high';
  } else if (prefs.confirmationCount > prefs.executionCount) {
    prefs.preferredAutonomy = 'medium';
  }
  
  prefs.lastUpdate = new Date();
  
  return prefs;
};

/**
 * Get autonomy preference for a conversation
 */
export const getAutonomyPreference = (conversationId) => {
  if (!conversationPreferences.has(conversationId)) {
    return {
      preferredAutonomy: 'high',
      isNew: true
    };
  }
  
  const prefs = conversationPreferences.get(conversationId);
  return {
    ...prefs,
    isNew: false
  };
};

/**
 * Tool for tracking autonomy preferences
 */
export const autonomyTrackingTool = tool({
  name: 'track_autonomy_preference',
  description: 'Track user preferences for autonomous execution within the conversation',
  parameters: z.object({
    action: z.enum(['confirmed', 'executed', 'get']).describe('Action to track or get current preference'),
    conversationId: z.string().nullable().describe('Conversation ID (uses global if not provided)')
  }),
  execute: async ({ action, conversationId }) => {
    const convId = conversationId || global.currentConversationId;
    
    if (!convId) {
      return { error: 'No conversation ID available' };
    }
    
    if (action === 'get') {
      return getAutonomyPreference(convId);
    } else {
      return trackAutonomyPreference(convId, action);
    }
  }
});

/**
 * Analyze conversation history to determine autonomy preference
 */
export const analyzeConversationPattern = (messages) => {
  let confirmationRequests = 0;
  let directExecutions = 0;
  
  messages.forEach((msg, index) => {
    const content = msg.content?.toLowerCase() || '';
    
    // Check if assistant asked for confirmation
    if (msg.role === 'assistant') {
      if (content.includes('should i') || content.includes('would you like me to') || 
          content.includes('confirm') || content.includes('proceed?')) {
        confirmationRequests++;
      }
    }
    
    // Check if user gave direct commands
    if (msg.role === 'user' && index > 0) {
      const prevMsg = messages[index - 1];
      if (prevMsg.role === 'assistant' && 
          (prevMsg.content?.toLowerCase().includes('should i') || 
           prevMsg.content?.toLowerCase().includes('confirm'))) {
        // User responded to confirmation
        if (content.match(/^(yes|yeah|sure|ok|proceed|do it|go ahead)/i)) {
          directExecutions++;
        }
      }
    }
  });
  
  // Determine pattern
  if (directExecutions > confirmationRequests * 0.8) {
    return {
      pattern: 'prefers_execution',
      autonomyLevel: 'high',
      confidence: 0.9
    };
  } else if (confirmationRequests > directExecutions * 2) {
    return {
      pattern: 'prefers_confirmation',
      autonomyLevel: 'medium',
      confidence: 0.8
    };
  } else {
    return {
      pattern: 'balanced',
      autonomyLevel: 'high',
      confidence: 0.7
    };
  }
};