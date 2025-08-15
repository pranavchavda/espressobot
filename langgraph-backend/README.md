# 🚀 EspressoBot LangGraph Backend

**Production-Ready E-Commerce AI Backend**

> ⚡ Unified orchestrator with native MCP integration  
> 🧠 Advanced memory system with intelligent filtering  
> 🔧 Complete e-commerce management: products, orders, inventory, sales  
> 🎯 Clean, maintainable architecture ready for production

## 🏗️ Architecture Overview

This backend leverages **native MCP (Model Context Protocol) support** through LangChain's official `langchain-mcp-adapters` package, ensuring:
- 🔌 Direct integration with LangGraph agents
- 🔧 Automatic tool discovery and registration  
- 📦 No custom tool wrappers or maintenance overhead
- ⚡ Seamless updates as MCP protocol evolves

## 📚 Critical Documentation Strategy

### 🔍 Always Use DeepWiki First

**IMPORTANT**: Before implementing any feature or debugging any issue, **ALWAYS** consult DeepWiki for the latest information:

```
1. Check DeepWiki for current LangChain/LangGraph patterns
2. Verify MCP protocol compatibility  
3. Confirm package versions and APIs
4. Then implement
```

#### Key DeepWiki Repositories to Monitor:
- `langchain-ai/langchain` - Core LangChain functionality
- `langchain-ai/langgraph` - LangGraph patterns and agents
- `modelcontextprotocol/servers` - MCP server implementations
- `anthropic/anthropic-sdk-python` - Claude integration patterns

### Why DeepWiki is Critical:
- 📅 **Rapid Evolution**: LangChain/LangGraph APIs change frequently
- 🔄 **Protocol Updates**: MCP protocol evolves with new capabilities
- 🎯 **Best Practices**: Implementation patterns improve constantly
- ⚠️ **Deprecation Notices**: Avoid using outdated approaches

## 🎯 Simplified Architecture (August 2025)

### Single Orchestrator Pattern
- **🎪 `app/orchestrator.py`** - Unified orchestrator handling all requests
- **🔌 `app/api/chat.py`** - Single API endpoint at `/api/agent/*`
- **🧠 Memory System v2** - Intelligent extraction with task-specific filtering
- **⚙️ Agent Management** - Dynamic configuration via `/agent-management` and `/admin/agents`

### Clean File Structure
```
langgraph-backend/
├── app/
│   ├── orchestrator.py          # Single unified orchestrator
│   ├── api/chat.py             # Main chat endpoint
│   ├── agents/                 # All specialized agents
│   ├── memory/                 # Memory system with langextract
│   └── config/                 # Dynamic model configuration
├── docs/                       # Organized documentation
│   ├── setup/                  # Migration and setup guides
│   ├── integrations/           # Auth, frontend, GPT-5 docs
│   ├── memory/                 # Memory system documentation
│   └── archive/                # Obsolete documentation
├── migrations/                 # Database migration scripts
├── tests/                      # Formal unit tests
└── README.md                   # This file
```

## ✅ Current Implementation Status

### What's Been Built

#### 🎯 Native MCP Integration
- ✅ **Products Agent**: Full native MCP using `MultiServerMCPClient`
- ✅ **Automatic Tool Discovery**: Tools loaded directly from MCP servers
- ✅ **Real Shopify API**: Confirmed working with actual product data
- ✅ **Zero Custom Wrappers**: Pure native implementation
- ✅ **Conversation Memory**: Full context maintained across messages

#### Core Infrastructure  
- ✅ FastAPI backend with CORS configuration
- ✅ LangGraph 0.6.3 orchestrator with proper state management
- ✅ Native MCP support via `langchain-mcp-adapters`
- ✅ SSE endpoint for streaming responses (frontend-compatible)
- ✅ SQLite database models with async SQLAlchemy
- ✅ State management using LangGraph's TypedDict pattern
- ✅ In-memory and SQLite checkpointing support

