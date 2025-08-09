## Development Notes

- Use context7 and/or deepwiki to ascertain what langgraph wants, we are using the latest versions, and they won't align with your training data pre-knowledge-cutoff

## System Status (January 9, 2025)

### ✅ Major Optimizations Completed

#### 1. **Orchestrator Efficiency - 50% Cost Reduction**
- **Issue**: Orchestrator was making TWO API calls for every direct response
  - First call: Routing decision with full system prompt
  - Second call: Generate actual response with simple prompt
- **Solution**: Modified `orchestrator_direct.py` to use routing response directly when complete
- **Impact**: ~50% reduction in API costs for direct orchestrator responses
- **Implementation**: Check if routing decision contains complete message (>20 chars), use it directly

#### 2. **Memory System Fully Operational**
- **Extraction**: Working perfectly after each conversation using GPT-4o-mini
- **Storage**: 16+ memories successfully stored in PostgreSQL with embeddings
- **Deduplication**: 4-layer system preventing duplicates (hash, fuzzy text, key phrases, semantic)
- **Categories**: facts, preferences, interactions, problems, solutions, products, general
- **Admin UI**: Fully functional at `/admin/memory` with search/filter/export capabilities

#### 3. **Multimodal Support Added**
- **Image Upload**: Orchestrator can now process images in conversations
- **Implementation**: Added proper content array handling in `chat.py`
- **Format Support**: URL images, data URLs, base64 encoded images

#### 4. **Dynamic Model Configuration**
- **Per-Agent Models**: Each agent can use different models/providers
- **Provider Support**: OpenAI (direct), Anthropic (direct), OpenRouter (proxy)
- **UI Integration**: Agent management page allows switching providers/models
- **Fix Applied**: Model name normalization for OpenRouter compatibility

### 🐛 Critical Fixes Applied

1. **Memory Management Page**
   - Fixed user ID issue (was using 'all', now defaults to '1')
   - Memories now display correctly in admin interface

2. **React Router Compatibility**
   - Removed useLoaderData usage (incompatible with BrowserRouter)
   - Fixed 422 errors on memory endpoints

3. **OpenRouter Model Issues**
   - Fixed model ID validation (e.g., `google/gemini-2.5-pro-preview`)
   - Proper provider prefix handling

4. **GPT-5 Streaming**
   - Bypassed organization verification requirement
   - Non-streaming fallback for GPT-5 models

### 📊 Current Architecture

```
langgraph-backend/
├── app/
│   ├── orchestrator_direct.py       # Optimized single-call orchestrator
│   ├── agents/                      # Specialized agents with context support
│   │   ├── base_context_mixin.py    # A2A context passing
│   │   └── memory_aware_mixin.py    # Memory injection support
│   ├── memory/                      # Memory system
│   │   ├── memory_persistence.py    # Extraction & storage
│   │   └── postgres_memory_manager.py # Database operations
│   ├── config/
│   │   ├── agent_model_manager.py   # Dynamic model configuration
│   │   └── agent_models.json        # Per-agent model settings
│   └── api/
│       ├── chat.py                  # Multimodal message support
│       ├── memory_enhanced.py       # Memory CRUD endpoints
│       └── agent_management.py      # Dynamic agent configuration
```

### ✅ LangSmith Tracing Integration (January 9, 2025)

**Implementation Complete:**
- Added LangSmith client initialization in `llm_factory.py`
- Decorated orchestrator methods with `@traceable`:
  - `process_request` - Main request processing
  - `synthesize_multi_agent` - Multi-agent coordination
- Decorated agent base methods with `@traceable`:
  - `__call__` - Agent invocation
  - `_process_messages` - Message processing
- Environment variables required:
  ```bash
  LANGSMITH_TRACING="true"
  LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
  LANGSMITH_API_KEY="<your-api-key>"
  LANGSMITH_PROJECT="espressobot"
  ```
- View traces at: https://smith.langchain.com/o/pranav-kulesza/projects/p/espressobot/runs

### 🚀 Next Steps

1. **Memory Injection Refinement**
   - Test memory influence on agent responses
   - Optimize retrieval based on relevance scores
   - Fine-tune importance scoring algorithms

2. **A2A Context Enhancement**
   - Improve context passing between agents
   - Add conversation summary for multi-agent tasks

3. **Performance Monitoring**
   - Track API usage reduction metrics via LangSmith
   - Monitor memory extraction quality
   - Analyze trace data for optimization opportunities

4. **Fix Database Issues**
   - Fix prompt_fragments table vector type
   - Resolve PostgreSQL role "pranav" error

### 📝 Important Configuration Notes

- **Database**: PostgreSQL at `espressobot_dev` with memories table
- **Default User**: User ID "1" for memory operations
- **Memory Threshold**: 0.7 similarity for deduplication
- **Streaming**: Disabled for GPT-5 models (verification required)
- **Token Optimization**: Single API call for direct responses

### 🔧 Quick Commands

```bash
# Check memory count in database
PGPASSWORD=localdev123 psql -h localhost -U espressobot -d espressobot_dev -c "SELECT COUNT(*) FROM memories;"

# Test memory API
curl -s "http://localhost:8000/api/memory/list/1?limit=10" | jq '.'

# View orchestrator logs for duplicate call monitoring
grep "API Call" server.log | tail -20
```

### ⚠️ Known Issues to Monitor

1. **Streaming Display**: Messages may briefly appear twice during streaming (UI rendering issue, not data)
2. **Title Auto-Refresh**: Sidebar doesn't auto-refresh when title is generated
3. **Memory Injection**: Not yet fully tested with agent responses

---
*Last Updated: January 9, 2025*
- model name is fine. gpt-4.1-nano is faster, cheaper and newer than gpt-4o-mini