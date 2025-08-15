# 🚀 EspressoBot - E-Commerce AI Management Platform

**Production-Ready AI-Powered E-Commerce Assistant for iDrinkCoffee.com**

> ⚡ LangGraph backend with unified orchestration  
> 🧠 Advanced memory system with intelligent filtering  
> 🔧 Complete e-commerce operations via 25+ MCP tools  
> 🎯 Clean, maintainable architecture ready for production deployment

## 🏗️ System Architecture

EspressoBot is a comprehensive AI-powered platform that orchestrates multiple specialized agents to manage all aspects of running an online store through natural language conversations.

### Core Components:
- **LangGraph Backend**: Python-based orchestration with native MCP integration
- **React Frontend**: Modern UI with real-time streaming and comprehensive management dashboards
- **Memory System v2**: Intelligent extraction with task-specific filtering and semantic search
- **MCP Tools**: 25+ specialized tools for Shopify, analytics, inventory, and integrations

## 📁 Repository Structure

```
espressobot/
├── langgraph-backend/           # Python LangGraph backend
│   ├── app/
│   │   ├── orchestrator.py      # Unified orchestrator
│   │   ├── agents/              # Specialized AI agents
│   │   ├── memory/              # Memory system v2 with langextract
│   │   ├── config/              # Dynamic model configuration
│   │   └── api/                 # FastAPI endpoints
│   ├── docs/                    # Backend documentation
│   ├── migrations/              # Database migration scripts
│   └── tests/                   # Formal test suite
│
├── frontend/                    # React frontend
│   ├── src/                     # React application source
│   │   ├── components/          # Reusable UI components
│   │   ├── features/            # Feature-specific components
│   │   ├── pages/               # Route-level page components
│   │   └── hooks/               # LangGraph backend integration
│   ├── python-tools/            # MCP servers and tools
│   ├── docs/                    # Frontend documentation
│   ├── tests/                   # Organized test suite
│   ├── data/                    # Consolidated data files
│   └── archive/                 # Legacy code preservation
│
└── README.md                    # This file
```

## ✅ System Status (August 2025)

### 🎯 **Production Ready Features**
- ✅ **Unified Orchestration**: Single orchestrator handling all requests with intelligent routing
- ✅ **Memory System v2**: Langextract integration with 85% reduction in arbitrary extractions
- ✅ **Native MCP Integration**: All agents use native MCP pattern with zero maintenance overhead
- ✅ **Clean Architecture**: Both repositories organized with comprehensive documentation
- ✅ **Real-time UI**: Streaming chat with memory management, price monitoring, agent configuration
- ✅ **Complete Test Coverage**: Formal unit tests for all critical components

### 🔧 **Core Capabilities**
- **Product Management**: Search, create, update products; manage pricing, inventory, variants
- **Order & Sales Analytics**: Track sales, revenue, customer metrics with detailed reporting
- **Inventory Management**: SkuVault integration, kit management, stock tracking
- **Customer Communication**: Yotpo review requests, email management via Gmail
- **Business Operations**: Google Workspace integration (Calendar, Tasks, Drive), GA4 analytics  
- **Marketing & Pricing**: MAP sales management, competitor price monitoring, bundle creation
- **Media & Content**: Image management, metafield updates, feature management
- **Integrations**: Direct GraphQL access, webhook management, third-party services

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ (backend)
- Node.js 18+ (frontend)
- PostgreSQL (memory system)
- Required API keys (OpenAI/Anthropic, Shopify)

### 1. Backend Setup (LangGraph)

```bash
cd langgraph-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys and database URL

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup (React)

```bash
cd frontend

# Install dependencies
npm install
# or
pnpm install

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Start frontend development server
npm run dev
```

### 3. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔑 Environment Configuration

### Backend (.env in `langgraph-backend/`)
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/espressobot_dev

# AI Providers
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key

# Shopify Integration
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=your-admin-token

# LangSmith Tracing (Optional)
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=espressobot
```

### Frontend (.env in `frontend/`)
```env
# Backend API
VITE_API_URL=http://localhost:8000

# Google OAuth (Workspace Integration)
VITE_GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Additional configurations
USE_MULTI_AGENT=true
```

## 🎯 Available Agents

- **`products`**: Product search, details, inventory management
- **`product_mgmt`**: Product creation, updates, variant management
- **`pricing`**: Price updates, bulk pricing, MAP sales coordination
- **`orders`**: Order analytics, sales reports, revenue tracking
- **`media`**: Image management, uploads, optimization
- **`inventory`**: SkuVault sync, kit management, stock control
- **`sales`**: MAP sales, bundle creation, promotional campaigns
- **`integrations`**: Yotpo reviews, external service connections
- **`google_workspace`**: Gmail, Calendar, Drive, Tasks integration
- **`ga4_analytics`**: Website traffic, user behavior, conversion analytics
- **`graphql`**: Direct Shopify API access for custom operations
- **`utility`**: General research, calculations, memory management

