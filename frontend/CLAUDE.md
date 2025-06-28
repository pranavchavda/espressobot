# Claude Development Log

## 🚀 EspressoBot v0.2 - Native Tools Integration Complete!

### Current State (December 21, 2024)
EspressoBot v0.2 is now fully functional with:
- **7 specialized Shopify agents** using OpenAI Agents SDK
- **25+ native Python tools** imported directly (no subprocess overhead)
- **Clean architecture** based on OpenAI CS Agents Demo
- **Working agent handoffs** and context management
- **Native tool execution** for better performance and debugging

### Architecture Overview
```
/home/pranav/espressobot/espressobot-v2/
├── python-backend/
│   ├── shopify_agents/       # 7 specialized agents
│   ├── tools/                # All native Python tools
│   │   ├── shopify_tools.py  # Main wrapper with function_tool decorators
│   │   └── [25+ tool files]  # Copied from /home/pranav/idc/tools
│   ├── api.py                # FastAPI endpoints
│   ├── context.py            # ShopifyAgentContext
│   └── main.py               # Agent setup (guardrails disabled)
└── ui/                       # Next.js 15 frontend
```

### Running EspressoBot v0.2
```bash
cd /home/pranav/espressobot/espressobot-v2
./start.sh  # Starts both backend (port 8000) and frontend (port 3000)
```

### Native Tools Status
✅ **Working Tools:**
- search_products, get_product, perplexity_search
- product_create_full, create_combo, create_open_box
- update_pricing, manage_tags, update_status
- manage_inventory_policy, manage_variant_links
- run_graphql_query, run_graphql_mutation
- bulk_price_update (implemented as individual updates)

⚠️ **CLI-Only Tools** (return "not implemented" errors):
- manage_map_sales
- upload_to_skuvault

### Important Function Name Mappings
When calling tools, use these corrected function names:
- `create_combo` → calls `create_combo_listing()`
- `update_pricing` → calls `update_variant_pricing()`
- `manage_tags` → calls `manage_tags(action, identifier, tags)`
- `update_product_status` → calls `update_status(identifier, status)`
- `manage_variant_links` → calls `link_products()` or `unlink_products()`

### Testing Tools
```python
# Test native tool imports
cd /home/pranav/espressobot/espressobot-v2/python-backend
python test_native_tools.py

# Test API with native tools
python test_native_api.py
```

### Next Steps for Improvement
1. **Re-enable Guardrails**: Wait for openai-agents SDK fix for the `.tripwire_triggered` bug
2. **Implement CLI-only tools**: Convert manage_map_sales and upload_to_skuvault to native functions
3. **Add streaming responses**: Implement SSE for real-time agent responses
4. **Enhance error handling**: Add better error messages and recovery strategies
5. **Add more agents**: Consider agents for customer service, reporting, etc.
6. **Implement memory**: Add conversation persistence and context retrieval
7. **Add authentication**: Secure the API endpoints
8. **Performance monitoring**: Add logging and metrics
9. **Test coverage**: Add unit tests for all tools and agents
10. **Documentation**: Create API docs and user guides

### Common Issues & Solutions

#### Tool Function Errors
If you get errors like `module 'X' has no attribute 'Y'`:
1. Check the actual function name in the tool file: `grep "^def " /path/to/tool.py`
2. Update the function call in shopify_tools.py
3. See "Important Function Name Mappings" above

#### Environment Variables
Tools expect these environment variables:
- `SHOPIFY_SHOP_URL`: Your Shopify store URL
- `SHOPIFY_ACCESS_TOKEN`: Admin API access token
- `OPENAI_API_KEY`: For agents and Perplexity tool
- `PERPLEXITY_API_KEY`: For product research

#### Virtual Environment
Make sure the virtual environment is activated:
```bash
cd /home/pranav/espressobot/espressobot-v2/python-backend
source venv/bin/activate
```

---

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

## December 22, 2024 - Shopify Dev MCP Server Integration

