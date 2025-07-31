# Multi-Provider LLM Integration Plan

**Status**: 📋 **PLANNED** - Ready for implementation  
**Date**: July 31, 2025  
**Dependencies**: Anthropic integration breakthrough (completed)

## 🎯 **Strategic Overview**

Implement a multi-tiered model provider architecture leveraging:
1. **Groq** for ultra-fast context/memory tasks (400+ t/s Chinese models)
2. **OpenRouter** for specialized agent models with fallback capabilities
3. **Existing Anthropic/OpenAI** for baseline functionality

## 🚀 **Phase 1: Groq Integration (High-Speed Context Tasks)**

### Target Models
- **Qwen-2.5-32b**: ~397 t/s, 128k context, GPT-4.1 level intelligence
- **DeepSeek-r1-distill-qwen-32b**: ~388 t/s, 128k context, strong reasoning
- **Kimi K2**: MoE model, 1T parameters, advanced tool use

### Implementation
1. **Create Groq Provider** (`/server/models/groq-provider.js`)
   - Use proven Direct Provider Pattern from Anthropic integration
   - Handle Groq API request/response format
   - Implement streaming for real-time responses

2. **Integrate with Context Systems**
   - Memory search operations (currently slow with embeddings)
   - Context analysis and synthesis 
   - Task planning and intent analysis
   - Bulk operation processing

3. **Configuration**
   ```bash
   MODEL_PROVIDER=groq
   GROQ_MODEL=qwen-2.5-32b  # or deepseek-r1-distill-qwen-32b
   GROQ_API_KEY=your_key
   ```

### Expected Benefits
- **10x faster** context processing (400+ t/s vs current ~40 t/s)
- **Cheaper** than GPT-4.1 for high-volume memory/context tasks
- **Maintains quality** with GPT-4.1 level Chinese models

## 🎯 **Phase 2: OpenRouter Integration (Specialized Agent Models)**

### Agent-Specific Model Selection
- **Pricing Agent**: Command R+ (analytical reasoning)
- **SWE Agent**: Claude Sonnet 4 (code generation)
- **Product Creator**: Creative writing fine-tuned models
- **Documentation Agent**: Technical writing specialists
- **Memory/Context**: Groq models (speed priority)
- **General Tasks**: OpenAI GPT-4.1 (baseline)

### Implementation
1. **Create OpenRouter Provider** (`/server/models/openrouter-provider.js`)
   - Support 300+ models through unified API
   - Dynamic model selection per agent
   - Cost optimization routing

2. **Agent Model Configuration**
   ```javascript
   const AGENT_MODEL_MAP = {
     'Pricing Agent': 'cohere/command-r-plus',
     'SWE Agent': 'anthropic/claude-sonnet-4', 
     'Product Management Agent': 'creative-tuned-model',
     'Memory Operations': 'groq/qwen-2.5-32b'
   };
   ```

3. **Environment Configuration**
   ```bash
   MODEL_PROVIDER=openrouter
   OPENROUTER_API_KEY=your_key
   AGENT_MODELS_CONFIG=path/to/config.json
   ```

## 🛡️ **Phase 3: Fallback & Reliability System**

### Multi-Provider Fallback Chain
1. **Primary Model**: Agent-specific optimal model
2. **Secondary**: Cost-effective alternative 
3. **Tertiary**: Groq high-speed model
4. **Fallback**: OpenAI GPT-4.1 (reliable baseline)

### Timeout & Retry Logic
- **10-second timeout** for primary model
- **Automatic failover** to secondary model
- **Circuit breaker** pattern for failed providers
- **Health monitoring** for provider status

### Implementation
1. **Provider Manager** (`/server/models/provider-manager.js`)
   - Centralized provider coordination
   - Health checking and failover
   - Load balancing across providers

2. **Configuration**
   ```javascript
   const FALLBACK_CONFIG = {
     'Pricing Agent': [
       'openrouter/command-r-plus',
       'groq/qwen-2.5-32b', 
       'openai/gpt-4.1'
     ],
     timeout: 10000,
     retries: 3
   };
   ```

## 🏗️ **Technical Architecture**

