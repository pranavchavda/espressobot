/**
 * OpenRouter Provider for OpenAI Agents SDK
 * Provides access to 300+ models through unified API
 * Uses the proven Direct Provider Pattern from Anthropic integration
 */

import OpenAI from 'openai';

/**
 * OpenRouter Model wrapper for OpenAI Agents SDK compatibility
 */
export class OpenRouterModel {
  constructor(config) {
    const {
      modelName,
      apiKey,
      baseURL = 'https://openrouter.ai/api/v1',
      appName = 'EspressoBot',
      siteUrl = 'https://idrinkcoffee.com'
    } = config;

    this.modelName = modelName;
    this.openai = new OpenAI({
      baseURL: baseURL,
      apiKey: apiKey,
      defaultHeaders: {
        'HTTP-Referer': siteUrl,
        'X-Title': appName
      }
    });

    if (process.env.DEBUG_OPENROUTER === 'true') {
      console.log('[OpenRouter] Created model:', modelName);
    }
  }

  async getResponse(request) {
    try {
      if (process.env.DEBUG_OPENROUTER === 'true') {
        console.log('[OpenRouter] Non-streaming request received');
      }

      // Convert OpenAI Agents SDK format to OpenRouter format
      // The SDK uses 'input' array and 'systemInstructions', not 'messages' and 'system'
      const inputMessages = request.input || request.messages || [];
      const systemMessage = request.systemInstructions || request.system || '';

      const messages = this.convertMessages(inputMessages, systemMessage);
      
      if (process.env.DEBUG_OPENROUTER === 'true') {
        console.log('[OpenRouter] Converted messages:', messages?.length || 0);
      }

      const response = await this.openai.chat.completions.create({
        model: this.modelName,
        messages: messages,
        max_tokens: request.max_tokens || 512,
        temperature: request.temperature || 0.7,
        stream: false
      });

      return this.formatResponse(response);

    } catch (error) {
      console.error('OpenRouter non-streaming error:', error);
      throw error;
    }
  }

  async *getStreamedResponse(request) {
    try {
      if (process.env.DEBUG_OPENROUTER === 'true') {
        console.log('[OpenRouter] Streaming request received with keys:', Object.keys(request || {}));
        console.log('[OpenRouter] Input messages:', request.input?.length || 0);
      }
      
      // Convert OpenAI Agents SDK format to OpenRouter format  
      // The SDK uses 'input' array and 'systemInstructions', not 'messages' and 'system'
      const inputMessages = request.input || request.messages || [];
      const systemMessage = request.systemInstructions || request.system || '';

      const messages = this.convertMessages(inputMessages, systemMessage);
      
      if (process.env.DEBUG_OPENROUTER === 'true') {
        console.log('[OpenRouter] Converted messages:', messages?.length || 0);
        if (messages?.length > 0) {
          console.log('[OpenRouter] First message:', messages[0]);
        }
      }

      // First yield response started event
      yield {
        type: 'response_started'
      };

      const stream = await this.openai.chat.completions.create({
        model: this.modelName,
        messages: messages,
        max_tokens: request.max_tokens || 512,
        temperature: request.temperature || 0.7,
        stream: true
      });

      let fullContent = '';
      let usage = {
        prompt_tokens: 0,
        completion_tokens: 0,
        total_tokens: 0
      };

      for await (const chunk of stream) {
        if (chunk.choices?.[0]?.delta?.content) {
          const deltaText = chunk.choices[0].delta.content;
          fullContent += deltaText;
          
          // Yield text delta event
          if (process.env.DEBUG_OPENROUTER === 'true') {
            console.log('[OpenRouter] Yielding delta:', deltaText.substring(0, 50));
          }
          yield {
            type: 'output_text_delta',
            delta: deltaText
          };
        }

        // Capture usage information if available
        if (chunk.usage) {
          usage = {
            prompt_tokens: chunk.usage.prompt_tokens || 0,
            completion_tokens: chunk.usage.completion_tokens || 0,
            total_tokens: chunk.usage.total_tokens || 0
          };
        }
      }

      // Final completion event
      if (process.env.DEBUG_OPENROUTER === 'true') {
        console.log('[OpenRouter] Yielding response_done with content length:', fullContent.length);
      }
      yield {
        type: 'response_done',
        response: {
          id: `openrouter_${Date.now()}`,
          output: [{
            type: 'message',
            role: 'assistant',
            status: 'completed',
            content: [{
              type: 'output_text',
              text: fullContent
            }]
          }],
          usage: {
            inputTokens: usage.prompt_tokens,
            outputTokens: usage.completion_tokens,
            totalTokens: usage.total_tokens
          }
        }
      };

    } catch (error) {
      console.error('OpenRouter streaming error:', error);
      // Don't yield error events - let the SDK handle errors
      throw error;
    }
  }