### 🎯 **Objective**
Integrated the Shopify Dev MCP server to provide documentation search and schema introspection capabilities to the multi-agent system.

### 🔧 **Implementation Details**

#### 1. **Shopify Dev MCP Server Setup**
- Added `@shopify/dev-mcp` package (v1.1.0) to dependencies
- Created MCP wrapper at `/server/shopify-dev-tools/shopify-dev-mcp-wrapper.js`
- Implemented proper MCP protocol communication via subprocess
- Handles tool execution with timeout and error handling

#### 2. **Tool Registry Integration**
- Extended `tool-registry-extended.js` with generic `registerTool()` method
- Updated `custom-tool-discovery.js` to register Shopify Dev tools
- Tools now available alongside existing Python tools
- Fallback mechanism when MCP server unavailable

#### 3. **Available Shopify Dev Tools**
1. **search_dev_docs** - Search Shopify.dev documentation
2. **introspect_admin_schema** - Explore GraphQL schema types
3. **fetch_docs_by_path** - Retrieve specific documentation
4. **get_started** - Overview of Shopify APIs

#### 4. **Agent Updates**
- **Product Creation Agent**: 
  - Added schema introspection tools
  - Can verify field types before creating products
  - Example: `introspect_admin_schema({type: "ProductInput"})`
  
- **Product Update Agent**:
  - Added documentation search capabilities
  - Can lookup proper mutation formats
  - Example: `search_dev_docs({query: "productUpdate mutation"})`

#### 5. **Enhanced Agent Instructions**
Updated agent instructions with examples:
```javascript
// Product Creation Agent
- Use introspect_admin_schema to verify field types before creating products
- Use search_dev_docs when uncertain about API capabilities
- Always check schema before using new field types or mutations

// Product Update Agent  
- Use search_dev_docs to find proper mutation formats
- Use fetch_docs_by_path for specific API documentation
- Reference documentation before complex GraphQL operations
```

### 📁 **New Files Created**
- `/server/shopify-dev-tools/shopify-dev-mcp-wrapper.js` - MCP server wrapper
- `/server/shopify-dev-tools/index.js` - Tool registration helper
- `/server/test-shopify-dev-mcp.js` - Integration test suite

### 🔄 **Modified Files**
- `package.json` - Added @shopify/dev-mcp dependency
- `/server/custom-tool-discovery.js` - Integrated Shopify Dev tools
- `/server/custom-tools/tool-registry-extended.js` - Added registerTool method
- `/server/agents/product-creation-agent.js` - Added dev tools
- `/server/agents/product-update-agent.js` - Added dev tools
- `/server/agents/enhanced-instructions.js` - Added tool usage examples

### ✅ **Benefits**
1. **Better API Understanding**: Agents can introspect schema before operations
2. **Reduced Errors**: Documentation lookup prevents incorrect API usage
3. **Self-Learning**: Agents can discover new API capabilities
4. **Type Safety**: Schema introspection ensures correct field types
5. **Best Practices**: Access to official Shopify documentation

### 🚀 **Usage Examples**
```javascript
// Before creating a product, check the schema
await introspect_admin_schema({ type: "ProductInput" });

// Look up how to update metafields
await search_dev_docs({ query: "productUpdate metafields" });

// Get specific mutation documentation
await fetch_docs_by_path({ 
  path: "/api/admin-graphql/2024-10/mutations/productCreate" 
});
```

### 🔄 **Updated: Direct MCP Integration** (December 25, 2024)

Simplified to use OpenAI agents SDK's native MCP support:

```javascript
import { Agent, MCPServerStdio } from '@openai/agents';

// Create MCP server
const shopifyDevMCP = new MCPServerStdio({
  name: 'Shopify Dev Docs',
  fullCommand: 'npx -y @shopify/dev-mcp',
  cacheToolsList: true
});

// Add to agent
const agent = new Agent({
  name: 'Product_Agent',
  tools: [...customTools],
  mcpServers: [shopifyDevMCP]  // Native MCP support!
});
```

