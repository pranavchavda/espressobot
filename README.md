<!-- markdownlint-disable MD041 MD025 -->
# EspressoBot - Shell Agency Architecture

> A revolutionary AI-powered e-commerce assistant for iDrinkCoffee.com, featuring a "Shell Agency" architecture where agents are given direct bash access instead of wrapped tools, following Unix philosophy of composable commands.

## 🚀 Features

### Shell Agency Architecture
- **Dynamic Bash Orchestrator**: Main orchestrator that spawns specialized bash agents on demand
- **Unix Philosophy**: Agents compose simple tools into complex solutions  
- **Direct Tool Access**: Agents execute Python tools directly via bash
- **Parallel Execution**: Spawn multiple agents for independent tasks
- **Real-time Progress**: SSE streaming shows live agent actions

### Core Capabilities
- **Shopify Integration**: Full access to 30+ Shopify tools for product, inventory, and order management
- **Planning Agent**: Breaks down complex requests into structured task plans
- **SWE Agent**: Software engineering agent with MCP integration for tool creation/modification
- **Memory System**: (Currently disabled - needs redesign)
- **Google OAuth**: Authentication with workspace account support
- **Real-time Streaming**: Live updates via Server-Sent Events (SSE)
- **Task Tracking**: Visual progress indicators for multi-step operations

## Prerequisites

- **Node.js** (v22+) and **pnpm** (recommended) or **npm**
- **SQLite** (for local development) or **PostgreSQL** (for production)
- **OpenAI API Key** with access to o3-mini and gpt-4 models
- **Shopify Store** with Admin API access token
- **Google OAuth** credentials (for authentication)

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/pranavchavda/flask-shopifybot.git
   cd flask-shopifybot
   ```

2. **Set up environment variables**
   ```bash
   cd frontend
   cp .env.example .env
   ```
   
   Edit `.env` and configure:
   - `DATABASE_URL` - SQLite or PostgreSQL connection string
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `OPENAI_MODEL` - Model to use (e.g., `gpt-4o-mini`)
   - `SHOPIFY_SHOP_URL` - Your Shopify store URL
   - `SHOPIFY_ACCESS_TOKEN` - Shopify Admin API token
   - `GOOGLE_CLIENT_ID` - Google OAuth client ID
   - `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
   - `SESSION_SECRET` - Random string for session encryption

3. **Install dependencies**
   ```bash
   cd frontend
   pnpm install  # or npm install
   ```

4. **Set up the database**
   ```bash
   npx prisma migrate dev --name init
   npx prisma generate
   ```

5. **Run the development server**
   ```bash
   pnpm dev  # or npm run dev
   ```

6. **Access the application**
   - Open `http://localhost:5173` in your browser
   - Log in with your Google workspace account

## Architecture Overview

### Shell Agency Design
```
User Request
    ↓
Dynamic Bash Orchestrator
    ↓
Spawns Specialized Agents ←→ Direct Bash Access
    ↓                            ↓
Task Execution              Python Tools
    ↓                            ↓
Results Aggregation         Tool Results
    ↓
Response to User
```

### Key Components

1. **Dynamic Bash Orchestrator** (`/frontend/server/dynamic-bash-orchestrator.js`)
   - Analyzes user requests
   - Spawns specialized bash agents
   - Coordinates parallel execution
   - Aggregates results

2. **Bash Tool** (`/frontend/server/tools/bash-tool.js`)
   - Safety checks for dangerous commands
   - Configurable timeout (default 5 minutes)
   - Real-time progress updates
   - Working directory management

3. **Python Tools** (`/frontend/python-tools/`)
   - 30+ Shopify-specific tools
   - Direct execution via bash
   - No wrapper overhead
   - Composable via pipes and scripts

4. **Planning Agent** (`/frontend/server/agents/planning-agent.js`)
   - Analyzes request complexity
   - Creates structured task plans
   - Updates task status in real-time

5. **SWE Agent** (`/frontend/server/agents/swe-agent-connected.js`)
   - Software engineering capabilities
   - MCP integration for:
     - Shopify Dev documentation search
     - GraphQL schema introspection
     - Context7 library resolution
   - Can create and modify tools

## Available Tools

### Shopify Tools
- **Product Management**: search_products, get_product, create_product, update_pricing, manage_tags
- **Inventory**: manage_inventory_policy, update_product_status, bulk_operations
- **Special Features**: create_combo, create_open_box, manage_variant_links
- **GraphQL**: run_graphql_query, run_graphql_mutation

### MCP Tools (via SWE Agent)
- **Shopify Dev**: search_dev_docs, introspect_admin_schema, fetch_docs_by_path
- **Context7**: resolve-library-id, get-library-docs

## Usage Examples

### Simple Task
```
User: "Update the price of SKU ABC123 to $29.99"
→ Orchestrator spawns single bash agent
→ Agent runs: python update_pricing.py --sku ABC123 --price 29.99
```

### Complex Task
```
User: "Find all coffee products under $20 and increase their prices by 10%"
→ Orchestrator spawns Task Manager to plan
→ Spawns parallel agents:
  - Search_Agent: python search_products.py --query "coffee" --max-price 20
  - Price_Update_Agent: python bulk_price_update.py --increase 10
```

### Tool Creation
```
User: "Create a tool to export product data to CSV"
→ Orchestrator hands off to SWE Agent
→ SWE Agent creates new Python tool with proper error handling
```

## Project Structure

```
espressobot/
├── frontend/                 # Main application
│   ├── server/              # Backend services
│   │   ├── agents/          # Agent implementations
│   │   ├── tools/           # Tool wrappers
│   │   └── *.js            # API endpoints
│   ├── src/                 # React frontend
│   ├── python-tools/        # Python tool collection
│   ├── prisma/             # Database schema
│   └── package.json        
├── CLAUDE.md               # Development log
├── TODO.md                 # Future enhancements
└── README.md               # This file
```

## Development

### Adding New Tools
1. Create Python script in `/frontend/python-tools/`
2. Follow existing patterns for argument parsing
3. No registration needed - agents discover tools automatically

### Testing
```bash
# Test basic agent
node test-basic-agent.js

# Test SWE agent with MCP
node test-swe-mcp.js

# Test specific tools
cd frontend/python-tools
python search_products.py --help
```

### Debugging
- Check server logs for agent actions
- Use `VERBOSE=true` for detailed bash output
- Monitor SSE events in browser DevTools

## Known Issues

1. **Memory System**: Currently disabled due to infinite loops. Needs:
   - Queue system for operations
   - Cancellation tokens
   - Circuit breaker pattern

2. **Large Images**: Base64 image handling has limitations in OpenAI agents SDK
   - Recommend using image URLs instead
   - Keep uploads under 375KB

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is proprietary software for iDrinkCoffee.com.

## Acknowledgments

- Built with OpenAI Agents SDK
- Inspired by Unix philosophy
- Powered by Shopify APIs