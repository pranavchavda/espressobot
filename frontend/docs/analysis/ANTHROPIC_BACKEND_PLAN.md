# Anthropic Backend Plan

## Current Situation
- OpenAI Agents SDK is tightly coupled to OpenAI's API
- Attempting to integrate Anthropic models into the SDK creates unnecessary complexity
- Direct Anthropic API works perfectly (tested with claude-opus-4-0 and claude-sonnet-4-0)

## Future Architecture

### Option 1: Parallel Backend
Create a separate backend service that uses Anthropic's SDK directly:
- `/server/anthropic-backend/` - Separate service running on different port
- Custom agent system built around Anthropic's message API
- Own SSE streaming implementation
- Frontend can switch between backends based on user preference

### Option 2: Unified Agent Abstraction
Build our own agent abstraction layer:
```javascript
// Abstract agent interface
class UnifiedAgent {
  constructor(config) {
    this.provider = config.provider; // 'openai' or 'anthropic'
    this.model = config.model;
    this.tools = config.tools;
  }
  
  async run(prompt, options) {
    if (this.provider === 'anthropic') {
      return this.runAnthropic(prompt, options);
    } else {
      return this.runOpenAI(prompt, options);
    }
  }
}
```

### Option 3: API Gateway
Use an API gateway service that provides OpenAI-compatible endpoints:
- LiteLLM Proxy
- OpenRouter (commercial)
- Custom proxy service

## Implementation Notes

### Direct Anthropic Integration (Tested & Working)
```javascript
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

// Models available:
// - claude-opus-4-0
// - claude-sonnet-4-0
// - claude-3-5-sonnet-20241022
// - claude-3-5-haiku-20241022
// - claude-3-opus-20240229

const response = await client.messages.create({
  model: 'claude-sonnet-4-0',
  messages: [{ role: 'user', content: 'Hello!' }],
  tools: [...],  // Tool format is similar to OpenAI
  max_tokens: 4096
});
```

### Key Differences to Handle
1. **Message Format**: Anthropic uses a slightly different message structure
2. **System Prompts**: Handled separately in Anthropic (not as a message)
3. **Tool Results**: Different format for tool responses
4. **Streaming**: Different SSE event structure

## Recommendation
Start with **Option 2** (Unified Agent Abstraction) as it:
- Maintains the current architecture
- Allows gradual migration
- Provides flexibility to switch providers per agent
- Keeps the codebase manageable

## Files Created for Reference
- `/server/providers/anthropic-provider.js` - Initial attempt at ModelProvider
- `/server/providers/anthropic-agent-wrapper.js` - Working wrapper implementation
- `/test-anthropic-direct.js` - Confirms Anthropic API access works

## Next Steps When Ready
1. Create `/server/unified-agent/` directory
2. Build provider-agnostic agent system
3. Migrate existing agents one by one
4. Add provider selection in UI
5. Update documentation