**Benefits**:
- No custom wrappers needed
- Automatic tool discovery
- Works alongside custom tools
- Built-in error handling

### 📝 **Environment Variables**
Optional configuration:
- `SHOPIFY_DEV_POLARIS=true` - Enable Polaris component docs
- `SHOPIFY_DEV_OPT_OUT_INSTRUMENTATION=true` - Disable telemetry

### 🧪 **Testing**
Run integration tests:
```bash
node test-mcp-direct.js
```

**Status**: Shopify Dev MCP integration **complete** ✅ (using native SDK support)

---

## June 28, 2025 - Enhanced Multi-Agent System with Specialized Agents

### 🎯 **Primary Objective Achieved**
Successfully updated the agentic architecture to use 9 specialized agents from `/server/agents/specialized/` with proper tool distribution and integration.

### 🔧 **Major Changes Implemented**

#### 1. **Multi-Agent Integration**
- Integrated 9 specialized agents into the enhanced orchestrator:
  - **Catalog_Query_Agent**: Product searches and lookups
  - **Product_Creation_Agent**: New products, combos, open box items
  - **Product_Update_Agent**: Pricing, tags, status modifications
  - **Inventory_Agent**: Stock management and SkuVault sync
  - **Channel_Specials_Agent**: MAP sales and vendor promotions
  - **Secure_Data_Agent**: Sensitive order/customer data access
  - **System_Health_Agent**: Diagnostics and health checks
  - **Task_Planning_Agent**: Complex multi-step request handling
  - **User_Clarification_Agent**: Ambiguous request clarification

#### 2. **Tool System Overhaul**
- Added 36 tools total (32 Shopify + 4 Shopify Dev tools)
- Converted all tools to OpenAI SDK format using Zod schemas
- Fixed parameter mapping issues throughout
- Created proper tool assignment to specialized agents

#### 3. **Critical Bug Fixes**
- **create_product.py**: Fixed GraphQL schema error with variants field
- **Tool Parameter Mapping**: Fixed mismatches (e.g., `product_type` → `type`)
- **update_pricing**: Created wrapper for identifier resolution
- **pollMarkdownInterval**: Fixed scope error in multi-agent-orchestrator.js

#### 4. **New Infrastructure**
- Created comprehensive API test suites
- Built tool execution diagnostics
- Added parameter mapping tests
- Implemented proper error handling

### ✅ **Current Working State**
- Product creation via API: **Working** ✅
- Product search functionality: **Working** ✅
- Agent handoffs: **Working** ✅
- Tool execution through agents: **Working** ✅
- Update pricing with wrapper: **Working** ✅

### 📁 **Key Files Modified/Created**
- `/server/enhanced-multi-agent-orchestrator-v2.js` - Main orchestrator
- `/server/tools/openai-tool-converter.js` - Tool format conversion
- `/server/custom-tools/tool-registry-extended.js` - Extended tool registry
- `/server/python-tools/update_pricing_wrapper.py` - Identifier resolution
- Various test files for comprehensive testing

### 🚀 **Next Steps**
1. **Complete Tool Testing**: Test remaining tools (inventory, GraphQL, channel-specific)
2. **Create More Wrappers**: Similar identifier resolution for other update tools
3. **Performance Optimization**: Monitor and optimize agent response times
4. **Error Recovery**: Implement better error handling and recovery strategies
5. **Documentation**: Update API docs with new multi-agent system

### 🐛 **Known Issues**
- Some update tools still need wrapper functions for identifier resolution
- Bulk operations need CSV file handling implementation
- Channel-specific tools (MAP sales) need thorough testing

### 💡 **Architecture Benefits**
- Clear separation of concerns with specialized agents
- Better maintainability with focused agent responsibilities
- Improved error isolation and debugging
- Scalable design for adding new agents/tools

---

*Last Updated: June 28, 2025*