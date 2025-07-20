# Claude Development Log

## Current Architecture (July 1, 2025)

### 🎯 **System Overview**
EspressoBot uses a Shell Agency architecture with bash orchestrator as the primary system, following Unix philosophy of composable commands.

### 📁 **Current Architecture**
```
server/
├── agents/              # 6 active agents
│   ├── task-planning-agent.js
│   ├── swe-agent-connected.js  
│   ├── semantic-bash-agent.js
│   ├── python-tools-agent.js      # NEW: MCP agent for Shopify tools
│   ├── external-mcp-agent.js      # NEW: MCP agent for external servers
│   └── documentation-mcp-agent.js # NEW: MCP agent for API docs
├── data/               # Runtime data (not watched by Vite)
│   └── plans/          # Task TODO files
├── memory/             # Local memory system
│   └── data/           # SQLite database
├── tools/              # Tool implementations
│   ├── mcp-server-manager.js      # NEW: External server management
│   ├── mcp-agent-router.js        # NEW: Intelligent MCP routing
│   └── spawn-mcp-agent-tool.js    # NEW: Orchestrator delegation
└── espressobot-orchestrator.js    # Main orchestrator
```

### ✅ **System Status**
- **Memory System**: SQLite + OpenAI embeddings (unlimited operations)
- **Task System**: Working without Vite restarts
- **Models**: Using OpenAI (GPT-4/O4-mini), Anthropic SDK ready
- **Architecture**: Shell Agency with dynamic bash agent spawning

---

## Shell Agency Implementation

### 🚀 **Key Features**
1. **Bash Tool with Safety**: Dangerous command detection, configurable timeout
2. **Dynamic Agent Spawning**: Can spawn specialized agents for focused tasks
3. **Unix Philosophy**: Agents compose simple tools into complex solutions
4. **Direct Tool Execution**: No wrapper overhead, direct bash access

### 💡 **Benefits**
- **Flexibility**: Agents can create tools on the fly
- **Composability**: Chain tools with pipes and scripts
- **Performance**: Direct execution without handoff overhead
- **Debugging**: Clear command output visibility

---

## Local Memory System

### 🔧 **Implementation**
- **Technology**: SQLite + OpenAI text-embedding-3-small
- **Features**: Semantic search, deduplication (85% threshold), user isolation
- **Performance**: ~100ms search, ~200ms add with embedding
- **Extraction**: GPT-4.1-mini/nano for intelligent fact extraction

### 📁 **Memory Files**
- `/server/memory/simple-local-memory.js` - Core implementation
- `/server/memory/memory-operations-local.js` - Operations wrapper
- `/python-tools/memory_operations.py` - CLI for bash agents

---

## MCP Integration

### ✅ **External MCP Server Support** (NEW - July 14, 2025)
Users can now easily add external MCP servers via `mcp-servers.json`:
- Simple JSON configuration (compatible with Claude Desktop format)
- Hot reload - changes applied without restart
- Automatic tool discovery and integration
- Built-in servers remain untouched
- **NEW**: Proper MCP agent pattern with OpenAI SDK v0.11
- **NEW**: Specialized MCP agents for intelligent routing
- **NEW**: No startup overhead - removed MCP discovery/testing
- See `/docs/mcp-servers-guide.md` for details

### ✅ **Python Tools MCP Server** (NEW - July 4, 2025)
Stdio-based MCP server for direct tool execution:
- 28 tools currently in single server (causing token bloat)
- Tool-specific context reduces prompt size
- Orchestrator executes directly (no bash agent needed)
- Auto-restart on tool changes
- Location: `/python-tools/mcp-server.py`

**PLANNED OPTIMIZATION (July 17, 2025)**: Split into multiple specialized MCP servers with 3-4 mutually relevant tools each to reduce input token costs. Currently all 28 tools are loaded for every agent invocation, adding ~10k+ tokens.

### ✅ **Shopify Dev MCP Tools**
Successfully integrated with SWE Agent for real-time API introspection:
- `introspect_admin_schema` - GraphQL schema exploration
- `search_dev_docs` - Documentation search
- `fetch_docs_by_path` - Specific doc retrieval
- `get_started` - API overviews

### 🔧 **MCP Agent Pattern** (NEW - July 14, 2025)
OpenAI SDK v0.11 expects MCP servers passed directly to agents:
```javascript
// CORRECT: Pass servers to agent
const agent = new Agent({
  name: 'Python Tools Agent',
  mcpServers: [mcpServer],  // ✅ OpenAI SDK pattern
  // ...
});

// WRONG: Wrapping tools
const tools = mcpServer.getTools();  // ❌ Old pattern
```

