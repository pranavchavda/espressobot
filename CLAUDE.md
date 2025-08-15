# EspressoBot - E-Commerce Business Management System

## System Overview

**EspressoBot is a comprehensive AI-powered e-commerce business management platform**, not just a product search tool. It orchestrates multiple specialized agents to help manage all aspects of running an online store.

### Core Capabilities:
- **Product Management**: Search, create, update products; manage pricing, inventory, variants
- **Order & Sales Analytics**: Track sales, revenue, customer metrics
- **Inventory Management**: SkuVault integration, kit management, stock tracking
- **Customer Communication**: Yotpo review requests, email management via Gmail
- **Business Operations**: Google Workspace (Calendar, Tasks, Drive), GA4 analytics
- **Marketing & Pricing**: MAP sales management, competitor price monitoring, bundle creation
- **Media & Content**: Image management, metafield updates, feature management
- **Integrations**: Direct GraphQL access, webhook management, third-party services

### Available Agents:
- `products`: Product search, details, inventory
- `product_mgmt`: Product creation, updates, variants
- `pricing`: Price updates, bulk pricing, MAP sales
- `orders`: Order analytics, sales reports, revenue tracking
- `media`: Image management, uploads, optimization
- `inventory`: SkuVault sync, kit management, stock control
- `sales`: MAP sales, bundle creation, promotions
- `integrations`: Yotpo reviews, external services
- `google_workspace`: Gmail, Calendar, Drive, Tasks
- `ga4_analytics`: Website traffic, user behavior, conversions
- `graphql`: Direct Shopify API access
- `utility`: General research, calculations

## Development Notes

- Use context7 and/or deepwiki to ascertain what langgraph wants, we are using the latest versions, and they won't align with your training data pre-knowledge-cutoff
- **IMPORTANT RULE**: Always use LLM intelligence for routing decisions. Never resort to programmatic/keyword-based fallbacks. When there's a choice between intelligence-based and programmatic approaches, always choose intelligence. The system should rely on the LLM's reasoning capabilities, not hard-coded heuristics.

## System Status (August 9, 2025)

### ✅ Memory System v2 - Quality & Decay Implementation (August 15, 2025)

#### Memory Extraction Improvements:
1. **Better Quality Filtering**
   - Refined extraction prompts to focus on long-term value
   - Added ephemerality detection (filters task-specific memories)
   - Confidence scoring (filters < 0.3 confidence)
   - Result: ~70% reduction in low-quality memories expected

2. **Langextract Integration - WORKING** ✅
   - Successfully integrated langextract for structured memory extraction
   - Using gpt-4.1-mini model (same as context compression)
   - Extracts 4-8 high-quality memories per conversation
   - Fallback to GPT-4.1-nano if langextract fails
   - All memories tagged with `extraction_method: "langextract"`
   - Handles markdown-wrapped JSON responses if needed

3. **Memory Decay System**
   - Time-based decay with category-specific rates
   - Usage tracking (access_count, last_accessed_at)
   - Usefulness scoring with feedback loop
   - Automatic archival of old/unused memories

4. **Database Enhancements**
   - Added 10 new tracking columns to memories table
   - Created calculate_effective_importance() function
   - Added performance indexes for better query speed
   - Archive status for memory lifecycle management

5. **Feedback Loop Implementation**
   - Tracks which memories influenced responses
   - Updates usefulness scores based on usage
   - Analytics for memory health monitoring
   - Memory verification system for quality control

#### Memory Management UI Fixes (August 15, 2025):
- ✅ **Bulk delete fixed** - Removed integer conversion for UUID strings
- ✅ **Search working** - Lowered similarity threshold to 0.3, fixed response parsing
- ✅ **Pagination added** - 20 memories per page with Previous/Next navigation
- ✅ **Category filter fixed** - Consolidated useEffects to prevent race conditions
- ✅ **"Select all on page" checkbox** - Added for easier bulk operations
- ✅ **Navigation fixed** - "New" button now navigates to "/" instead of "/chat"

#### Next Steps for Memory System:
- Refine extraction prompts to reduce arbitrary extractions from assistant responses
- Add stricter filtering to prevent speculation extraction
- Improve extraction examples for better guidance
- Test memory influence on agent responses

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

## Previous System Status (August 9, 2025)

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

### ✅ LangSmith Tracing Integration (August 9, 2025)

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

### 🔴 CRITICAL: A2A Orchestration Async/Sync Mismatch (August 12, 2025)