#### Agents Status (All Native MCP ✅)
- ✅ **Products Agent**: Native MCP implementation with full conversation memory (PRODUCTION READY)
- ✅ **Pricing Agent**: Native MCP implementation with full tool access (PRODUCTION READY)
- ✅ **Inventory Agent**: Native MCP implementation with stock management tools (PRODUCTION READY)
- ✅ **Sales Agent**: Native MCP implementation with MAP sales and analytics (PRODUCTION READY)
- ✅ **Features Agent**: Native MCP implementation with metafields and metaobjects (PRODUCTION READY)
- ✅ **Media Agent**: Native MCP implementation with image management (PRODUCTION READY)
- ✅ **Integrations Agent**: Native MCP implementation with SkuVault and Yotpo (PRODUCTION READY)
- ✅ **Product Management Agent**: Native MCP implementation with full product lifecycle (PRODUCTION READY)
- ✅ **Utility Agent**: Native MCP implementation with memory and research (PRODUCTION READY)
- ✅ **GraphQL Agent**: Native MCP implementation for custom API operations (PRODUCTION READY)
- ✅ **General Agent**: Handles greetings and general conversation with context retention

#### Native MCP Pattern Used
```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# This is the actual implementation pattern we're using
client = MultiServerMCPClient({
    "products": {
        "command": "python3",
        "args": ["mcp-products-server.py"],
        "transport": "stdio"
    }
})
tools = await client.get_tools()
agent = create_react_agent(model, tools)
```

### 🔧 Important Implementation Notes

#### Conversation Memory
Both GeneralAgent and ProductsAgent now maintain full conversation context:

```python
# ✅ CORRECT: Pass full conversation history
agent_state = {"messages": messages}  # All messages from state

# ❌ WRONG: Only passing last message loses context
agent_state = {"messages": [last_message]}  # Loses previous context
```

This ensures agents can:
- Remember user names and preferences
- Understand references like "this item" from previous messages
- Maintain coherent multi-turn conversations

## Quick Start

### Prerequisites
- Python 3.11+ (use latest stable)
- MCP servers from `frontend/python-tools/`
- Environment variables (ANTHROPIC_API_KEY, SHOPIFY_*, etc.)

### Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install core dependencies
pip install -r requirements.txt

# CRITICAL: Install native MCP support
pip install langchain-mcp-adapters

# Verify installation
python -c "from langchain_mcp_adapters.client import MultiServerMCPClient; print('✅ Native MCP ready')"
```

### Running the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the run script
python run.py

# Or use make
make dev
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test files
pytest tests/test_agents.py -v
pytest tests/test_orchestrator.py -v
```

## API Endpoints

- `GET /` - Health check
- `GET /health` - Health status
- `POST /api/agent/sse` - SSE streaming chat endpoint
- `POST /api/agent/message` - Standard chat endpoint
- `GET /api/agent/agents` - List available agents
- `GET /api/conversations/` - List conversations
- `POST /api/auth/register` - Register user
- `GET /api/dashboard/stats` - Dashboard statistics

## Project Structure

```
langgraph-backend/
├── app/
│   ├── agents/           # Specialist agents
│   ├── api/             # FastAPI endpoints
│   ├── database/        # SQLAlchemy models
│   ├── state/           # LangGraph state management
│   ├── tools/           # MCP client integration
│   ├── main.py          # FastAPI application
│   └── orchestrator.py  # LangGraph orchestrator
├── tests/               # Test suite
├── requirements.txt     # Python dependencies
└── run.py              # Development server runner
```

## 🔄 Staying Current & Maintenance-Free

### Weekly Maintenance Checklist

1. **Check DeepWiki First**
   ```
   Query: "MultiServerMCPClient latest changes"
   Query: "create_react_agent API updates"
   Query: "MCP protocol 2025 updates"
   ```

2. **Verify Package Compatibility**
   ```bash
   pip list --outdated | grep -E "langchain|langgraph|mcp"
   # Only update after checking DeepWiki for breaking changes
   ```

3. **Test Critical Paths**
   ```bash
   python test_mcp.py  # Tests native MCP integration
   python cli.py       # Interactive testing
   ```

### Zero-Maintenance Principles

