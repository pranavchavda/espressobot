## Development Notes

- Use context7 and/or deepwiki to ascertain what langgraph wants, we are using the latest versions, and they won't align with your training data pre-knowledge-cutoff

## System Status (August 9, 2025)

### ✅ Memory System v2 - Quality & Decay Implementation

#### Memory Extraction Improvements:
1. **Better Quality Filtering**
   - Refined extraction prompts to focus on long-term value
   - Added ephemerality detection (filters task-specific memories)
   - Confidence scoring (filters < 0.3 confidence)
   - Result: ~70% reduction in low-quality memories expected

2. **Memory Decay System**
   - Time-based decay with category-specific rates
   - Usage tracking (access_count, last_accessed_at)
   - Usefulness scoring with feedback loop
   - Automatic archival of old/unused memories

3. **Database Enhancements**
   - Added 10 new tracking columns to memories table
   - Created calculate_effective_importance() function
   - Added performance indexes for better query speed
   - Archive status for memory lifecycle management

4. **Feedback Loop Implementation**
   - Tracks which memories influenced responses
   - Updates usefulness scores based on usage
   - Analytics for memory health monitoring
   - Memory verification system for quality control

### ✅ Price Monitor Python Migration - COMPLETE

#### Successfully Migrated Components:
1. **Product Matching with Embeddings** (`app/services/price_monitor/product_matching.py`)
   - Implemented OpenAI text-embedding-3-large (3072 dimensions)
   - Cosine similarity calculation working
   - Hybrid matching: 40% embeddings + 60% traditional factors
   - **Result**: 37/51 products matched (72% match rate)

2. **MAP Violation Detection** (`app/services/price_monitor/violations.py`)
   - Detecting 7 violations correctly with severity levels
   - Creating PriceAlert records in database
   - Fixed SQL cartesian product bug (was showing 49 instead of 7)
   - Violation history tracking operational

3. **Frontend Integration** (`app/api/price_monitor.py`)
   - All endpoints operational including violation-history
   - Fixed field naming (plural forms for frontend compatibility)
   - Fixed PriceAlert model fields (old_price/new_price)
   - Competitor product URLs working

#### Fixed Issues:
- ✅ Shopify data showing $0 (MCP layer issue)
- ✅ "Today" button fetching tomorrow's date (timezone)
- ✅ Price monitor infinite polling loop
- ✅ Brotli compression error in competitor scraping
- ✅ Product matching finding 0 matches (missing embeddings)
- ✅ "Unknown Product" display in price alerts
- ✅ MAP violation statistics showing 49 instead of 7

## Previous System Status (January 9, 2025)

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
- View traces at: https://smith.langchain.com/o/336cb8ba-b6ab-42fa-85a4-9c079014f4ce/projects/p/espressobot/runs

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
PGPASSWORD=localdev123 psql -h localhost -U espressobot -d espressobot_dev -c "SELECT COUNT(*) FROM memories WHERE status='active';"

# View memory quality metrics
PGPASSWORD=localdev123 psql -h localhost -U espressobot -d espressobot_dev -c "SELECT AVG(confidence_score) as avg_confidence, AVG(usefulness_score) as avg_usefulness, COUNT(*) FILTER (WHERE is_ephemeral) as ephemeral_count FROM memories WHERE status='active';"

# Test memory API
curl -s "http://localhost:8000/api/memory/list/1?limit=10" | jq '.'

# Archive old memories manually
PGPASSWORD=localdev123 psql -h localhost -U espressobot -d espressobot_dev -c "SELECT archive_old_memories();"

# View orchestrator logs for duplicate call monitoring
grep "API Call" server.log | tail -20

# Monitor memory extraction quality
grep "Extracted memory\|filtered" server.log | tail -20
```

### ⚠️ Known Issues to Monitor

1. **Streaming Display**: Messages may briefly appear twice during streaming (UI rendering issue, not data)
2. **Title Auto-Refresh**: Sidebar doesn't auto-refresh when title is generated
3. **Memory Injection**: Not yet fully tested with agent responses

---
*Last Updated: August 9, 2025*
- Price monitor Python migration complete with embeddings
- SQL cartesian product issue fixed in violation statistics
- model name is fine. gpt-4.1-nano is faster, cheaper and newer than gpt-4o-mini