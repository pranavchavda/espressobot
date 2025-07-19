/**
 * Agent Message Injector
 * 
 * Manages a queue system for injecting messages into running agents.
 * Allows dynamic context updates without restarting agent execution.
 */

import EventEmitter from 'events';

class AgentMessageInjector extends EventEmitter {
  constructor() {
    super();
    // Map of conversation ID to message queues
    this.messageQueues = new Map();
    // Map of conversation ID to agent state
    this.agentStates = new Map();
    // Injection points tracking
    this.injectionPoints = new Map();
  }

  /**
   * Initialize a queue for a conversation
   */
  initializeQueue(conversationId) {
    if (!this.messageQueues.has(conversationId)) {
      this.messageQueues.set(conversationId, []);
      this.agentStates.set(conversationId, {
        isRunning: false,
        lastInjectionTime: null,
        currentStep: null
      });
    }
  }

  /**
   * Queue a message for injection
   */
  queueMessage(conversationId, message, priority = 'normal') {
    this.initializeQueue(conversationId);
    
    const queueItem = {
      id: `inject-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      conversationId,
      message,
      priority,
      timestamp: new Date().toISOString(),
      status: 'pending'
    };

    const queue = this.messageQueues.get(conversationId);
    
    // Insert based on priority
    if (priority === 'high') {
      queue.unshift(queueItem);
    } else {
      queue.push(queueItem);
    }

    this.emit('messageQueued', queueItem);
    return queueItem.id;
  }

  /**
   * Get pending messages for a conversation
   */
  getPendingMessages(conversationId) {
    const queue = this.messageQueues.get(conversationId) || [];
    return queue.filter(item => item.status === 'pending');
  }

  /**
   * Mark agent as running/stopped
   */
  setAgentRunning(conversationId, isRunning) {
    this.initializeQueue(conversationId);
    const state = this.agentStates.get(conversationId);
    state.isRunning = isRunning;
    
    if (!isRunning) {
      // Clear queue when agent stops
      this.clearQueue(conversationId);
    }
  }

  /**
   * Register an injection point (safe checkpoint)
   */
  registerInjectionPoint(conversationId, stepName) {
    const state = this.agentStates.get(conversationId);
    if (state) {
      state.currentStep = stepName;
      state.lastInjectionTime = new Date().toISOString();
    }
    
    // Check if we have pending messages
    const pending = this.getPendingMessages(conversationId);
    if (pending.length > 0) {
      this.emit('injectionReady', {
        conversationId,
        stepName,
        pendingCount: pending.length
      });
    }
  }

  /**
   * Get next message to inject
   */
  getNextMessage(conversationId) {
    const queue = this.messageQueues.get(conversationId) || [];
    const pending = queue.find(item => item.status === 'pending');
    
    if (pending) {
      pending.status = 'injecting';
      return pending;
    }
    
    return null;
  }

  /**
   * Mark message as injected
   */
  markInjected(messageId, conversationId) {
    const queue = this.messageQueues.get(conversationId) || [];
    const item = queue.find(msg => msg.id === messageId);
    
    if (item) {
      item.status = 'injected';
      item.injectedAt = new Date().toISOString();
      this.emit('messageInjected', item);
    }
  }

  /**
   * Clear queue for a conversation
   */
  clearQueue(conversationId) {
    this.messageQueues.delete(conversationId);
    this.agentStates.delete(conversationId);
  }

  /**
   * Get agent state
   */
  getAgentState(conversationId) {
    return this.agentStates.get(conversationId) || {
      isRunning: false,
      lastInjectionTime: null,
      currentStep: null
    };
  }

  /**
   * Check if injection is safe
   */
  canInject(conversationId) {
    const state = this.getAgentState(conversationId);
    return state.isRunning && state.currentStep !== null;
  }
}

// Export singleton instance
export const messageInjector = new AgentMessageInjector();