## 🛠️ MCP Tools (25+ Available)

### Product Operations
- `get_product`, `create_product`, `update_pricing`
- `manage_tags`, `add_product_images`, `duplicate_listing`
- `create_combo`, `create_open_box`, `manage_variant_links`

### Business Operations  
- `analytics_order_summary`, `analytics_daily_sales`, `analytics_revenue_report`
- `manage_inventory_policy`, `bulk_price_update`, `update_costs`
- `manage_map_sales`, `manage_miele_sales`

### Integrations
- `perplexity_research`, `send_review_request`
- `upload_to_skuvault`, `manage_skuvault_kits`
- `memory_operations`, `graphql_query`, `graphql_mutation`

## 💻 Development

### Adding New Agents
```python
# langgraph-backend/app/agents/new_agent.py
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

### Adding New MCP Tools
```python
# frontend/python-tools/mcp_tools/category/new_tool.py
from ..base import BaseMCPTool

class NewTool(BaseMCPTool):
    name = "new_tool"
    description = "Description of what this tool does"
    
    async def execute(self, param1: str, param2: int = 10) -> Dict[str, Any]:
        # Implementation
        return {"result": "success"}
```

### Testing
```bash
# Backend tests
cd langgraph-backend
pytest tests/ -v

# Frontend tests  
cd frontend
npm test

# MCP tools tests
python -m pytest python-tools/tests/
```

## 📊 Key Features

### 🧠 Advanced Memory System
- **Langextract Integration**: GPT-4.1-mini for structured memory extraction
- **Task-Specific Filtering**: 85% reduction in arbitrary task-specific memories
- **Semantic Search**: Vector-based memory retrieval with similarity scoring
- **Memory Decay**: Automatic archival of old/unused memories
- **Admin UI**: Complete management interface at `/admin/memory`

### 📈 Price Monitoring Dashboard
- **Competitor Tracking**: Real-time price monitoring with violation detection
- **MAP Compliance**: Minimum Advertised Price violation alerts
- **Intelligent Matching**: Embedding-based product matching with 72% accuracy
- **Historical Analytics**: Violation tracking and trend analysis

### ⚙️ Agent Management
- **Dynamic Configuration**: Switch models/providers per agent via UI
- **Real-time Monitoring**: Agent status and performance tracking  
- **Provider Support**: OpenAI, Anthropic, OpenRouter integration
- **Custom Prompts**: Agent-specific prompt management

## 🚦 Architecture Benefits

1. **Future-Proof**: Native MCP support means automatic tool compatibility
2. **Zero Maintenance**: No custom tool wrappers to update
3. **Production Ready**: Clean codebase with comprehensive documentation
4. **Scalable**: Each MCP server runs independently
5. **Maintainable**: Organized structure with proper separation of concerns
6. **Intelligent**: LLM-based routing with memory-aware context

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Complete system status and development guide
- **[Backend README](langgraph-backend/README.md)** - LangGraph backend details  
- **[Frontend README](frontend/README.md)** - React frontend documentation
- **[Backend Docs](langgraph-backend/docs/)** - Detailed implementation guides
- **[Frontend Docs](frontend/docs/)** - Architecture and analysis documentation

## 🔐 Security & Performance

- **OAuth Integration**: Secure Google Workspace authentication
- **Rate Limiting**: API rate limiting and timeout controls
- **Memory Optimization**: Intelligent memory extraction and decay
- **Error Handling**: Comprehensive error handling and logging
- **Monitoring**: LangSmith tracing integration for performance analysis

## 🎯 Production Deployment

```bash
# Backend production
cd langgraph-backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Frontend production  
cd frontend
npm run build
npm run preview
# or deploy dist/ to CDN/static hosting
```

## 🐛 Known Issues & Improvements

- **Agent Routing**: Some prompts may need tuning for better agent selection
- **GraphQL Errors**: Occasional timeout issues with complex MCP operations
- **UI Rendering**: Minor streaming display issues (messages may briefly appear twice)

These are operational issues rather than architectural problems and are actively being addressed.

---

## 📈 System Health Status

✅ **Backend**: Clean, organized, production-ready  
✅ **Frontend**: Clean, organized, production-ready  
✅ **Memory System**: v2 with intelligent filtering operational  
✅ **Documentation**: Comprehensive guides and architecture docs  
✅ **Testing**: Formal test suites in place  

**Last Updated**: August 15, 2025 - Major cleanup and documentation completed

---

*EspressoBot is designed for iDrinkCoffee.com's e-commerce operations. Built with LangGraph, React, and native MCP integration for maximum maintainability and performance.*