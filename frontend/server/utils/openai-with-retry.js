/**
 * OpenAI API wrapper with model retry functionality
 */

import OpenAI from 'openai';

const MODEL_FALLBACKS = {
  'gpt-4.1-mini': 'gpt-4o-mini',
  'gpt-4.1-nano': 'gpt-4o-mini',
  'o1-mini': 'gpt-4o-mini',
  'o1': 'gpt-4o'
};

/**
 * Create OpenAI client with retry wrapper
 */
export function createOpenAIWithRetry() {
  const client = new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
  });
  
  // Store original create method
  const originalCreate = client.chat.completions.create.bind(client.chat.completions);
  
  // Override create method with retry logic
  client.chat.completions.create = async function(params) {
    try {
      // Try with original model first
      return await originalCreate(params);
    } catch (error) {
      // Check if it's a model not found error
      if (error.status === 404 && error.message && error.message.includes('Model not found')) {
        const originalModel = params.model;
        const fallbackModel = MODEL_FALLBACKS[originalModel];
        
        if (fallbackModel) {
          console.log(`[OpenAI Retry] Model ${originalModel} not found, retrying with ${fallbackModel}`);
          
          // Retry with fallback model
          return await originalCreate({
            ...params,
            model: fallbackModel
          });
        }
      }
      
      // Re-throw if not a model error or no fallback available
      throw error;
    }
  };
  
  return client;
}