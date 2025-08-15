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
  /**
   * Parse model's text output for tool calls
   * Supports multiple formats:
   * 1. Official Anthropic format: <function_calls><invoke>...</invoke></function_calls>
   * 2. Simple format: <invoke name="tool_name">{"param": "value"}</invoke>
   * 3. OpenAI format: Function call: {"name": "tool", "arguments": {...}}
   */
  parseToolCalls(text) {
    const toolCalls = [];
    let remainingText = text;
    
    // First try to parse the official Anthropic format
    const officialFormatRegex = /<function_calls>(.*?)<\/function_calls>/gs;
    const officialMatch = officialFormatRegex.exec(text);
    
    if (officialMatch) {
      const functionCallsContent = officialMatch[1];
      const invokeRegex = /<invoke>(.*?)<\/invoke>/gs;
      let invokeMatch;
      
      while ((invokeMatch = invokeRegex.exec(functionCallsContent)) !== null) {
        const invokeContent = invokeMatch[1];
        
        // Extract tool name
        const toolNameMatch = /<tool_name>(.*?)<\/tool_name>/s.exec(invokeContent);
        if (!toolNameMatch) continue;
        const toolName = toolNameMatch[1].trim();
        
        // Extract parameters
        const parametersMatch = /<parameters>(.*?)<\/parameters>/s.exec(invokeContent);
        const args = {};
        
        if (parametersMatch) {
          const paramsContent = parametersMatch[1];
          // Extract each parameter
          const paramRegex = /<(\w+)>(.*?)<\/\1>/gs;
          let paramMatch;
          while ((paramMatch = paramRegex.exec(paramsContent)) !== null) {
            const [, paramName, paramValue] = paramMatch;
            // Try to parse as JSON, otherwise keep as string
            try {
              args[paramName] = JSON.parse(paramValue);
            } catch {
              args[paramName] = paramValue.trim();
            }
          }
        }
        
        toolCalls.push({
          type: 'function_call',
          callId: `call_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          name: toolName,
          arguments: JSON.stringify(args),
          status: 'completed'
        });
      }
      
      // Remove the function calls from the text
      remainingText = remainingText.replace(officialMatch[0], '');
    }
    
    // Check for the simpler format
    const simpleFormatRegex = /<invoke\s+name="([^"]+)">(.*?)<\/invoke>/gs;
    let simpleMatch;
    
    while ((simpleMatch = simpleFormatRegex.exec(remainingText)) !== null) {
      const [fullMatch, toolName, argsString] = simpleMatch;
      
      try {
        // Parse the arguments
        const args = argsString.trim() ? JSON.parse(argsString) : {};
        
        toolCalls.push({
          type: 'function_call',
          callId: `call_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          name: toolName,
          arguments: JSON.stringify(args),
          status: 'completed'
        });
        
        // Remove the tool call from the text
        remainingText = remainingText.replace(fullMatch, '');
      } catch (e) {
        console.error(`Failed to parse tool call for ${toolName}:`, e);
      }
    }
    
    // Check for OpenAI-style function calls (some models might use this)
    const openAIFormatRegex = /Function call:\s*({[^}]+})/g;
    let openAIMatch;
    
    while ((openAIMatch = openAIFormatRegex.exec(remainingText)) !== null) {
      try {
        const callData = JSON.parse(openAIMatch[1]);
        if (callData.name) {
          toolCalls.push({
            type: 'function_call',
            callId: `call_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            name: callData.name,
            arguments: JSON.stringify(callData.arguments || {}),
            status: 'completed'
          });
          
          remainingText = remainingText.replace(openAIMatch[0], '');
        }
      } catch (e) {
        console.error('Failed to parse OpenAI-style function call:', e);
      }
    }
    
    return {
      toolCalls,
      text: remainingText.trim()
    };
  }
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
        stream: false,
        stop: ['</function_calls>']
      });

      // Parse the response for tool calls
      const responseText = response.choices?.[0]?.message?.content || '';
      const { toolCalls, text } = this.parseToolCalls(responseText);
      
      // Build the output array
      const output = [];
      
      // Add tool calls first if any
      if (toolCalls.length > 0) {
        output.push(...toolCalls);
      }
      
      // Add remaining text if any
      if (text) {
        output.push({
          type: 'message',
          role: 'assistant',
          status: 'completed',
          content: [{
            type: 'output_text',
            text: text
          }]
        });
      }

      // Return the formatted response
      const usage = response.usage || {};
      return {
        id: response.id || `openrouter_${Date.now()}`,
        output: output,
        usage: {
          inputTokens: usage.prompt_tokens || 0,
          outputTokens: usage.completion_tokens || 0,
          totalTokens: usage.total_tokens || 0
        }
      };

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
        stream: true,
        stop: ['</function_calls>']
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

      // Parse the complete response for tool calls
      const { toolCalls, text } = this.parseToolCalls(fullContent);
      
      // Build the output array
      const output = [];
      
      // Add tool calls first if any
      if (toolCalls.length > 0) {
        output.push(...toolCalls);
      }
      
      // Add remaining text if any
      if (text) {
        output.push({
          type: 'message',
          role: 'assistant',
          status: 'completed',
          content: [{
            type: 'output_text',
            text: text
          }]
        });
      }

      // Final completion event
      if (process.env.DEBUG_OPENROUTER === 'true') {
        console.log('[OpenRouter] Yielding response_done with content length:', fullContent.length);
        console.log('[OpenRouter] Detected tool calls:', toolCalls.length);
      }
      yield {
        type: 'response_done',
        response: {
          id: `openrouter_${Date.now()}`,
          output: output,
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
        // Handle content that might be an array or object
        let content = '';
        if (typeof msg.content === 'string') {
          content = msg.content;
        } else if (Array.isArray(msg.content)) {
          // Extract text from content array
          content = msg.content.map(item => {
            if (typeof item === 'string') return item;
            if (item.type === 'text' || item.type === 'output_text') return item.text || '';
            return '';
          }).join('');
        } else if (msg.content && typeof msg.content === 'object') {
          content = JSON.stringify(msg.content);
        }
        
        return {
          role: msg.role,
          content: content || ''
        };
      }
      
      // Handle tool response messages
      if (msg.type === 'function_call_output') {
        let resultStr = '';
        if (typeof msg.result === 'string') {
          resultStr = msg.result;
        } else {
          resultStr = JSON.stringify(msg.result);
        }
        
        return {
          role: 'user',
          content: `Tool result for ${msg.toolName || 'unknown'}: ${resultStr}`
        };
      }

      // Handle standard OpenAI format
      let content = '';
      if (typeof msg.content === 'string') {
        content = msg.content;
      } else if (Array.isArray(msg.content)) {
        content = msg.content.map(item => {
          if (typeof item === 'string') return item;
          if (item.type === 'text' || item.type === 'output_text') return item.text || '';
          return '';
        }).join('');
      } else if (msg.content && typeof msg.content === 'object') {
        content = JSON.stringify(msg.content);
      }
      
      return {
        role: msg.role,
        content: content || ''
      };
    }).filter(msg => msg.content && typeof msg.content === 'string' && msg.content.trim());

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
      defaultModel: config.defaultModel || 'openrouter/horizon-alpha',
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
 * Predefined model configurations for different agent types (2025 Latest Models)
 */
export const AGENT_MODEL_MAP = {
  // Orchestrator - Stealth model (possibly GPT-5 or OpenAI FOSS)
  'Orchestrator': 'openrouter/horizon-alpha',
  
  // Analytical and reasoning tasks
  'Pricing Agent': 'openai/o3',              // Best reasoning model
  'Inventory Agent': 'z-ai/glm-4.5-air:free', // SOTA agentic model
  'Sales Agent': 'anthropic/claude-sonnet-4', // Latest Claude
  
  // Code and technical tasks  
  'SWE Agent': 'qwen/qwen3-coder:free',      // Specialized coding model
  'Documentation Agent': 'anthropic/claude-sonnet-4',
  
  // Creative and content tasks
  'Product Management Agent': 'anthropic/claude-sonnet-4',
  'Features Agent': 'openai/gpt-4.1',       // Latest OpenAI
  
  // Fast processing tasks
  'Utility Agent': 'openai/gpt-4.1-mini',   // Fast OpenAI
  'Memory Operations': 'openai/gpt-4.1-nano', // Fastest OpenAI
  
  // Agentic tasks
  'Google Workspace Agent': 'z-ai/glm-4.5-air:free', // SOTA agentic
  'GA4 Analytics Agent': 'z-ai/glm-4.5-air:free',
  
  // Default fallback
  'default': 'openrouter/horizon-alpha'
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
      defaultModel: process.env.OPENROUTER_MODEL || 'openrouter/horizon-alpha'
    });
  }
  
  // Return null for other providers (handled by existing logic)
  return null;
}

export default OpenRouterProvider;