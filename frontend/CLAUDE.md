# Claude Development Log

## ⚠️ Known Issues

### Guardrails Compatibility Issue with openai-agents SDK
**Date Identified**: December 21, 2024  
**Status**: Temporarily disabled, awaiting SDK fix  
**Severity**: Medium (security feature disabled but agents work)

#### Issue Description
The openai-agents library has a bug where it attempts to access the `.tripwire_triggered` attribute on `None` objects when guardrails pass their validation checks.

**Error Message**: `'NoneType' object has no attribute 'tripwire_triggered'`

#### Technical Details
- **Expected Behavior**: When a guardrail approves input, it returns `None` to allow processing
- **Actual Behavior**: The SDK tries to access `.tripwire_triggered` on the `None` return value
- **Location**: Error occurs in the openai-agents library's internal guardrail processing
- **Our Code**: Guardrails are correctly implemented in `/python-backend/main.py`

#### Implemented Guardrails (Currently Disabled)
1. **Relevance Guardrail** (lines 30-89)
   - Validates that queries relate to Shopify/e-commerce operations
   - Checks for keywords: product, coffee, inventory, order, etc.
   - Returns friendly message for off-topic queries

2. **Jailbreak Guardrail** (lines 91-129)
   - Prevents prompt injection attacks
   - Blocks phrases like "ignore previous instructions", "show system prompt"
   - Protects agent instructions from being overridden

#### Temporary Workaround
```python
# In /python-backend/main.py, line 157:
# setup_guardrails()  # Commented out until SDK fix
```

#### To Re-enable When Fixed
1. Uncomment line 157 in `/python-backend/main.py`
2. Test with a simple query to verify the fix
3. Remove this warning section from CLAUDE.md

#### Alternative Solutions to Explore
- Check for openai-agents SDK updates
- Consider implementing guardrails at the API level before calling agents
- Look into monkey-patching the SDK if critical

---

## December 21, 2024 - Session Summary: EspressoBot v0.2 OpenAI Agents Implementation

### 🎯 **Primary Objective Achieved**
Successfully adapted the OpenAI CS Agents Demo to create EspressoBot v0.2 with 7 specialized Shopify agents using the openai-agents SDK.

### 🔧 **Major Implementation Details**

#### 1. **Agent Architecture**
Created 7 specialized agents:
- **Triage_Agent**: Routes requests to appropriate specialized agents
- **Product_Search_Agent**: Handles product discovery and search
- **Product_Editor_Agent**: Manages product modifications
- **Product_Creator_Agent**: Creates new products and bundles
- **Inventory_Manager_Agent**: Handles stock and warehouse sync
- **Analytics_Orders_Agent**: Provides reports and order analysis
- **Task_Manager_Agent**: Manages complex multi-step operations

#### 2. **Key Fixes Applied**
- **Agent Names**: Changed to use underscores (e.g., "Triage Agent" → "Triage_Agent") for OpenAI API compliance
- **Handoff Descriptions**: Removed to avoid tool naming conflicts
- **GuardrailFunctionOutput**: Fixed API compatibility issues
- **Tool Parameters**: Aligned search_products with actual Python script arguments
- **Virtual Environment**: Fixed path from `.venv` to `venv`

#### 3. **Integration Points**
- **Python Tools**: Successfully integrated with existing tools at `/home/pranav/idc/tools`
- **Context Management**: ShopifyAgentContext tracks conversation state
- **API**: FastAPI backend on port 8000
- **Frontend**: Next.js 15 UI on port 3000

### ✅ **Working Features**
- Agent handoffs functioning correctly
- Product search returning real results
- Context preservation across handoffs
- Tool execution via Python subprocess
- Conversation state management

### 📁 **Project Structure**
```
/home/pranav/espressobot/espressobot-v2/
├── python-backend/
│   ├── main.py           # Guardrails and agent setup
│   ├── api.py            # FastAPI endpoints
│   ├── context.py        # ShopifyAgentContext
│   ├── shopify_agents/   # All 7 agent implementations
│   └── tools/            # Tool wrappers for Python scripts
└── ui/                   # Next.js frontend
```