#### ✅ DO's
- Use `MultiServerMCPClient` directly (native support)
- Let MCP servers define tools (automatic discovery)
- Trust LangGraph's `create_react_agent` (no custom logic)
- Check DeepWiki before any changes

#### ❌ DON'Ts  
- Don't write custom tool wrappers
- Don't parse tool calls manually
- Don't implement custom protocols
- Don't assume APIs are stable - always verify

### When Things Break

1. **First**: Check DeepWiki for the component
2. **Common Fixes**:
   ```python
   # API signature changed? Check DeepWiki for new pattern
   # Example: If MultiServerMCPClient changes
   from langchain_mcp_adapters.client import MultiServerMCPClient
   # DeepWiki will have the latest usage pattern
   ```

3. **Version Pinning Strategy**:
   ```toml
   # Use >= for patch versions (safe)
   langchain-mcp-adapters >= "0.1.9"
   
   # Pin minor for stability
   langgraph ~= "0.6.3"
   ```

## Environment Variables

Create a `.env` file:

```env
ANTHROPIC_API_KEY=your_api_key_here
DATABASE_URL=sqlite+aiosqlite:///./espressobot.db
FRONTEND_URL=http://localhost:3000
MCP_TOOLS_PATH=/home/pranav/espressobot/frontend/python-tools
LOG_LEVEL=INFO
```

## Testing & Verification

### Test Native MCP Integration
```bash
# Test product search (real Shopify data)
python test_mcp.py

# Interactive testing
python cli.py
>>> Find product with SKU IDC-MBC-T-S
# Should return: iDrinkCoffee.com Me Before Coffee T-Shirt

>>> Search for Breville espresso machines  
# Should return: List of actual Breville products with inventory
```

### Verify MCP Tools Are Working
```python
# Quick verification script
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio

async def verify():
    client = MultiServerMCPClient({
        "products": {
            "command": "python3",
            "args": ["frontend/python-tools/mcp-products-server.py"],
            "transport": "stdio"
        }
    })
    tools = await client.get_tools()
    print(f"✅ Found {len(tools)} tools")
    for tool in tools:
        print(f"  - {tool.name}")

asyncio.run(verify())
```

## Adding New Agents (Native MCP Pattern)

```python
# app/agents/new_agent.py
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

class NewAgentNativeMCP:
    async def _ensure_mcp_connected(self):
        self.client = MultiServerMCPClient({
            "server_name": {
                "command": "python3",
                "args": ["path/to/mcp-server.py"],
                "transport": "stdio"
            }
        })
        self.tools = await self.client.get_tools()
        self.agent = create_react_agent(self.model, self.tools)
```

## 🚦 Current Status

- ✅ **Native MCP Integration**: COMPLETE - All agents using native MCP pattern
- ✅ **All Specialist Agents**: PRODUCTION READY with full tool access
- ✅ **General Agent**: Handles greetings and maintains conversation context
- ✅ **Backend Infrastructure**: COMPLETE with proper message routing
- ✅ **CLI Interface**: Fixed and working with proper conversation flow
- ✅ **DeepWiki Integration**: Documentation emphasizes latest patterns
- 🔄 **Next Steps**: Authentication, Google Workspace, and frontend integration

## 📊 Performance Metrics

- **MCP Connection**: < 1s startup time
- **Tool Discovery**: Automatic, no maintenance
- **Product Search**: Real-time Shopify API responses
- **Memory Usage**: Minimal - MCP servers run as separate processes
- **Maintenance**: Zero custom code to maintain

## 🎯 Why This Architecture Wins

1. **Future-Proof**: Native MCP support means automatic compatibility
2. **Zero Maintenance**: No custom tool wrappers to update
3. **Always Current**: DeepWiki ensures we use latest patterns
4. **Production Ready**: Tested with real Shopify data
5. **Scalable**: Each MCP server runs independently
6. **Natural Conversations**: Full context retention across messages
7. **Intelligent Routing**: Specialized agents for specific tasks, general agent for conversation

---

**Remember**: Always check DeepWiki first. The native MCP pattern with `MultiServerMCPClient` is the key to keeping this backend maintenance-free.