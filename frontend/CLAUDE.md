# Claude Development Log

## Current Architecture (July 1, 2025)

### 🎯 **System Overview**
EspressoBot uses a Shell Agency architecture with bash orchestrator as the primary system, following Unix philosophy of composable commands.

### 📁 **Current Architecture**
```
server/
├── agents/              # 3 active agents
│   ├── task-planning-agent.js
│   ├── swe-agent-connected.js  
│   └── semantic-bash-agent.js
├── data/               # Runtime data (not watched by Vite)
│   └── plans/          # Task TODO files
├── memory/             # Local memory system
│   └── data/           # SQLite database
├── tools/              # Tool implementations
└── espressobot-orchestrator.js  # Main orchestrator
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

### ✅ **Python Tools MCP Server** (NEW - July 4, 2025)
Stdio-based MCP server for direct tool execution:
- 8 tools migrated (get_product, search_products, manage_inventory_policy, etc.)
- Tool-specific context reduces prompt size
- Orchestrator executes directly (no bash agent needed)
- Auto-restart on tool changes
- Location: `/python-tools/mcp-server.py`

### ✅ **Shopify Dev MCP Tools**
Successfully integrated with SWE Agent for real-time API introspection:
- `introspect_admin_schema` - GraphQL schema exploration
- `search_dev_docs` - Documentation search
- `fetch_docs_by_path` - Specific doc retrieval
- `get_started` - API overviews

### 🔧 **Connection Pattern**
```javascript
// Connect FIRST
await shopifyDevMCP.connect();
// THEN create agent
const agent = new Agent({ mcpServers: [shopifyDevMCP] });
```

---

## Recent Fixes & Improvements

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

### Guardrails (EspressoBot v0.2)
- **Issue**: openai-agents SDK bug with `.tripwire_triggered`
- **Status**: Temporarily disabled, awaiting SDK fix
- **Workaround**: Commented out in `/python-backend/main.py:157`

---

## Quick Reference

### Running the System
```bash
# Main frontend
cd /home/pranav/espressobot/frontend
npm run dev

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

*Last Updated: July 12, 2025*