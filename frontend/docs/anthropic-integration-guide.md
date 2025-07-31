# Anthropic Integration with OpenAI Agents SDK

**Status**: ✅ **WORKING** - Full integration with streaming support  
**Date**: July 31, 2025  
**Models Supported**: Claude 3.5 Sonnet, Claude 4 Sonnet  

## 🎯 Overview

This document captures the complete journey of integrating Anthropic's Claude models with the OpenAI Agents SDK, including all the challenges, breakthroughs, and the final working solution.

## 🚀 Final Working Solution

### Quick Start

```bash
# Set environment variables
MODEL_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=your_key_here

# Optional: Enable debug logging
DEBUG_ANTHROPIC=true

# Run with Anthropic
pnpm run dev
```

### Architecture

The solution uses a **Direct Provider Pattern** with these key components:

1. **Custom Anthropic Provider** (`/server/models/anthropic-provider.js`)
2. **Agent + Runner Pattern** (both required for proper integration)
3. **Request Structure Adaptation** (OpenAI Agents SDK → Anthropic API)
4. **Streaming Event Translation** (Anthropic streams → OpenAI Agents events)

## 🧩 The Challenge

### Initial Problem
The OpenAI Agents SDK is designed for OpenAI models. Integrating other providers requires understanding:
- How the SDK constructs requests for custom providers
- What streaming event format it expects
- How to properly implement the Model and ModelProvider interfaces

### Key Discovery: Request Structure Mismatch

❌ **Expected** (based on OpenAI API patterns):
```javascript
{
  messages: [{role: 'user', content: 'Hello'}],
  system: 'You are a helpful assistant'
}
```

✅ **Actual** (OpenAI Agents SDK format):
```javascript
{
  input: [{type: 'message', role: 'user', content: 'Hello'}],
  systemInstructions: 'You are a helpful assistant'
}
```

This was the **core breakthrough** - the SDK uses a completely different request structure!

## 🔍 Pre-Success Tribulations

### Phase 1: The Silent Failure
**Problem**: Claude was responding with generic "Hello" messages instead of actual user input.

**Symptoms**:
- ✅ Streaming infrastructure worked
- ✅ Claude API calls succeeded  
- ❌ User messages weren't reaching Claude
- ❌ Always got fallback responses

**Debug Process**:
```javascript
// Added extensive logging to trace message flow
console.log('[DEBUG] Received request:', {
  messages: request.messages?.length || 0,
  system: request.system?.length || 0,
  hasMessages: !!request.messages
});

// Result: { messages: 0, system: 0, hasMessages: false }
```

**Key Insight**: The OpenAI Agents SDK wasn't passing messages in the expected format.

### Phase 2: The Request Structure Discovery
**Breakthrough**: Added full request logging:
```javascript
console.log('[DEBUG] Full request:', JSON.stringify(request, null, 2));
```

**Result**:
```json
{
  "systemInstructions": "You are Claude...",
  "input": [
    {
      "type": "message", 
      "role": "user",
      "content": "This is a test. What model are you using?"
    }
  ],
  "modelSettings": {},
  "tools": [],
  "handoffs": [],
  "outputType": "text",
  "tracing": true
}
```

**Revelation**: The SDK uses `input` and `systemInstructions`, not `messages` and `system`!

### Phase 3: The Streaming Timing Issue
**Problem**: Messages were being passed correctly, but streaming responses arrived after `runner.run()` returned.

**Symptoms**:
```
📋 Final Result: 
Output length: 0

✅ Runner-based test completed successfully!
[ANTHROPIC STREAM DEBUG] Yielding delta: I am Claude...
```

**Solution**: The combination of Agent model + Runner modelProvider + proper async stream handling resolved the timing.

### Phase 4: AI SDK Integration Attempt
**Experiment**: Tried using Vercel AI SDK integration (`@ai-sdk/anthropic` + `@openai/agents-extensions`).

**Result**: Failed silently - model created but no responses.

**Learning**: While AI SDK is officially supported, there may be version compatibility issues or missing configuration. Direct provider pattern proved more reliable.

## 🏗️ Technical Implementation

### 1. Custom Provider Structure