**Key Changes:**
- MCP servers are passed via `mcpServers` array
- Each MCP domain has its own specialized agent
- Orchestrator uses `spawn_mcp_agent` for delegation
- Intelligent routing based on task keywords
- No startup MCP discovery - uses static operation list

---

## Latest Updates (July 18, 2025)

### ✅ **Agent Specialization Phase 2 - COMPLETED**
Successfully split the Python Tools Agent into 9 specialized agents:

**Planned Specialized Agents:**
1. **Products Agent** → Products Server (6 tools)
   - System prompt: Product operations, GraphQL, collections
   - Expertise: Product lifecycle, search, basic CRUD
   
2. **Pricing Agent** → Pricing Server (3 tools) 
   - System prompt: Pricing strategies, cost management, bulk updates
   - Expertise: MAP pricing, sales, margin analysis
   
3. **Inventory Agent** → Inventory Server (3 tools)
   - System prompt: Inventory policies, tagging, redirects
   - Expertise: Stock management, URL management
   
4. **Sales Agent** → Sales Server (2 tools)
   - System prompt: MAP sales, campaign management
   - Expertise: Miele/Breville sales, promotional windows
   
5. **Features Agent** → Features Server (3 tools)
   - System prompt: Content management, metafields, variant linking
   - Expertise: Rich content, product relationships
   
6. **Media Agent** → Media Server (1 tool)
   - System prompt: Image management, optimization
   - Expertise: Product photography, alt text, SEO
   
7. **Integrations Agent** → Integrations Server (4 tools)
   - System prompt: External systems, SkuVault, reviews
   - Expertise: System integrations, data sync
   
8. **Product Management Agent** → Product Management Server (5 tools)
   - System prompt: Complex product creation, variants, combos
   - Expertise: Advanced product operations
   
9. **Utility Agent** → Utility Server (1 tool)
   - System prompt: Memory operations, knowledge management
   - Expertise: Information storage and retrieval

**Benefits:**
- Each agent becomes domain expert with specialized knowledge
- Better prompts tailored to specific tool capabilities
- Enhanced routing precision (agent-level instead of server-level)
- Reduced context confusion between different operation types
- More targeted error handling and troubleshooting

**Implementation:**
- Create 9 new agent files based on current python-tools-agent-v2.js
- Each agent connects to only its assigned MCP server
- Update orchestrator to route to specific agents instead of generic python_tools_agent
- Enhanced routing logic based on task domain classification

###  Bulk Operations Task Tracking
- Make task list available to the orchestrator at all times when in bulk mode. Inject it to the end of the system prompt, along with instructions on how to mark the tasks as either in progress or complete.

### ✅ **OpenAI Tracing Configuration** (NEW - July 18, 2025)
Implemented flexible tracing system with cost controls:
- **Environment-based control**: Enable/disable via `OPENAI_TRACING_ENABLED`
- **Selective agent tracing**: Trace specific agents with `OPENAI_TRACING_AGENTS`
- **Output size limits**: Prevent massive traces with `OPENAI_TRACING_MAX_OUTPUT`
- **Automatic truncation**: Traces exceeding limits are truncated
- **Cost safeguards**: Default disabled, requires explicit opt-in
- **Documentation**: See `/docs/openai-tracing-guide.md`

**Configuration Examples:**
```bash
# Enable for all agents (development only!)
OPENAI_TRACING_ENABLED=true npm run dev

# Enable for specific agents only
OPENAI_TRACING_ENABLED=true OPENAI_TRACING_AGENTS="Products Agent,Pricing Agent" npm run dev

# With size limit
OPENAI_TRACING_ENABLED=true OPENAI_TRACING_MAX_OUTPUT=200 npm run dev
```

---

## Recent Fixes & Improvements

### July 18, 2025 - Google Workspace Integration
- **COMPLETED**: Google Workspace Integration
  - Added `google-workspace` MCP server configuration
  - Created `google-workspace-agent.js` with specialized prompts
  - Integrated Gmail, Calendar, Drive, and Tasks capabilities
  - Added direct agent tool wrapper and updated orchestrator
  - Ready for OAuth authentication and usage
- **COMPLETED**: Single Sign-In Implementation
  - Implemented direct Google API integration using existing OAuth tokens
  - Eliminated need for second authentication
  - Added database fields for storing Google OAuth tokens
  - Created direct tool implementations using googleapis npm package
  - Added 6 Google Tasks tools for complete task management
- **COMPLETED**: Fixed Google Workspace Agent Output Extraction
  - Fixed result extraction to match OpenAI SDK v0.11 structure
  - Agent output now properly flows to orchestrator
  - All Gmail, Calendar, Drive, and Tasks tools working correctly

