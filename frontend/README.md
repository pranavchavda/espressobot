# 🎯 EspressoBot Frontend

**Production-Ready React Frontend with Native Backend Integration**

> ⚡ Clean, organized architecture ready for production deployment  
> 🧠 Advanced memory management UI with semantic search  
> 🔧 Complete price monitoring and analytics dashboard  
> 🎯 Modern React 18+ with Vite build system

## 🏗️ Architecture Overview

The frontend provides a comprehensive interface for the EspressoBot e-commerce management platform, with direct integration to the LangGraph backend via REST APIs and Server-Sent Events (SSE) for real-time updates.

### Core Features:
- **Chat Interface**: Real-time streaming chat with agent orchestration
- **Memory Management**: Advanced UI for semantic memory search and organization  
- **Price Monitoring**: Complete dashboard for competitor pricing and MAP violations
- **Agent Management**: Dynamic configuration of AI agents and models
- **Google Workspace Integration**: OAuth flow and workspace connectivity
- **Analytics Dashboard**: Business intelligence and sales reporting

## 📁 Clean Directory Structure (August 2025)

```
frontend/
├── src/                          # React application source
│   ├── components/               # Reusable UI components
│   │   ├── chat/                # Chat-specific components
│   │   ├── common/              # Shared UI components
│   │   ├── memory/              # Memory management UI
│   │   └── ui/                  # Base UI primitives
│   ├── features/                # Feature-specific components
│   │   ├── agents/              # Agent management interfaces
│   │   ├── auth/                # Authentication components
│   │   ├── chat/                # Main chat feature
│   │   └── prompt-library/      # Prompt management
│   ├── pages/                   # Route-level page components
│   │   └── price-monitor/       # Price monitoring dashboard
│   ├── hooks/                   # Custom React hooks
│   └── utils/                   # Utility functions
├── python-tools/                # MCP servers and tools
│   ├── mcp_tools/              # Organized tool modules
│   │   ├── analytics/          # Order and sales analytics
│   │   ├── features/           # Product features management
│   │   ├── inventory/          # Stock and inventory tools
│   │   ├── media/              # Image and media management
│   │   ├── memory/             # Memory system operations
│   │   ├── pricing/            # Price management tools
│   │   ├── products/           # Product CRUD operations
│   │   ├── research/           # Perplexity AI research
│   │   ├── sales/              # MAP sales and promotions
│   │   ├── skuvault/           # SkuVault inventory integration
│   │   └── store/              # Store management
│   └── mcp-*-server.py         # Individual MCP servers
├── docs/                        # Organized documentation
│   ├── analysis/               # Architecture and analysis docs
│   └── implementation/         # Implementation guides
├── data/                        # Organized data files
│   └── price-monitor/          # Price monitoring datasets
├── tests/                       # Organized test suite
│   ├── integration/            # Integration tests
│   ├── unit/                   # Unit tests
│   ├── api/                    # API tests
│   ├── ui/                     # UI tests
│   └── tools/                  # Tool-specific tests
├── scripts/                     # Utility scripts
│   └── development/            # Development-specific scripts
├── archive/                     # Archived legacy code
│   └── legacy-nodejs-backend/  # Obsolete Node.js backend
├── static/                      # Static assets
├── prisma/                      # Database schema and migrations
└── public/                      # Public static files
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ (use latest stable)
- Python 3.11+ (for MCP servers)
- PostgreSQL database (for memory system)

### Installation

```bash
# Install dependencies
npm install
# or
pnpm install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start development server
npm run dev
```

### Environment Variables

Create a `.env` file:

```env
# Backend API
VITE_API_URL=http://localhost:8000

# Google OAuth (for workspace integration)
VITE_GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Database (for local development)
DATABASE_URL=postgresql://username:password@localhost:5432/espressobot_dev

# Shopify Integration
SHOPIFY_STORE_DOMAIN=your-store.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=your-admin-token

# OpenAI/Anthropic (for AI features)
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

## 🎯 Key Features

### 💬 Streaming Chat Interface
- Real-time SSE streaming from LangGraph backend
- Multi-agent orchestration with status indicators
- Message history and conversation management
- Image upload support for visual queries

### 🧠 Advanced Memory Management
- Semantic search across extracted memories
- Category-based organization (facts, preferences, products, etc.)
- Bulk operations with smart filtering
- Memory quality scoring and decay system
- Import/export capabilities

### 📊 Price Monitoring Dashboard
- Competitor price tracking and violation detection
- MAP (Minimum Advertised Price) compliance monitoring
- Intelligent product matching with embeddings
- Historical violation tracking and analytics
- Automated alert system

