import Anthropic from '@anthropic-ai/sdk';

/**
 * Custom Model Provider for Anthropic Claude models
 * Implements the OpenAI Agents SDK ModelProvider interface
 */
export class AnthropicModelProvider {
  constructor(apiKey) {
    this.anthropic = new Anthropic({
      apiKey: apiKey || process.env.ANTHROPIC_API_KEY
    });
    
    // No need for model mapping - Anthropic provides server-side aliases:
    // claude-3-5-haiku-latest, claude-3-5-sonnet-latest, etc.
  }

  async getModel(modelName) {
    // Just pass the model name directly - Anthropic handles aliases
    return new AnthropicModel(this.anthropic, modelName);
  }
}

/**
 * Anthropic Model implementation
 * Implements the OpenAI Agents SDK Model interface
 */
export class AnthropicModel {
  constructor(client, modelId) {
    this.client = client;
    this.modelId = modelId;
  }

  async generateChatCompletion(request) {
    try {
      // Convert OpenAI format to Anthropic format
      const messages = this.convertMessages(request.messages);
      const system = this.extractSystemMessage(request.messages);
      
      const response = await this.client.messages.create({
        model: this.modelId,
        messages: messages,
        system: system,
        max_tokens: request.max_tokens || 4096,
        temperature: request.temperature || 0.7,
        stream: request.stream || false,
        tools: this.convertTools(request.tools),
        tool_choice: request.tool_choice
      });

      // Convert response back to OpenAI format
      if (request.stream) {
        return this.createStreamResponse(response);
      } else {
        return this.createNonStreamResponse(response);
      }
    } catch (error) {
      console.error('AnthropicModel error:', error);
      throw error;
    }
  }

  // Convert OpenAI messages format to Anthropic format
  convertMessages(messages) {
    const anthropicMessages = [];
    
    for (const msg of messages) {
      if (msg.role === 'system') {
        // System messages are handled separately in Anthropic
        continue;
      }
      
      if (msg.role === 'assistant' && msg.tool_calls) {
        // Convert tool calls
        anthropicMessages.push({
          role: 'assistant',
          content: msg.content || '',
          tool_calls: msg.tool_calls.map(tc => ({
            id: tc.id,
            type: 'function',
            function: {
              name: tc.function.name,
              arguments: tc.function.arguments
            }
          }))
        });
      } else if (msg.role === 'tool') {
        // Tool responses
        anthropicMessages.push({
          role: 'user',
          content: [{
            type: 'tool_result',
            tool_call_id: msg.tool_call_id,
            content: msg.content
          }]
        });
      } else {
        // Regular messages
        anthropicMessages.push({
          role: msg.role === 'user' ? 'user' : 'assistant',
          content: msg.content
        });
      }
    }
    
    return anthropicMessages;
  }

  // Extract system message from OpenAI format
  extractSystemMessage(messages) {
    const systemMessage = messages.find(m => m.role === 'system');
    return systemMessage ? systemMessage.content : null;
  }

  // Convert OpenAI tools format to Anthropic format
  convertTools(tools) {
    if (!tools) return undefined;
    
    return tools.map(tool => ({
      name: tool.function.name,
      description: tool.function.description,
      input_schema: tool.function.parameters
    }));
  }

  // Create OpenAI-compatible response from Anthropic response
  createNonStreamResponse(anthropicResponse) {
    const choice = {
      index: 0,
      message: {
        role: 'assistant',
        content: anthropicResponse.content[0]?.text || ''
      },
      finish_reason: anthropicResponse.stop_reason || 'stop'
    };

    // Handle tool calls
    if (anthropicResponse.content.some(c => c.type === 'tool_use')) {
      choice.message.tool_calls = anthropicResponse.content
        .filter(c => c.type === 'tool_use')
        .map((tc, index) => ({
          id: tc.id,
          type: 'function',
          function: {
            name: tc.name,
            arguments: JSON.stringify(tc.input)
          }
        }));
    }

    return {
      id: anthropicResponse.id,
      object: 'chat.completion',
      created: Date.now(),
      model: this.modelId,
      choices: [choice],
      usage: {
        prompt_tokens: anthropicResponse.usage.input_tokens,
        completion_tokens: anthropicResponse.usage.output_tokens,
        total_tokens: anthropicResponse.usage.input_tokens + anthropicResponse.usage.output_tokens
      }
    };
  }

  // Create streaming response (returns an async generator)
  async* createStreamResponse(anthropicStream) {
    for await (const chunk of anthropicStream) {
      if (chunk.type === 'content_block_delta') {
        yield {
          id: chunk.id || 'stream',
          object: 'chat.completion.chunk',
          created: Date.now(),
          model: this.modelId,
          choices: [{
            index: 0,
            delta: {
              content: chunk.delta.text || ''
            },
            finish_reason: null
          }]
        };
      } else if (chunk.type === 'message_stop') {
        yield {
          id: chunk.id || 'stream',
          object: 'chat.completion.chunk',
          created: Date.now(),
          model: this.modelId,
          choices: [{
            index: 0,
            delta: {},
            finish_reason: 'stop'
          }]
        };
      }
    }
  }
}

// Helper function to create an Anthropic-powered agent
export function createAnthropicAgent(agentConfig, apiKey) {
  const provider = new AnthropicModelProvider(apiKey);
  
  // Replace the model in the agent config
  return {
    ...agentConfig,
    model: 'claude-4-sonnet',  // or any Claude model you prefer
    modelProvider: provider
  };
}