```javascript
export class AnthropicModel {
  async getResponse(request) {
    // Handle non-streaming requests
    const messages = this.convertMessages(request.input || []);
    const system = request.systemInstructions || '';
    
    const response = await this.anthropic.messages.create({
      model: this.modelName,
      messages: messages,
      system: system,
      max_tokens: request.max_tokens || 4096
    });
    
    return this.formatResponse(response);
  }

  async *getStreamedResponse(request) {
    // Handle streaming requests
    const messages = this.convertMessages(request.input || []);
    const system = request.systemInstructions || '';
    
    yield { type: 'response_started' };
    
    const stream = await this.anthropic.messages.create({
      model: this.modelName,
      messages: messages,
      system: system,
      stream: true
    });

    for await (const chunk of stream) {
      if (chunk.type === 'content_block_delta') {
        yield {
          type: 'output_text_delta',
          delta: chunk.delta.text
        };
      }
    }

    yield {
      type: 'response_done',
      response: this.formatFinalResponse(fullContent, usage)
    };
  }
}
```

### 2. Message Format Conversion

```javascript
convertMessages(messages) {
  return messages.map(msg => {
    // Handle OpenAI Agents SDK message format
    if (msg.type === 'message') {
      return {
        role: msg.role === 'system' ? 'user' : msg.role,
        content: msg.content || ''
      };
    }
    
    // Handle standard OpenAI format (fallback)
    return {
      role: msg.role === 'system' ? 'user' : msg.role,
      content: msg.content || ''
    };
  }).filter(msg => msg.content && msg.content.trim());
}
```

### 3. Orchestrator Integration

```javascript
function createModelProvider() {
  const modelProvider = process.env.MODEL_PROVIDER || 'openai';
  
  if (modelProvider === 'anthropic') {
    return new AnthropicProvider({
      modelName: process.env.ANTHROPIC_MODEL || 'claude-sonnet-4-20250514',
      apiKey: process.env.ANTHROPIC_API_KEY
    });
  }
  
  return null; // Default to OpenAI
}

// In agent creation
const modelProvider = createModelProvider();
if (modelProvider) {
  const runner = new Runner({ modelProvider });
  const agent = new Agent({
    name: 'EspressoBot',
    instructions: systemPrompt,
    model: modelProvider.getModel()
  });
  
  result = await runner.run(agent, message, options);
}
```

### 4. Streaming Event Format

The OpenAI Agents SDK expects these specific event types:

```javascript
// Start streaming
yield { type: 'response_started' };

// Stream content tokens
yield {
  type: 'output_text_delta',
  delta: 'token text'
};

// Complete streaming  
yield {
  type: 'response_done',
  response: {
    id: 'unique_id',
    output: [{
      type: 'message',
      role: 'assistant',
      status: 'completed',
      content: [{
        type: 'output_text',
        text: 'full response'
      }]
    }],
    usage: {
      inputTokens: 100,
      outputTokens: 50, 
      totalTokens: 150
    }
  }
};
```

## ✅ Verification Results

### Test Output
```
Sending: "Test 1: What model are you using? Answer in exactly 10 words."

[ANTHROPIC STREAM DEBUG] Processing input messages: 1
[ANTHROPIC STREAM DEBUG] Converted messages: 1  
[ANTHROPIC STREAM DEBUG] System message length: 12143
[ANTHROPIC STREAM DEBUG] First message: {
  role: 'user',
  content: 'Test 1: What model are you using? Answer in exactly 10 words.'
}

*** Stream token received: I
*** Stream token received:  am Claude 3.5 Sonnet by
*** Stream token received:  Anthropic, powering EspressoBot1.

Final Response: "I am Claude 3.5 Sonnet by Anthropic, powering EspressoBot1."
```

### Success Metrics
- ✅ **Message Passing**: Real user input reaches Claude (not fallback)
- ✅ **System Instructions**: Full context and prompts work
- ✅ **Streaming**: Token-by-token real-time responses  
- ✅ **Response Quality**: Contextually appropriate answers
- ✅ **Integration**: Works seamlessly with orchestrator
- ✅ **Performance**: No timing issues or async problems

