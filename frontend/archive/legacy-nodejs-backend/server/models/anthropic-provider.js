/**
 * Custom Anthropic Model Provider for OpenAI Agents SDK
 * Implements the Model and ModelProvider interfaces to use Claude models
 * FIXED VERSION: Properly handles tool calls by parsing Claude's output
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

  /**
   * Parse Claude's text output for tool calls
   * Claude outputs tool calls in official format:
   * <function_calls>
   * <invoke>
   * <tool_name>function_name</tool_name>
   * <parameters>
   * <param1>value1</param1>
   * <param2>value2</param2>
   * </parameters>
   * </invoke>
   * </function_calls>
   * 
   * Also supports the simpler format: <invoke name="tool_name">{"param": "value"}</invoke>
   */
  parseToolCalls(text) {
    const toolCalls = [];
    let remainingText = text;
    
    // Parse the format Claude actually uses: <function_calls><invoke name="..."><parameter...
    const functionCallsRegex = /<function_calls>(.*?)<\/function_calls>/gs;
    const functionCallsMatch = functionCallsRegex.exec(text);
    
    if (functionCallsMatch) {
      const functionCallsContent = functionCallsMatch[1];
      
      // Look for <invoke name="tool_name"> format
      const invokeRegex = /<invoke\s+name="([^"]+)">(.*?)<\/invoke>/gs;
      let invokeMatch;
      
      while ((invokeMatch = invokeRegex.exec(functionCallsContent)) !== null) {
        const [, toolName, invokeContent] = invokeMatch;
        const args = {};
        
        // Extract parameters using <parameter name="...">value</parameter>
        const paramRegex = /<parameter\s+name="([^"]+)">(.*?)<\/parameter>/gs;
        let parameterMatch;
        
        while ((parameterMatch = paramRegex.exec(invokeContent)) !== null) {
          const [, paramName, paramValue] = parameterMatch;
          // Try to parse as JSON, otherwise keep as string
          try {
            args[paramName] = JSON.parse(paramValue.trim());
          } catch {
            args[paramName] = paramValue.trim();
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
      remainingText = remainingText.replace(functionCallsMatch[0], '').trim();
      
      // Also remove any hallucinated function results
      remainingText = remainingText.replace(/<function_result>.*?<\/function_result>/gs, '').trim();
    }
    
    // Check for the format with parameter tags (common in actual usage)
    const parameterFormatRegex = /<invoke\s+name="([^"]+)">(.*?)<\/invoke>/gs;
    let paramMatch;
    
    while ((paramMatch = parameterFormatRegex.exec(remainingText)) !== null) {
      const [fullMatch, toolName, invokeContent] = paramMatch;
      const args = {};
      
      // Extract parameters using <parameter name="...">value</parameter>
      const paramRegex = /<parameter\s+name="([^"]+)">(.*?)<\/parameter>/gs;
      let parameterMatch;
      
      while ((parameterMatch = paramRegex.exec(invokeContent)) !== null) {
        const [, paramName, paramValue] = parameterMatch;
        // Try to parse as JSON, otherwise keep as string
        try {
          args[paramName] = JSON.parse(paramValue.trim());
        } catch {
          args[paramName] = paramValue.trim();
        }
      }
      
      // If no parameters found, try to parse the entire content as JSON
      if (Object.keys(args).length === 0 && invokeContent.trim()) {
        try {
          const parsedArgs = JSON.parse(invokeContent.trim());
          Object.assign(args, parsedArgs);
        } catch {
          // Not JSON, ignore
        }
      }
      
      toolCalls.push({
        type: 'function_call',
        callId: `call_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        name: toolName,
        arguments: JSON.stringify(args),
        status: 'completed'
      });
      
      // Remove the tool call from the text
      remainingText = remainingText.replace(fullMatch, '');
    }
    
    return {
      toolCalls,
      text: remainingText.trim()
    };
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
        messages: messages,
        stop_sequences: ['</function_calls>']
      });

      // Parse the response for tool calls
      const responseText = response.content[0].text;
      const { toolCalls, text } = this.parseToolCalls(responseText);
      
      if (process.env.DEBUG_ANTHROPIC === 'true') {
        console.log('[ANTHROPIC DEBUG] Response text:', responseText.substring(0, 500));
        console.log('[ANTHROPIC DEBUG] Parsed tool calls:', toolCalls.length);
        if (toolCalls.length > 0) {
          console.log('[ANTHROPIC DEBUG] First tool call:', toolCalls[0]);
        }
      }
      
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

      // Convert Anthropic response to OpenAI format
      return {
        id: `anthropic_${Date.now()}`,
        usage: {
          inputTokens: response.usage.input_tokens,
          outputTokens: response.usage.output_tokens,
          totalTokens: response.usage.input_tokens + response.usage.output_tokens
        },
        output: output
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
        stream: true,
        stop_sequences: ['</function_calls>']
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

      // If content was cut off by stop sequence, add the closing tag
      if (fullContent.includes('<function_calls>') && !fullContent.includes('</function_calls>')) {
        fullContent += '</function_calls>';
      }
      
      // Parse the complete response for tool calls
      const { toolCalls, text } = this.parseToolCalls(fullContent);
      
      if (process.env.DEBUG_ANTHROPIC === 'true') {
        console.log('[ANTHROPIC STREAM DEBUG] Full content:', fullContent.substring(0, 500));
        console.log('[ANTHROPIC STREAM DEBUG] Parsed tool calls:', toolCalls);
        console.log('[ANTHROPIC STREAM DEBUG] Remaining text:', text?.substring(0, 200));
      }
      
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
      if (process.env.DEBUG_ANTHROPIC === 'true') {
        console.log('[ANTHROPIC STREAM DEBUG] Yielding response_done with content length:', fullContent.length);
        console.log('[ANTHROPIC STREAM DEBUG] Detected tool calls:', toolCalls.length);
      }
      yield {
        type: 'response_done',
        response: {
          id: `anthropic_${Date.now()}`,
          output: output,
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
    if (process.env.DEBUG_ANTHROPIC === 'true') {
      console.log('[ANTHROPIC DEBUG] Converting messages:', messages.length);
      console.log('[ANTHROPIC DEBUG] Message types:', messages.map(m => ({ type: m.type, contentType: typeof m.content, hasContent: !!m.content })));
    }
    
    const convertedMessages = messages.map(msg => {
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
          role: msg.role === 'system' ? 'user' : msg.role,
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

      // Handle standard OpenAI format or any other message type
      let content = '';
      if (msg.content === null || msg.content === undefined) {
        content = '';
      } else if (typeof msg.content === 'string') {
        content = msg.content;
      } else if (Array.isArray(msg.content)) {
        content = msg.content.map(item => {
          if (typeof item === 'string') return item;
          if (item && (item.type === 'text' || item.type === 'output_text')) return item.text || '';
          return '';
        }).join('');
      } else if (typeof msg.content === 'object') {
        content = JSON.stringify(msg.content);
      }
      
      return {
        role: msg.role === 'system' ? 'user' : msg.role, // Convert system to user for Anthropic
        content: content || ''
      };
    }).filter(msg => {
      // Ensure content exists and is a non-empty string
      return msg.content && 
             typeof msg.content === 'string' && 
             msg.content.trim().length > 0;
    }); // Remove empty messages
    
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