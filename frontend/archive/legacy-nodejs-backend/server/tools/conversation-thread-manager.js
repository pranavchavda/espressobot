import { tool } from '@openai/agents';
import { z } from 'zod';

/**
 * Conversation Thread Manager
 * 
 * Manages conversation context and threading across agent interactions,
 * implementing the OpenAI Agents JS pattern for maintaining conversation state.
 */

// In-memory storage for conversation threads (could be replaced with persistent storage)
const conversationThreads = new Map();

/**
 * Get or create a conversation thread
 */
export function getConversationThread(conversationId) {
  if (!conversationThreads.has(conversationId)) {
    conversationThreads.set(conversationId, {
      id: conversationId,
      messages: [],
      metadata: {
        createdAt: new Date().toISOString(),
        lastActivity: new Date().toISOString(),
        confirmationPatterns: {
          confirmedOperations: [],
          rejectedOperations: [],
          autonomyPreference: null
        }
      }
    });
  }
  return conversationThreads.get(conversationId);
}

/**
 * Add a message to the conversation thread
 */
export function addToThread(conversationId, role, content, metadata = {}) {
  const thread = getConversationThread(conversationId);
  
  const message = {
    role,
    content,
    timestamp: new Date().toISOString(),
    ...metadata
  };
  
  thread.messages.push(message);
  thread.metadata.lastActivity = message.timestamp;
  
  // Analyze patterns if it's a user message
  if (role === 'user') {
    analyzeUserPatterns(thread, content);
  }
  
  return thread;
}

/**
 * Analyze user patterns to determine autonomy preferences
 */
function analyzeUserPatterns(thread, userMessage) {
  const lowerMessage = userMessage.toLowerCase();
  const metadata = thread.metadata.confirmationPatterns;
  
  // Check for confirmation responses
  if (/^(yes|ok|go ahead|do it|proceed|sure|yeah|yep|correct|exactly|please do)/.test(lowerMessage)) {
    // User confirmed an operation
    const lastAssistantMessage = findLastAssistantMessage(thread);
    if (lastAssistantMessage && lastAssistantMessage.pendingOperation) {
      metadata.confirmedOperations.push({
        operation: lastAssistantMessage.pendingOperation,
        timestamp: new Date().toISOString()
      });
    }
  }
  
  // Check for rejection patterns
  if (/^(no|stop|wait|cancel|don't|hold on|abort)/.test(lowerMessage)) {
    const lastAssistantMessage = findLastAssistantMessage(thread);
    if (lastAssistantMessage && lastAssistantMessage.pendingOperation) {
      metadata.rejectedOperations.push({
        operation: lastAssistantMessage.pendingOperation,
        timestamp: new Date().toISOString()
      });
    }
  }
  
  // Check for explicit autonomy preferences
  if (/just do it|don't ask|stop asking|without confirmation/.test(lowerMessage)) {
    metadata.autonomyPreference = 'high';
  } else if (/always ask|confirm everything|be careful/.test(lowerMessage)) {
    metadata.autonomyPreference = 'low';
  }
  
  // Update thread autonomy recommendation based on patterns
  updateAutonomyRecommendation(thread);
}

/**
 * Find the last assistant message in the thread
 */
function findLastAssistantMessage(thread) {
  for (let i = thread.messages.length - 1; i >= 0; i--) {
    if (thread.messages[i].role === 'assistant') {
      return thread.messages[i];
    }
  }
  return null;
}

/**
 * Update autonomy recommendation based on user patterns
 */
function updateAutonomyRecommendation(thread) {
  const patterns = thread.metadata.confirmationPatterns;
  
  // If user has explicit preference, use it
  if (patterns.autonomyPreference) {
    thread.metadata.recommendedAutonomy = patterns.autonomyPreference;
    return;
  }
  
  // Calculate based on confirmation/rejection ratio
  const totalOperations = patterns.confirmedOperations.length + patterns.rejectedOperations.length;
  
  if (totalOperations >= 3) {
    const confirmationRate = patterns.confirmedOperations.length / totalOperations;
    
    if (confirmationRate >= 0.9) {
      // User almost always confirms - increase autonomy
      thread.metadata.recommendedAutonomy = 'high';
    } else if (confirmationRate >= 0.7) {
      // User usually confirms - medium autonomy
      thread.metadata.recommendedAutonomy = 'medium';
    } else {
      // User often rejects - low autonomy
      thread.metadata.recommendedAutonomy = 'low';
    }
  }
}

/**
 * Get autonomy recommendation for a conversation
 */
export function getAutonomyRecommendation(conversationId) {
  const thread = getConversationThread(conversationId);
  return thread.metadata.recommendedAutonomy || null;
}

/**
 * Get recent context from conversation
 */
export function getRecentContext(conversationId, maxMessages = 10) {
  const thread = getConversationThread(conversationId);
  const recentMessages = thread.messages.slice(-maxMessages);
  
  return {
    messages: recentMessages,
    autonomyRecommendation: thread.metadata.recommendedAutonomy,
    confirmationPatterns: thread.metadata.confirmationPatterns
  };
}

/**
 * Format thread for agent context
 */
export function formatThreadForAgent(conversationId, maxMessages = 10) {
  const context = getRecentContext(conversationId, maxMessages);
  
  let formatted = "Recent conversation history:\n";
  context.messages.forEach(msg => {
    formatted += `${msg.role}: ${msg.content}\n`;
  });
  
  if (context.autonomyRecommendation) {
    formatted += `\nUser preference: ${context.autonomyRecommendation} autonomy based on past interactions\n`;
  }
  
  return formatted;
}

/**
 * Tool for agents to access conversation context
 */
export const conversationContextTool = tool({
  name: 'get_conversation_context',
  description: 'Get recent conversation history and user preferences',
  parameters: z.object({
    conversationId: z.string().describe('The conversation ID'),
    maxMessages: z.number().optional().default(10).describe('Maximum number of recent messages to retrieve')
  }),
  execute: async ({ conversationId, maxMessages }) => {
    const context = getRecentContext(conversationId, maxMessages);
    return {
      recentMessages: context.messages,
      userPreferences: {
        autonomy: context.autonomyRecommendation || 'default',
        confirmationHistory: {
          confirmed: context.confirmationPatterns.confirmedOperations.length,
          rejected: context.confirmationPatterns.rejectedOperations.length
        }
      }
    };
  }
});

/**
 * Clear old conversations (housekeeping)
 */
export function clearOldConversations(maxAgeHours = 24) {
  const cutoffTime = new Date(Date.now() - maxAgeHours * 60 * 60 * 1000);
  
  for (const [id, thread] of conversationThreads.entries()) {
    const lastActivity = new Date(thread.metadata.lastActivity);
    if (lastActivity < cutoffTime) {
      conversationThreads.delete(id);
    }
  }
}

// Set up periodic cleanup
setInterval(() => {
  clearOldConversations(48); // Clear conversations older than 48 hours
}, 60 * 60 * 1000); // Run every hour

console.log('[ConversationThreadManager] Initialized with thread management and autonomy tracking');