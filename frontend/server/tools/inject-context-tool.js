/**
 * Inject Context Tool
 * 
 * Tool for orchestrator to check and inject queued messages during execution.
 */

import { tool } from '@openai/agents';
import { z } from 'zod';
import { messageInjector } from '../utils/agent-message-injector.js';

export function createInjectContextTool() {
  return tool({
    name: 'check_inject_context',
    description: 'Check for and inject any queued context updates from the user. Use this between major steps to allow dynamic context updates.',
    parameters: z.object({
      conversationId: z.string().describe('The conversation ID to check for updates'),
      currentStep: z.string().describe('Current step or phase of execution'),
      allowMultiple: z.boolean().default(false).describe('Whether to inject multiple messages at once')
    }),
    execute: async ({ conversationId, currentStep, allowMultiple }) => {
      try {
        // Register injection point
        messageInjector.registerInjectionPoint(conversationId, currentStep);
        
        // Check if we can inject
        if (!messageInjector.canInject(conversationId)) {
          return {
            hasUpdates: false,
            message: 'No injection possible at this time'
          };
        }
        
        // Get pending messages
        const pending = messageInjector.getPendingMessages(conversationId);
        if (pending.length === 0) {
          return {
            hasUpdates: false,
            message: 'No pending context updates'
          };
        }
        
        const injectedMessages = [];
        
        // Inject messages
        if (allowMultiple) {
          // Inject all pending messages
          for (const msg of pending) {
            const message = messageInjector.getNextMessage(conversationId);
            if (message) {
              injectedMessages.push({
                content: message.message,
                priority: message.priority,
                timestamp: message.timestamp
              });
              messageInjector.markInjected(message.id, conversationId);
            }
          }
        } else {
          // Inject only the next message
          const message = messageInjector.getNextMessage(conversationId);
          if (message) {
            injectedMessages.push({
              content: message.message,
              priority: message.priority,
              timestamp: message.timestamp
            });
            messageInjector.markInjected(message.id, conversationId);
          }
        }
        
        return {
          hasUpdates: true,
          injectedCount: injectedMessages.length,
          remainingCount: messageInjector.getPendingMessages(conversationId).length,
          messages: injectedMessages,
          currentStep: currentStep
        };
        
      } catch (error) {
        console.error('Error in inject context tool:', error);
        return {
          hasUpdates: false,
          error: error.message
        };
      }
    }
  });
}

export function createManageInjectionTool() {
  return tool({
    name: 'manage_injection_state',
    description: 'Manage the injection state for a conversation (start/stop agent execution tracking)',
    parameters: z.object({
      conversationId: z.string().describe('The conversation ID'),
      action: z.enum(['start', 'stop', 'status']).describe('Action to perform'),
    }),
    execute: async ({ conversationId, action }) => {
      try {
        switch (action) {
          case 'start':
            messageInjector.setAgentRunning(conversationId, true);
            return {
              success: true,
              message: 'Agent execution tracking started',
              state: messageInjector.getAgentState(conversationId)
            };
            
          case 'stop':
            messageInjector.setAgentRunning(conversationId, false);
            return {
              success: true,
              message: 'Agent execution tracking stopped',
              state: messageInjector.getAgentState(conversationId)
            };
            
          case 'status':
            const state = messageInjector.getAgentState(conversationId);
            const pending = messageInjector.getPendingMessages(conversationId);
            return {
              success: true,
              state: state,
              pendingMessages: pending.length,
              canInject: messageInjector.canInject(conversationId)
            };
            
          default:
            return {
              success: false,
              error: 'Invalid action'
            };
        }
      } catch (error) {
        console.error('Error in manage injection tool:', error);
        return {
          success: false,
          error: error.message
        };
      }
    }
  });
}