#### Current State:
- **Single-agent requests**: Working perfectly ✅
- **Compound requests** (e.g., "sales AND traffic"): Failing with sync/async errors ❌
- **Root Issue**: Fundamental architectural mismatch between LangGraph (expects sync) and our async agents

#### What We Fixed:
1. ✅ **Media agent tool result extraction** - Agent wasn't capturing React tool execution results
2. ✅ **Removed keyword-based routing fallbacks** - Eliminated the code that checked for agent names in responses as a fallback
3. ✅ **Improved LLM routing prompt** - Made the routing prompt clearer about GA4 handling traffic/analytics (not keyword-based, just better instructions)
4. ✅ **State persistence** - Fixed agents_used_this_turn tracking across nodes

#### What Failed (Don't Try Again):
1. ❌ **Simple sync wrappers** - `def sync_wrapper(state): return agent(state)` - Doesn't work with async
2. ❌ **asyncio.run() in wrappers** - Fails with "cannot be called from running event loop"
3. ❌ **ThreadPoolExecutor with asyncio.run** - Still hits event loop conflicts
4. ❌ **nest_asyncio** - Doesn't solve the fundamental sync/async mismatch
5. ❌ **Switching to astream()** - LangGraph still needs sync node functions even with async streaming

#### Key Learnings:
- LangGraph's StateGraph fundamentally expects synchronous node functions
- FastAPI runs in an async context, creating event loop conflicts
- The user's question "why is it so complex?" highlights a valid architectural concern
- The desired pattern is: User → Orchestrator → Agent1 → Orchestrator → Agent2 → Orchestrator → User

#### Potential Solutions to Try:

**Option 1: Full Sync Conversion** (Most Reliable)
```python
# Convert all agents to synchronous
# Use sync HTTP clients and sync LLM calls
# Matches LangGraph's expectations perfectly
```

**Option 2: Custom Orchestration** (Simplest)
```python
# Skip LangGraph entirely
# Implement simple async orchestration:
async def orchestrate(message):
    routing = await get_routing(message)
    results = []
    for agent in routing.agents:
        result = await agent.process(message, context=results)
        results.append(result)
    return synthesize(results)
```

**Option 3: Hybrid Approach** (Current Attempt)
```python
# Keep async agents but provide sync interfaces
# Use concurrent.futures properly isolated
# Attach both sync and async versions to nodes
```

**Option 4: Different Framework**
- Consider LangFlow, Temporal, or custom async-first orchestration
- User seems open to simpler approaches based on feedback

#### Test Commands:
```bash
# Test compound request (currently failing)
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "check total sales today and website traffic today"}'

# Test single agent (working)
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message": "check total sales today"}'
```

#### Next Session Action Plan:
1. **First**: Try Option 2 (Custom Orchestration) - Simplest, async-native
2. **If needed**: Try Option 1 (Full Sync) - Most compatible with LangGraph
3. **Last resort**: Try Option 4 (Different framework)

### ⚠️ Known Issues to Monitor

1. **Streaming Display**: Messages may briefly appear twice during streaming (UI rendering issue, not data)
2. **Title Auto-Refresh**: Sidebar doesn't auto-refresh when title is generated
3. **Memory Injection**: Not yet fully tested with agent responses
4. **A2A Orchestration**: Compound requests failing due to sync/async mismatch

---

## Frontend System Status

### ✅ **Memory Management UI** (August 2025)
- **Location**: `/admin/memory` - comprehensive memory management page
- **Features**: Dashboard, semantic search, bulk operations, import/export
- **Extraction Process**: GPT-5-mini analyzes conversations after completion
- **Categories**: preferences, facts, problems, solutions, products, interactions, general
- **Deduplication**: 4-layer system (hash, fuzzy, key phrases, semantic)

### 🔧 **Known Frontend Issues**
- **Streaming Display Bug**: Messages briefly appear twice during streaming
- **Title Auto-Refresh**: Sidebar doesn't auto-refresh when title is generated
- Both issues are UI rendering problems, not data storage issues

### 📁 **Frontend Architecture**
```
frontend/
├── src/
│   ├── features/chat/       # Main chat interface
│   ├── pages/               # Admin pages, price monitor
│   └── hooks/               # LangGraph backend integration
├── server/                  # Node.js backend (deprecated)
│   ├── agents/             # Old agent implementations
│   └── memory/             # SQLite memory system
└── python-tools/           # MCP servers for Shopify
```

---
*Last Updated: August 15, 2025*
- Langextract successfully integrated for memory extraction with gpt-4.1-mini
- Memory Management UI fully functional with all fixes applied
- Bulk delete, search, pagination, and filters all working
- 15+ memories successfully extracted via langextract