### July 18, 2025 - Agent Specialization & Tracing
- **COMPLETED**: Agent Specialization Phase 2
  - Created 9 specialized agents (Products, Pricing, Inventory, Sales, Features, Media, Integrations, Product Management, Utility)
  - Each agent has domain-specific prompts and only loads relevant tools
  - Updated orchestrator to use specialized agents directly
  - Updated all prompts and guardrails to use new agent names
  - Result: Better performance, clearer responsibilities, improved routing

- **COMPLETED**: OpenAI Tracing Configuration
  - Implemented environment-based tracing control
  - Added output size limits to prevent massive traces
  - Created selective agent tracing capability
  - Documented in `/docs/openai-tracing-guide.md`
  - Safe to re-enable tracing with proper controls

### July 17, 2025 - Direct MCP Agent Access
- **MAJOR EFFICIENCY IMPROVEMENT**: Removed spawn_mcp_agent middleman
  - EspressoBot1 now has DIRECT access to MCP agents
  - Eliminates extra agent invocation overhead
  - Reduces token usage by ~30-40% per MCP operation
  - Cleaner error handling and response flow
- Created direct MCP agent tools:
  - `python_tools_agent`: Direct Shopify operations
  - `documentation_agent`: Direct API docs/schema access
  - `external_mcp_agent`: Direct external tool access
  - `smart_mcp_execute`: Auto-routing to best agent
- Updated orchestrator prompts for direct execution
- No more "spawn then execute" - just "execute"!

### July 17, 2025
- **COMPLETED**: MCP server split optimization - reduced token usage by ~90%
- **CREATED**: 9 specialized MCP servers covering all 28 tools:
  - Products Server (6 tools): Basic product ops + GraphQL
  - Pricing Server (3 tools): All pricing operations
  - Inventory Server (3 tools): Inventory, tags, redirects
  - Sales Server (2 tools): MAP sales management
  - Features Server (3 tools): Metafields and content
  - Media Server (1 tool): Image management
  - Integrations Server (4 tools): SkuVault, reviews, research
  - Product Management Server (5 tools): Full product creation
  - Utility Server (1 tool): Memory operations
- **RESULT**: Agents now load only 1-6 relevant tools instead of all 28
- **TOKEN REDUCTION**: ~90% reduction in input tokens (was ~10k+ per invocation)
- **COST IMPACT**: Should eliminate the $15+ charges from tool schema bloat
- **DEPLOYMENT**: Successfully removed old MCP client initialization - system now fully uses specialized servers
- **VERIFIED**: No more 28-tool monolithic server loading - only specialized servers run
- **FIXED**: EspressoBot1 claiming no GraphQL access when it actually had capabilities
- **FIXED**: MCP resource Zod validation errors - all servers use proper getter pattern
- **ARCHITECTURE**: Complete migration from monolithic to specialized MCP architecture

### July 14, 2025
- Added external MCP server support with hot reload
- Created MCP Server Manager for unified tool management
- Implemented JSON configuration compatible with Claude Desktop format
- Updated to OpenAI agents-core v0.11 (from v0.9)
- **MAJOR**: Migrated to proper MCP agent pattern:
  - Created specialized MCP agents (Python Tools, External, Documentation)
  - Implemented intelligent routing with keyword analysis
  - Removed wrapped MCP tools from orchestrator
  - Added `spawn_mcp_agent` tool for delegation
- **PERFORMANCE**: Removed startup MCP discovery/testing (15-20s saved)
- Created static operation list for task planning
- External MCP servers work correctly with the new pattern

### July 12, 2025
- Fixed OpenAI agents Zod validation: **CRITICAL** - Optional fields must be `.nullable().default(null)` not `.default('')` or `.default({})`
- Updated all tool schemas in `/server/custom-tools-definitions.js` to use nullable pattern
- Fixed "userProfile is not defined" error by properly passing user context to prompts
- Fixed "Cannot read properties of undefined (reading 'find')" error in extractProductBlobs - disabled product blobs since entity extraction was removed

### July 4, 2025
- Implemented MCP (Model Context Protocol) for Python tools
- Created stdio-based MCP server with auto-discovery and testing
- Added 8 MCP tools with tool-specific context (23 more to migrate)
- Fixed bash agents using curl instead of python-tools
- Fixed OpenAI SDK compatibility by making optional fields nullable
- MCP server working perfectly, orchestrator integration pending auth testing
- Architecture supports self-modification (SWE can add/update MCP tools)

