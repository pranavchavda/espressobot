/**
 * Model Retry Utility
 * Handles OpenAI model retries with fallback when models are unavailable
 */

import { Agent as OpenAIAgent, run as openAIRun } from '@openai/agents';

export const MODEL_FALLBACKS = {
  'gpt-4.1-mini': 'gpt-4o-mini',
  'gpt-4.1-nano': 'gpt-4o-mini',
  'o1-mini': 'gpt-4o-mini',
  'o1': 'gpt-4o'
};

/**
 * Create an agent with automatic retry on model failure
 * @param {Object} config - Agent configuration
 * @returns {Object} - Agent instance
 */
export function createAgentWithRetry(config) {
  const originalModel = config.model;
  
  // Create wrapper that handles model errors
  const agentWrapper = {
    _agent: new OpenAIAgent(config),
    _config: config,
    _originalModel: originalModel,
    
    // Proxy all properties to the underlying agent
    ...Object.fromEntries(
      Object.getOwnPropertyNames(OpenAIAgent.prototype)
        .filter(prop => prop !== 'constructor')
        .map(prop => [prop, function(...args) {
          return this._agent[prop](...args);
        }])
    )
  };
  
  // Return the original agent - retry will be handled in runWithRetry
  return new OpenAIAgent(config);
}

/**
 * Run an agent with automatic retry on model failure
 * @param {Object} agent - Agent instance
 * @param {string} task - Task to run
 * @param {Object} options - Run options
 * @returns {Promise} - Run result
 */
export async function runWithRetry(agent, task, options = {}) {
  try {
    // Try with the original model first
    return await openAIRun(agent, task, options);
  } catch (error) {
    // Check if it's a model not found error
    if (error.status === 404 && error.message && error.message.includes('Model not found')) {
      const originalModel = agent.model || 'unknown';
      const fallbackModel = MODEL_FALLBACKS[originalModel];
      
      if (fallbackModel) {
        console.log(`[Model Retry] Model ${originalModel} not found, retrying with ${fallbackModel}`);
        
        // Create new agent with fallback model
        const fallbackAgent = new OpenAIAgent({
          ...agent,
          model: fallbackModel,
          name: agent.name,
          instructions: agent.instructions,
          outputType: agent.outputType,
          tools: agent.tools
        });
        
        // Retry with fallback model
        return await openAIRun(fallbackAgent, task, options);
      }
    }
    
    // Re-throw if not a model error or no fallback available
    throw error;
  }
}

/**
 * Wrapper for Agent constructor that provides model retry capability
 */
export class Agent extends OpenAIAgent {
  constructor(config) {
    super(config);
    this._originalModel = config.model;
  }
}

/**
 * Wrapper for run function that provides model retry capability
 */
export async function run(agent, task, options) {
  return runWithRetry(agent, task, options);
}