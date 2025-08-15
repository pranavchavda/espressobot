/**
 * Custom Anthropic Model Provider for OpenAI Agents SDK
 * Implements the Model and ModelProvider interfaces to use Claude models
 */

import Anthropic from '@anthropic-ai/sdk';

export class AnthropicModel {
  constructor(config) {
    this.name = config.modelName;
    this.modelName = config.modelName;
    this.anthropic = new Anthropic({
      apiKey: config.apiKey,
      defaultHeaders: {
        'anthropic-version': '2023-06-01'
      }
    });
    this.config = config;
  }

  async getResponse(request) {
    try {
      // Debug logging (can be disabled in production)
      if (process.env.DEBUG_ANTHROPIC === 'true') {
        console.log('[ANTHROPIC DEBUG] Non-streaming request received');
      }
      
      // Convert OpenAI Agents SDK format to Anthropic format
      // The SDK uses 'input' array and 'systemInstructions', not 'messages' and 'system'
      const inputMessages = request.input || request.messages || [];
      const systemMessage = request.systemInstructions || request.system || '';
      
      const messages = this.convertMessages(inputMessages);
      
      if (process.env.DEBUG_ANTHROPIC === 'true') {
        console.log('[ANTHROPIC DEBUG] Converted messages:', messages?.length || 0);
        console.log('[ANTHROPIC DEBUG] System message length:', systemMessage?.length || 0);
      }

      const response = await this.anthropic.messages.create({
        model: this.modelName,
        max_tokens: request.max_tokens || 4096,
        temperature: request.temperature || 0.7,
        system: systemMessage,
        messages: messages
      });

      // Convert Anthropic response to OpenAI format
      return {
        id: `anthropic_${Date.now()}`,
        usage: {
          inputTokens: response.usage.input_tokens,
          outputTokens: response.usage.output_tokens,
          totalTokens: response.usage.input_tokens + response.usage.output_tokens
        },
        output: [{
          type: 'message',
          role: 'assistant', 
          status: 'completed',
          content: [{
            type: 'output_text',
            text: response.content[0].text
          }]
        }]
      };

    } catch (error) {
      console.error('Anthropic API error:', error);
      throw error;
    }
  }

  async *getStreamedResponse(request) {
    try {
      // Debug logging (can be disabled in production)
      if (process.env.DEBUG_ANTHROPIC === 'true') {
        console.log('[ANTHROPIC STREAM DEBUG] Received request with keys:', Object.keys(request || {}));
        console.log('[ANTHROPIC STREAM DEBUG] Input messages:', request.input?.length || 0);
      }
      
      // Convert OpenAI Agents SDK format to Anthropic format  
      // The SDK uses 'input' array and 'systemInstructions', not 'messages' and 'system'
      const inputMessages = request.input || request.messages || [];
      const systemMessage = request.systemInstructions || request.system || '';
      
      const messages = this.convertMessages(inputMessages);
      
      if (process.env.DEBUG_ANTHROPIC === 'true') {
        console.log('[ANTHROPIC STREAM DEBUG] Converted messages:', messages?.length || 0);
        console.log('[ANTHROPIC STREAM DEBUG] System message length:', systemMessage?.length || 0);
        if (messages?.length > 0) {
          console.log('[ANTHROPIC STREAM DEBUG] First message:', messages[0]);
        }
      }

      // First yield response started event
      yield {
        type: 'response_started'
      };

      const stream = await this.anthropic.messages.create({
        model: this.modelName,
        max_tokens: request.max_tokens || 4096,
        temperature: request.temperature || 0.7,
        system: systemMessage,
        messages: messages,
        stream: true
      });

      let fullContent = '';
      let usage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };

      for await (const chunk of stream) {
        if (chunk.type === 'content_block_delta') {
          const deltaText = chunk.delta.text || '';
          fullContent += deltaText;
          
          // Yield text delta event
          if (process.env.DEBUG_ANTHROPIC === 'true') {
            console.log('[ANTHROPIC STREAM DEBUG] Yielding delta:', deltaText.substring(0, 50));
          }
          yield {
            type: 'output_text_delta',
            delta: deltaText
          };
        } else if (chunk.type === 'message_delta' && chunk.usage) {
          usage = {
            prompt_tokens: chunk.usage.input_tokens || 0,
            completion_tokens: chunk.usage.output_tokens || 0,
            total_tokens: (chunk.usage.input_tokens || 0) + (chunk.usage.output_tokens || 0)
          };
        }
      }

      // Final completion event
      if (process.env.DEBUG_ANTHROPIC === 'true') {
        console.log('[ANTHROPIC STREAM DEBUG] Yielding response_done with content length:', fullContent.length);
      }
      yield {
        type: 'response_done',
        response: {
          id: `anthropic_${Date.now()}`,
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
      console.error('Anthropic streaming error:', error);
      // Don't yield error events - let the SDK handle errors
      throw error;
    }
  }

  convertMessages(messages) {
    const convertedMessages = messages.map(msg => {
      // Handle OpenAI Agents SDK message format
      if (msg.type === 'message') {
        return {
          role: msg.role === 'system' ? 'user' : msg.role,
          content: msg.content || ''
        };
      }
      
      // Handle tool calls and function calls if needed
      if (msg.tool_calls || msg.function_call) {
        // For now, convert to text representation
        // TODO: Implement proper tool calling when Anthropic supports it in agents
        return {
          role: msg.role === 'system' ? 'user' : msg.role,
          content: msg.content || 'Function call: ' + JSON.stringify(msg.tool_calls || msg.function_call)
        };
      }

      // Handle standard OpenAI format
      return {
        role: msg.role === 'system' ? 'user' : msg.role, // Convert system to user for Anthropic
        content: msg.content || ''
      };
    }).filter(msg => msg.content && msg.content.trim()); // Remove empty messages
    
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

export class AnthropicProvider {
  constructor(config = {}) {
    this.config = {
      modelName: config.modelName || 'claude-3-5-sonnet-20241022',
      apiKey: config.apiKey || process.env.ANTHROPIC_API_KEY,
      baseUrl: config.baseUrl || 'https://api.anthropic.com',
      ...config
    };

    if (!this.config.apiKey) {
      throw new Error('Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable or pass apiKey in config.');
    }
  }

  getModel(modelName) {
    const finalModelName = modelName || this.config.modelName;
    return new AnthropicModel({
      ...this.config,
      modelName: finalModelName
    });
  }
}

// Export default provider instance
export default AnthropicProvider;