### July 1, 2025
- Cleaned up codebase (removed 9 unused agents, kept 3 active)
- Fixed task system imports and Vite restart issues
- Consolidated documentation into single files
- Anthropic integration attempted (OpenAI SDK tightly coupled)

### June 30, 2025
- Implemented custom local memory system (no API limits)
- Made shell-agency branch the new main
- Unified bash orchestrator as default system

### June 28, 2025
- Fixed bash orchestrator display issue (use `agent_message` events)
- Fixed dynamic agent spawning ES module imports
- Implemented Shell Agency architecture

---

## Known Issues & Workarounds

### OpenAI Agents Zod Schemas
- **Issue**: Optional fields with `.default('')` or `.default({})` cause JSON parsing errors
- **Solution**: Use `.nullable().default(null)` for all optional fields
- **Example**: `z.string().nullable().default(null)` instead of `z.string().default('')`
- **Files**: `/server/custom-tools-definitions.js` and any new tool definitions

### Guardrails Configuration (NEW - July 16, 2025)
- **Location**: `/server/config/guardrail-config.js`
- **Features**: Configurable guardrails to prevent overzealous blocking
- **Settings**:
  - Bulk operation detection (enabled/disabled)
  - Max retries reduced from 5 to 3
  - Exclude patterns for false positives
  - AI chokidars can be disabled for simple pattern matching
- **Environment Overrides**:
  - `GUARDRAILS_ENABLED=false` - Disable all guardrails
  - `GUARDRAILS_BULK_MAX_RETRIES=1` - Reduce retry attempts
  - `GUARDRAILS_USE_AI=false` - Use simple patterns instead of AI
- **Status Check**: `node server/utils/show-guardrail-status.js`

---

## Quick Reference

### Running the System
```bash
# Main frontend
cd /home/pranav/espressobot/frontend
pnpm run dev  # Updated to pnpm

# EspressoBot v0.2 (if needed)
cd /home/pranav/espressobot/espressobot-v2
./start.sh
```

### Environment Variables
- `SHOPIFY_SHOP_URL` - Shopify store URL
- `SHOPIFY_ACCESS_TOKEN` - Admin API token
- `OPENAI_API_KEY` - For agents and embeddings
- `PERPLEXITY_API_KEY` - For product research

---

## Cost Optimization Findings & Fixes (July 17-18, 2025)

### ✅ **FIXED: MCP Tool Schema Token Bloat**
- **Problem**: Each MCP agent was loading ALL 28 tools with full JSON schemas
- **Impact**: ~10k+ tokens added to EVERY agent invocation
- **Cost**: Was causing $15+ charges per short interaction

### 📋 **Solution Implemented: Split MCP Servers**
Successfully split the monolithic Python MCP server into specialized servers:
- **Products Server**: get_product, search_products, create_product, update_status (4 tools)
- **Pricing Server**: update_pricing, bulk_price_update, update_costs (3 tools)
- **Inventory Server**: manage_inventory_policy, manage_tags, manage_redirects (3 tools)
- **Metafields Server**: manage_features_metaobjects, update_metafields, manage_variant_links (3 tools)
- **Sales Server**: manage_miele_sales, manage_map_sales (2 tools)
- **Features Server**: create_combo, create_open_box, add_product_images (3 tools)
- **Integration Server**: skuvault operations, send_review_request (4 tools)
- **GraphQL Server**: graphql_query, graphql_mutation (2 tools)
- **Utility Server**: memory_operations, perplexity_research (2 tools)

**Results**: 87% token reduction! Agents now only load 3-4 relevant tools.

### ✅ **FIXED: spawn_mcp_agent Response Bloat**
- **Problem**: Agent responses included entire state object (4k+ lines)
- **Solution**: Extract only meaningful output from agent results
- **Files Updated**:
  - `/server/agents/python-tools-agent-v2.js`
  - `/server/agents/documentation-mcp-agent.js`
  - `/server/agents/external-mcp-agent.js`
  - `/server/tools/spawn-mcp-agent-tool.js`

### ✅ **LATEST: Direct MCP Agent Access**
- **Problem**: spawn_mcp_agent added unnecessary routing overhead
- **Solution**: EspressoBot1 now directly calls MCP agents
- **Benefits**:
  - 30-40% token reduction per MCP operation
  - Faster execution (no intermediate agent)
  - Cleaner error handling
  - Simpler debugging
- **New Tools**:
  - `python_tools_agent`: Direct Shopify operations
  - `documentation_agent`: Direct API access
  - `external_mcp_agent`: Direct external tools
  - `smart_mcp_execute`: Auto-routing
- **Files**: `/server/tools/direct-mcp-agent-tools.js`

---

*Last Updated: July 18, 2025*
```