  convertMessages(messages, systemMessage = '') {
    const convertedMessages = [];

    // Add system message first if provided
    if (systemMessage && systemMessage.trim()) {
      convertedMessages.push({
        role: 'system',
        content: systemMessage.trim()
      });
    }

    // Convert input messages
    const userMessages = messages.map(msg => {
      // Handle OpenAI Agents SDK message format
      if (msg.type === 'message') {
        return {
          role: msg.role,
          content: msg.content || ''
        };
      }
      
      // Handle tool calls if needed (for future enhancement)
      if (msg.tool_calls || msg.function_call) {
        return {
          role: msg.role,
          content: msg.content || 'Function call: ' + JSON.stringify(msg.tool_calls || msg.function_call)
        };
      }

      // Handle standard OpenAI format
      return {
        role: msg.role,
        content: msg.content || ''
      };
    }).filter(msg => msg.content && msg.content.trim());

    convertedMessages.push(...userMessages);
    
    // Ensure we have at least one message
    if (convertedMessages.length === 0) {
      return [{
        role: 'user',
        content: 'Hello'
      }];
    }

    return convertedMessages;
  }

  formatResponse(response) {
    const content = response.choices?.[0]?.message?.content || '';
    const usage = response.usage || {};

    return {
      id: response.id || `openrouter_${Date.now()}`,
      output: [{
        type: 'message',
        role: 'assistant', 
        status: 'completed',
        content: [{
          type: 'output_text',
          text: content
        }]
      }],
      usage: {
        inputTokens: usage.prompt_tokens || 0,
        outputTokens: usage.completion_tokens || 0,
        totalTokens: usage.total_tokens || 0
      }
    };
  }
}

/**
 * OpenRouter Provider for OpenAI Agents SDK
 */
export class OpenRouterProvider {
  constructor(config = {}) {
    this.config = {
      apiKey: config.apiKey || process.env.OPENROUTER_API_KEY,
      baseURL: config.baseURL || 'https://openrouter.ai/api/v1',
      appName: config.appName || 'EspressoBot',
      siteUrl: config.siteUrl || 'https://idrinkcoffee.com',
      defaultModel: config.defaultModel || 'openai/gpt-4o',
      ...config
    };

    if (!this.config.apiKey) {
      throw new Error('OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable or pass apiKey in config.');
    }

    if (process.env.DEBUG_OPENROUTER === 'true') {
      console.log('[OpenRouter] Provider created with default model:', this.config.defaultModel);
    }
  }

  getModel(modelName) {
    const effectiveModelName = modelName || this.config.defaultModel;
    
    if (process.env.DEBUG_OPENROUTER === 'true') {
      console.log('[OpenRouter] Creating model:', effectiveModelName);
    }

    return new OpenRouterModel({
      modelName: effectiveModelName,
      apiKey: this.config.apiKey,
      baseURL: this.config.baseURL,
      appName: this.config.appName,
      siteUrl: this.config.siteUrl
    });
  }
}

/**
 * Predefined model configurations for different agent types
 */
export const AGENT_MODEL_MAP = {
  // Analytical and reasoning tasks
  'Pricing Agent': 'cohere/command-r-plus',
  'Inventory Agent': 'cohere/command-r-plus',
  'Sales Agent': 'anthropic/claude-3.5-sonnet',
  
  // Code and technical tasks
  'SWE Agent': 'anthropic/claude-3.5-sonnet',
  'Documentation Agent': 'anthropic/claude-3.5-sonnet',
  
  // Creative and content tasks
  'Product Management Agent': 'anthropic/claude-3.5-sonnet',
  'Features Agent': 'openai/gpt-4o',
  
  // Fast processing tasks (can be overridden with Groq later)
  'Utility Agent': 'openai/gpt-4o-mini',
  'Memory Operations': 'openai/gpt-4o-mini',
  
  // Default fallback
  'default': 'openai/gpt-4o'
};

/**
 * Create model provider based on environment variables
 * Integrates with existing orchestrator
 */
export function createModelProvider() {
  const modelProvider = process.env.MODEL_PROVIDER || 'openai';
  
  if (modelProvider === 'openrouter') {
    if (process.env.DEBUG_OPENROUTER === 'true') {
      console.log('[OpenRouter] Using OpenRouter model provider');
    }
    
    return new OpenRouterProvider({
      apiKey: process.env.OPENROUTER_API_KEY,
      defaultModel: process.env.OPENROUTER_MODEL || 'openai/gpt-4o'
    });
  }
  
  // Return null for other providers (handled by existing logic)
  return null;
}

export default OpenRouterProvider;