### ⚙️ Agent Management
- Dynamic agent configuration interface
- Model provider switching (OpenAI, Anthropic, OpenRouter)
- Real-time agent status monitoring
- Custom prompt management

### 🔐 Google Workspace Integration
- OAuth 2.0 authentication flow
- Gmail, Calendar, Drive, Tasks integration
- Secure token management with refresh handling
- Role-based access control

## 📦 Production Build

```bash
# Build for production
npm run build

# Preview production build locally
npm run preview

# Deploy to production
npm run build:prod
```

## 🧪 Testing

```bash
# Run all tests
npm test

# Run integration tests
npm run test:integration

# Run specific test category
npm run test:unit
npm run test:api
```

## 📡 Backend Integration

The frontend integrates with the LangGraph backend via:

- **REST API**: Standard CRUD operations at `http://localhost:8000/api/*`
- **SSE Streaming**: Real-time chat at `http://localhost:8000/api/agent/sse`
- **Memory API**: Semantic memory operations at `http://localhost:8000/api/memory/*`
- **Agent Management**: Dynamic agent configuration at `http://localhost:8000/api/agents/*`

## 🛠️ MCP Tools Integration

The `python-tools/` directory contains MCP (Model Context Protocol) servers that provide specialized capabilities:

### Available MCP Servers:
- **Products**: Product search, creation, updates, variants
- **Pricing**: Price management, bulk updates, MAP sales
- **Inventory**: Stock management, SkuVault integration
- **Media**: Image management and optimization
- **Orders**: Sales analytics, revenue reporting
- **Features**: Product features and metafields
- **Integrations**: External service connections (Yotpo, SkuVault)

### Running MCP Servers:
```bash
# Start all MCP servers
./run-mcp-server.sh

# Start specific server
python3 python-tools/mcp-products-server.py
```

## 📊 Performance Optimizations

### Built-in Optimizations:
- ⚡ **Vite Build System**: Lightning-fast development and builds
- 📦 **Code Splitting**: Automatic route-based code splitting
- 🗜️ **Tree Shaking**: Eliminates unused code
- 🎯 **Lazy Loading**: Components and routes loaded on demand
- 💾 **Memory Caching**: Intelligent memory search caching
- 🔄 **SSE Connection Pooling**: Efficient real-time updates

### Monitoring:
```bash
# Bundle size analysis
npm run analyze

# Performance audit
npm run lighthouse
```

## 🔒 Security Features

- 🔐 **OAuth 2.0 Integration**: Secure Google authentication
- 🛡️ **CORS Configuration**: Proper cross-origin security
- 🔑 **Token Management**: Secure token storage and refresh
- 📝 **Input Validation**: Client and server-side validation
- 🚫 **XSS Prevention**: React's built-in XSS protection

## 🚦 Current Status (August 2025)

- ✅ **Frontend Architecture**: COMPLETE - Clean, organized structure
- ✅ **Memory Management UI**: PRODUCTION READY - Full CRUD with semantic search
- ✅ **Price Monitor Dashboard**: PRODUCTION READY - Complete monitoring solution
- ✅ **Agent Management**: PRODUCTION READY - Dynamic configuration interface
- ✅ **Chat Interface**: PRODUCTION READY - Streaming with multi-agent support
- ✅ **Google OAuth**: CONFIGURED - Authentication flow ready for credentials
- ✅ **Documentation**: COMPLETE - Comprehensive setup and usage guides
- 🔄 **Next Steps**: Production deployment and user acceptance testing

## 📈 Analytics & Monitoring

The frontend includes comprehensive analytics for business intelligence:

### Sales Analytics:
- Daily, weekly, monthly revenue reports
- Order velocity tracking
- Customer behavior analysis
- Product performance metrics

### System Analytics:
- Memory system health monitoring
- Agent performance tracking
- API response time analysis
- Error rate monitoring

## 🎯 Why This Architecture Wins

1. **Clean Organization**: Everything in its proper place, easy to maintain
2. **Production Ready**: Optimized for deployment and scaling
3. **Modern Stack**: Latest React 18+ patterns with TypeScript support
4. **Real-time Updates**: SSE integration for live agent interactions
5. **Comprehensive Testing**: Organized test suite for reliability
6. **Security First**: OAuth integration and secure token management
7. **Business Intelligence**: Complete analytics and monitoring dashboard

---

**Remember**: This frontend is designed to work seamlessly with the LangGraph backend. Ensure the backend is running at `http://localhost:8000` for full functionality.

*Architecture cleaned and documented August 2025 for production deployment*