### Provider Abstraction Layer
```javascript
class UniversalModelProvider {
  constructor(config) {
    this.providers = {
      groq: new GroqProvider(config.groq),
      openrouter: new OpenRouterProvider(config.openrouter),
      anthropic: new AnthropicProvider(config.anthropic),
      openai: null // SDK default
    };
    this.fallbackChains = config.fallbackChains;
  }

  async getModelForAgent(agentName) {
    const chain = this.fallbackChains[agentName];
    return await this.tryProvidersInOrder(chain);
  }
}
```

### Agent Integration Points
1. **Orchestrator Update**: Modify `createModelProvider()` function
2. **Agent Creation**: Pass agent-specific model configuration
3. **MCP Agents**: Update specialized agents with optimal models
4. **Error Handling**: Implement graceful fallbacks

## 📊 **Expected Performance Improvements**

### Speed Gains
- **Memory/Context Tasks**: 10x faster (40 t/s → 400+ t/s)
- **Context Building**: Reduce from 4-5s to <1s
- **Memory Search**: Near-instant semantic matching

### Cost Optimization
- **High-Volume Tasks**: 50-70% cheaper with Chinese models
- **Specialized Tasks**: Right-sized models reduce waste
- **Fallback Prevention**: Fewer expensive backup calls

### Quality Improvements  
- **Analytical Tasks**: Enhanced with specialized models
- **Creative Tasks**: Purpose-built fine-tuned models
- **Code Generation**: Claude Sonnet 4 for SWE tasks
- **Reliability**: Multi-provider redundancy

## 🛠️ **Implementation Order**

### Sprint 1: Groq Foundation
1. Create Groq provider using Anthropic pattern
2. Test with Qwen-2.5-32b and DeepSeek models
3. Integrate with memory/context systems
4. Performance benchmarking

### Sprint 2: OpenRouter Integration
1. Implement OpenRouter provider
2. Create agent-model mapping system
3. Test specialized model assignments
4. Cost analysis and optimization

### Sprint 3: Fallback System
1. Build provider manager with health checks
2. Implement timeout and retry logic
3. Add circuit breaker patterns
4. Full integration testing

### Sprint 4: Production Optimization
1. Performance monitoring and alerting
2. Cost tracking and optimization
3. Error handling refinement
4. Documentation and deployment

## 🎯 **Success Metrics**

- **Speed**: Memory operations <1s (currently 4-5s)
- **Cost**: 50% reduction in context processing costs
- **Reliability**: 99.9% uptime with fallbacks
- **Quality**: Maintain or improve response quality
- **Flexibility**: Easy model swapping per agent

## 🔍 **Research Findings**

### Groq Performance Data (2025)
- **Qwen-2.5-32b**: 397 t/s, 128k context, 8k max completion
- **DeepSeek-r1-distill-qwen-32b**: 388 t/s, 128k context, 16k max completion
- **Both models**: Support tool calling and JSON mode
- **Pricing**: Significantly cheaper than GPT-4.1 for high-volume tasks

### OpenRouter Capabilities
- **300+ models** through unified API
- **Same pricing** as direct provider access
- **Unified fallbacks** and uptime pooling
- **Free tier options** for experimentation
- **Specialized models** for analytical, creative, and technical tasks

### Model Recommendations by Use Case
- **Analytical**: Cohere Command R+, Gemini 2.0 Flash
- **Creative**: EVA 70B variants, Creative-tuned models
- **Technical**: Claude models, DeepSeek variants
- **Speed**: Groq-hosted Chinese models (Qwen, DeepSeek)

## 🔧 **Implementation Notes**

### Leveraging Existing Architecture
This plan builds on the proven **Direct Provider Pattern** established with the Anthropic integration:
1. Custom provider classes with `getResponse()` and `getStreamedResponse()`
2. Request structure adaptation for each API
3. Agent + Runner integration pattern
4. Streaming event translation

### Configuration Strategy
- **Environment-based** provider selection
- **Agent-specific** model configuration
- **Runtime fallback** chain management
- **Debug logging** with provider-specific flags

### Testing Strategy
- **Unit tests** for each provider
- **Integration tests** with actual APIs
- **Performance benchmarks** for speed/cost
- **Fallback scenario** testing

---

*This plan leverages the breakthrough Anthropic integration patterns to build a sophisticated multi-provider architecture optimized for speed, cost, and specialization.*

**Next Steps**: Begin Sprint 1 with Groq provider implementation using the proven Direct Provider Pattern.