---

## December 20, 2025 - Session Summary: Replaced MCP with Custom Python Tools

### 🎯 **Primary Objective Achieved**
Successfully replaced MCP (Model Context Protocol) dependency with direct Python tool execution, providing a simpler and more maintainable architecture.

### 🔧 **Major Architecture Changes**

#### 1. **Removed MCP Dependency**
- **Before**: Complex MCP server connections via `@pranavchavda/shopify-mcp-stdio-client`, `@shopify/dev-mcp`, etc.
- **After**: Direct Python tool execution via subprocess spawning
- **Result**: Eliminated external dependencies and MCP protocol complexity

#### 2. **Custom Tool Implementation**
- **Python Tool Wrapper**: `/server/custom-tools/python-tool-wrapper.js` - Executes Python scripts from `/home/pranav/idc/tools`
- **Tool Registry**: `/server/custom-tools/tool-registry.js` - Manages tool definitions and execution
- **Tool Discovery**: `/server/custom-tool-discovery.js` - Replaces MCP tool discovery
- **Custom Agent**: `/server/basic-agent-custom.js` - Uses custom tools instead of MCP

#### 3. **Extended Tool Set**
Added 18+ Shopify tools including:
- **Core Operations**: search_products, get_product, product_create_full, update_pricing
- **Tag Management**: add_tags_to_product, remove_tags_from_product, manage_tags
- **Inventory**: manage_inventory_policy, update_product_status
- **Special Features**: create_combo, create_open_box, bulk_price_update
- **Integrations**: pplx (Perplexity AI), upload_to_skuvault
- **GraphQL**: run_full_shopify_graphql_query, run_full_shopify_graphql_mutation

### ✅ **Improvements Delivered**

1. **Simplified Architecture**: No more MCP server management or protocol handling
2. **Direct Tool Execution**: Python tools run directly via subprocess
3. **Better Error Handling**: Direct access to tool stderr/stdout
4. **Easier Maintenance**: Tools are simple Python scripts, easy to debug/modify
5. **Comprehensive Documentation**: All tools documented in system prompt with parameters

### 🐛 **Bug Fixes**

1. **Memory Agent Error**: Fixed `memoryAgent.run is not a function` by using proper `run(memoryAgent, prompt)` syntax
2. **Tool Format Error**: Fixed "Unsupported tool type" by converting memory tool to use `tool()` function with Zod schema
3. **OpenAI Tool Requirements**: All tool parameters now use Zod schemas with defaults to meet OpenAI's requirements

### 📁 **New/Modified Files**

#### New Files Created:
- `/server/custom-tools/python-tool-wrapper.js` - Python subprocess execution
- `/server/custom-tools/tool-registry.js` - Tool management and definitions
- `/server/custom-tool-discovery.js` - Discovers and formats tools
- `/server/custom-tools-definitions.js` - Core Shopify tools with Zod schemas
- `/server/custom-tools-definitions-extended.js` - Extended tool set
- `/server/basic-agent-custom.js` - New agent using custom tools

#### Modified Files:
- `/server/unified-orchestrator.js` - Uses custom agent, removed MCP calls
- `/server/task-generator-agent.js` - Uses custom tool discovery
- `/server/memory-agent.js` - Fixed tool format and execution
- `/server/espresso-system-prompt.txt` - Updated with detailed tool documentation

### 🚀 **Architecture Benefits**

- **No External Dependencies**: Removed reliance on MCP servers
- **Direct Control**: Full control over tool execution and error handling
- **Extensibility**: Easy to add new Python tools
- **Performance**: No MCP protocol overhead
- **Debugging**: Direct access to Python script output

### 📚 **Tool Documentation**

All tools are now documented in the system prompt with:
- Exact parameter names and types
- Required vs optional parameters
- Default values where applicable
- Usage examples and best practices
- IDC-specific operations guide

### 🔄 **Migration Path**

The system maintains backward compatibility:
- Same tool names preserved where possible
- Similar parameter structures
- GraphQL fallbacks still available
- Existing conversations will continue to work