## 🔑 Key Learnings

### 1. OpenAI Agents SDK Request Structure
- Uses `input` array, not `messages` array
- Uses `systemInstructions` string, not `system` field
- Message objects have `type: 'message'` wrapper

### 2. Both Agent Model AND Runner ModelProvider Required
- Setting only `Agent({model})` doesn't work
- Setting only `Runner({modelProvider})` doesn't work  
- Need **both** for proper integration

### 3. Streaming Event Types are Specific
- Must use exact event names: `response_started`, `output_text_delta`, `response_done`
- Response structure must match OpenAI Agents SDK schema
- Async generator pattern works correctly

### 4. AI SDK Integration Issues
- Official support exists but may have version conflicts
- Direct provider pattern is more reliable and debuggable
- Custom implementation provides full control

## 🚀 Reusable Patterns for Other Providers

This implementation creates reusable patterns for integrating any LLM provider:

### Template Structure
```javascript
// 1. Provider class with getModel() method
class CustomProvider {
  getModel(modelName) {
    return new CustomModel(config);
  }
}

// 2. Model class with both sync and streaming methods
class CustomModel {
  async getResponse(request) {
    // Handle request.input and request.systemInstructions
    // Call provider API
    // Return formatted response
  }
  
  async *getStreamedResponse(request) {
    // yield response_started
    // Stream with output_text_delta events
    // yield response_done with final response
  }
}

// 3. Message conversion utility
convertMessages(messages) {
  // Handle {type: 'message', role, content} format
  // Convert to provider's expected format
}
```

### Integration Points
1. **Environment Configuration**: `MODEL_PROVIDER=provider_name`
2. **Provider Factory**: `createModelProvider()` function
3. **Orchestrator Integration**: Agent + Runner pattern
4. **Error Handling**: Proper fallbacks and debugging

## 🐛 Debugging Tips

### Essential Debug Logging
```javascript
// Log request structure
console.log('[DEBUG] Request keys:', Object.keys(request));
console.log('[DEBUG] Input messages:', request.input?.length);
console.log('[DEBUG] System instructions:', request.systemInstructions?.length);

// Log message conversion
console.log('[DEBUG] Converted messages:', convertedMessages.length);
console.log('[DEBUG] First message:', convertedMessages[0]);

// Log streaming events
console.log('[DEBUG] Yielding:', eventType, eventData);
```

### Common Issues
1. **No response**: Check request structure (`input` vs `messages`)
2. **Generic responses**: Verify message conversion preserves content
3. **Streaming timing**: Ensure both Agent model and Runner modelProvider set
4. **Event format errors**: Match exact OpenAI Agents SDK event schema

## 📚 Files Reference

- **Provider Implementation**: `/server/models/anthropic-provider.js`
- **Orchestrator Integration**: `/server/espressobot1.js` (lines 1801-1820, 2395-2412)
- **Test Scripts**: 
  - `/test-runner-anthropic.js` (isolated testing)
  - `/test-orchestrator-aisdk.js` (full integration testing)
- **Configuration**: Environment variables in `.env`

## 🔮 Future Improvements

1. **Clean up debug logging** for production
2. **Add error handling** for API failures and rate limits
3. **Support more Claude models** (Claude 3, Claude 3.5 Haiku, etc.)
4. **Implement tool calling** when Anthropic supports it in agents
5. **Optimize token usage** and streaming performance
6. **Add model-specific configurations** (temperature, max_tokens, etc.)

## 🎯 Next Steps

This integration proves that **any LLM provider can be integrated** with the OpenAI Agents SDK using the direct provider pattern. The next logical steps are:

1. **OpenRouter Integration** - Access to 100+ models through one API
2. **Groq Integration** - Ultra-fast inference for supported models  
3. **Google Gemini Integration** - Alternative to OpenAI/Anthropic
4. **Local Model Support** - Ollama integration for privacy-focused deployments

The architecture is now **proven and reusable** for any provider integration!

---

*This integration represents a significant breakthrough in LLM provider flexibility for the OpenAI Agents ecosystem. The patterns established here can be applied to integrate virtually any language model provider.*