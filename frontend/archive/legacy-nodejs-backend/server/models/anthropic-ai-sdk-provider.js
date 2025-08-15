/**
 * AI SDK-based Anthropic Provider for OpenAI Agents
 * Uses the AI SDK integration approach which should handle streaming better
 */

import { createAnthropic } from '@ai-sdk/anthropic';
import { aisdk, AiSdkModel } from '@openai/agents-extensions';

/**
 * Create an AI SDK-based Anthropic model provider
 */
export function createAnthropicAISDKProvider(config = {}) {
  const {
    modelName = 'claude-sonnet-4-20250514',
    apiKey = process.env.ANTHROPIC_API_KEY,
    ...modelConfig
  } = config;

  if (!apiKey) {
    throw new Error('Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or pass apiKey in config.');
  }

  if (process.env.DEBUG_ANTHROPIC === 'true') {
    console.log('[AI SDK Anthropic] Creating provider with model:', modelName);
  }

  // Create the Anthropic AI SDK provider
  const anthropic = createAnthropic({
    apiKey: apiKey,
  });

  // Get the specific model
  const anthropicModel = anthropic(modelName, {
    // Add any model-specific configuration
    ...modelConfig
  });

  // Try using AiSdkModel class directly
  const agentsModel = new AiSdkModel({
    model: anthropicModel,
    name: modelName
  });

  if (process.env.DEBUG_ANTHROPIC === 'true') {
    console.log('[AI SDK Anthropic] Successfully created agents model with AiSdkModel');
    console.log('[AI SDK Anthropic] Model type:', typeof agentsModel);
    console.log('[AI SDK Anthropic] Model constructor:', agentsModel.constructor.name);
  }

  return {
    getModel: (modelNameOverride) => {
      if (modelNameOverride && modelNameOverride !== modelName) {
        if (process.env.DEBUG_ANTHROPIC === 'true') {
          console.log('[AI SDK Anthropic] Creating model with override:', modelNameOverride);
        }
        const overrideModel = anthropic(modelNameOverride, modelConfig);
        return new AiSdkModel({ model: overrideModel, name: modelNameOverride });
      }
      return agentsModel;
    },
    
    // For compatibility with existing code
    model: agentsModel,
    modelName: modelName
  };
}

// Export a default provider instance factory
export function createModelProvider() {
  const modelProvider = process.env.MODEL_PROVIDER || 'openai';
  
  if (modelProvider === 'anthropic') {
    if (process.env.DEBUG_ANTHROPIC === 'true') {
      console.log('[AI SDK] Using Anthropic model provider via AI SDK');
    }
    return createAnthropicAISDKProvider({
      modelName: process.env.ANTHROPIC_MODEL || 'claude-sonnet-4-20250514',
      apiKey: process.env.ANTHROPIC_API_KEY
    });
  }
  
  // Return null for OpenAI (default behavior)
  return null;
}

export default createAnthropicAISDKProvider;