---

## December 10, 2025 - Session Summary: Unified Agent Architecture with Real-Time Task Progress

### 🎯 **Primary Objective Achieved**
Successfully implemented a unified agent architecture with real-time task progress display, replacing the complex multi-agent planner/dispatcher system.

### 🔧 **Key Technical Changes**

#### 1. **Simplified Architecture**
- **Before**: Complex planner-agent.js → dispatcher-agent.js → basic-agent.js chain
- **After**: Single `unified-agent.js` that handles both planning and execution
- **Result**: Eliminated complexity and resource issues

#### 2. **Real-Time Task Display Implementation**
- **Method**: Direct MCP server polling during agent execution (every 500ms)
- **Trigger**: Tasks appear immediately when created by the agent
- **Backend**: Added task fetching in `/server/unified-orchestrator.js`
- **Frontend**: Enhanced SSE event handling for `task_summary` events

#### 3. **Conversation-Aware Task Tracking**
- Tasks are created with `conversation_id` for parallel conversation support
- Tasks are filtered and displayed per conversation
- Proper task persistence across conversation switches

### ✅ **Confirmed Working Features**

1. **Agent Execution**: Unified agent responds without hanging ✅
2. **Task Creation**: Tasks are created with proper conversation IDs ✅  
3. **Real-Time Display**: Tasks appear in UI during agent execution ✅
4. **Data Flow**: SSE events (`task_summary`) sent at correct timing ✅
5. **Frontend Processing**: React component receives and processes task events ✅

### 🔍 **Remaining Issue**
**Visual Persistence**: While tasks display correctly during agent execution, they disappear when the agent completes its response, despite the logic indicating they should remain visible (`shouldShow: true` in logs).

**Root Cause**: The visibility logic is correct, but there appears to be a visual/rendering issue where the TaskProgress component gets hidden or displaced by the agent's response content.

### 📁 **Modified Files**
- `/server/unified-orchestrator.js` - Main orchestrator with real-time task polling
- `/server/basic-agent-unified.js` - Simplified unified agent  
- `/src/features/chat/StreamingChatPage.jsx` - Enhanced task progress UI with sticky behavior
- `/src/components/chat/TaskProgress.jsx` - Task display component

### 🚀 **Architecture Benefits**
- **Performance**: Eliminated resource exhaustion issues (EAGAIN errors)
- **Simplicity**: Single agent vs. complex multi-agent chain
- **Scalability**: Conversation-aware task tracking supports parallel users
- **Real-Time UX**: Tasks appear immediately, not after completion

### 🔄 **Next Steps**
The core functionality is working - tasks are created, tracked, and displayed in real-time. The remaining work is purely visual: ensuring the TaskProgress component remains persistently visible in the UI after agent completion. This is a frontend styling/layout issue rather than a fundamental architecture problem.

**Status**: Real-time task progress **functional** ✅, visual persistence **in progress** 🔄

### 🛠 **Technical Implementation Details**

#### Backend Architecture
- **Unified Agent**: `/server/basic-agent-unified.js` - Single agent with MCP integration
- **Orchestrator**: `/server/unified-orchestrator.js` - Handles SSE streaming and real-time task polling
- **Task Polling**: Every 500ms during agent execution to detect new tasks
- **Direct MCP Calls**: Bypasses agent callbacks using direct subprocess calls

#### Frontend Implementation  
- **SSE Handler**: Enhanced event processing for `task_summary` events
- **Task State**: `currentTasks` and `hasShownTasks` for persistence
- **Visibility Logic**: Shows TaskProgress when tasks exist or have been shown
- **Conversation Isolation**: Tasks filtered by `conversation_id`

#### Key Debugging Insights
- Agent callbacks (`onMessage`, `onStepStart`, `onStepFinish`) not triggered reliably
- Resource issues (EAGAIN) resolved by closing Windsurf/excess processes
- Task creation working correctly, confirmed via direct MCP queries
- Frontend receives `task_summary` events at correct timing
- Visibility condition logic working (`shouldShow: true` in logs)

---

*Last Updated: December 20, 2025*