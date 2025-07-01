/**
 * Anthropic Agent Wrapper
 * Wraps OpenAI Agents SDK agents to use Anthropic's API
 */

import Anthropic from '@anthropic-ai/sdk';
import { tool } from '@openai/agents';

export class AnthropicAgentWrapper {
  constructor(apiKey) {
    this.client = new Anthropic({
      apiKey: apiKey || process.env.ANTHROPIC_API_KEY
    });
  }

  /**
   * Create a wrapper that mimics the Agent interface but uses Anthropic
   */
  wrapAgent(agentConfig) {
    const { name, model, instructions, tools = [] } = agentConfig;
    
    return {
      name,
      model,
      instructions,
      tools,
      _isAnthropicAgent: true,
      _anthropicClient: this.client
    };
  }

  /**
   * Run function that mimics the OpenAI Agents SDK run() but uses Anthropic
   */
  async run(agent, prompt, options = {}) {
    if (!agent._isAnthropicAgent) {
      throw new Error('Agent must be created with AnthropicAgentWrapper.wrapAgent()');
    }

    const { maxTurns = 10, onMessage, onStepStart, onStepFinish } = options;
    let messages = [];
    let currentTurn = 0;

    // Initial user message
    messages.push({ role: 'user', content: prompt });

    while (currentTurn < maxTurns) {
      currentTurn++;

      // Convert tools to Anthropic format
      const anthropicTools = agent.tools?.map(t => ({
        name: t.name,
        description: t.description,
        input_schema: t.parameters || { type: 'object', properties: {} }
      }));

      // Make API call
      const response = await this.client.messages.create({
        model: agent.model || 'claude-3-5-sonnet-20241022',
        messages: messages,
        system: agent.instructions,
        max_tokens: 4096,
        tools: anthropicTools,
        temperature: 0.7
      });

      // Process response
      let assistantMessage = { role: 'assistant', content: [] };
      let hasToolCalls = false;

      for (const content of response.content) {
        if (content.type === 'text') {
          assistantMessage.content.push({ type: 'text', text: content.text });
          
          // Call onMessage callback if provided
          if (onMessage && content.text) {
            onMessage({ content: content.text });
          }
        } else if (content.type === 'tool_use') {
          hasToolCalls = true;
          assistantMessage.content.push({
            type: 'tool_use',
            id: content.id,
            name: content.name,
            input: content.input
          });

          // Call onStepStart if provided
          if (onStepStart) {
            onStepStart({ type: 'tool_call', tool_name: content.name });
          }

          // Execute the tool
          const tool = agent.tools.find(t => t.name === content.name);
          if (tool && tool.execute) {
            try {
              const result = await tool.execute(content.input);
              
              // Add tool result to messages
              messages.push(assistantMessage);
              messages.push({
                role: 'user',
                content: [{
                  type: 'tool_result',
                  tool_use_id: content.id,
                  content: typeof result === 'string' ? result : JSON.stringify(result)
                }]
              });

              // Call onStepFinish if provided
              if (onStepFinish) {
                onStepFinish({ 
                  type: 'tool_call', 
                  tool_name: content.name,
                  result: result 
                });
              }
            } catch (error) {
              // Add error to messages
              messages.push(assistantMessage);
              messages.push({
                role: 'user',
                content: [{
                  type: 'tool_result',
                  tool_use_id: content.id,
                  content: `Error: ${error.message}`,
                  is_error: true
                }]
              });
            }
          }
        }
      }

      // If no tool calls, we're done
      if (!hasToolCalls) {
        messages.push(assistantMessage);
        
        // Extract final text response
        const finalText = assistantMessage.content
          .filter(c => c.type === 'text')
          .map(c => c.text)
          .join('\n');
        
        return {
          content: finalText,
          messages: messages,
          usage: response.usage
        };
      }
    }

    // Max turns reached
    return {
      content: 'Max turns reached',
      messages: messages,
      maxTurnsReached: true
    };
  }
}

// Singleton instance
let defaultWrapper = null;

/**
 * Get or create the default Anthropic wrapper
 */
export function getAnthropicWrapper(apiKey) {
  if (!defaultWrapper) {
    defaultWrapper = new AnthropicAgentWrapper(apiKey);
  }
  return defaultWrapper;
}

/**
 * Helper function to create an Anthropic-powered agent
 */
export function createAnthropicAgent(config) {
  const wrapper = getAnthropicWrapper();
  return wrapper.wrapAgent(config);
}

/**
 * Helper function to run an Anthropic agent
 */
export async function runAnthropicAgent(agent, prompt, options) {
  const wrapper = getAnthropicWrapper();
  return wrapper.run(agent, prompt, options);
}