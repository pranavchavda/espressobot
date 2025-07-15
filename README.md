# EspressoBot 🤖☕

An AI-powered e-commerce assistant for iDrinkCoffee.com, built with OpenAI agents SDK and Model Context Protocol (MCP).

## Overview

EspressoBot is a sophisticated conversational AI system that manages e-commerce operations through natural language. It uses a Shell Agency architecture with dynamic bash agents and native MCP tools to perform complex tasks autonomously.

## Key Features

- **🖼️ Vision Capability**: Process images (screenshots, product photos) with automatic retry logic
- **🔧 27+ Native Tools**: Direct Shopify API integration via MCP (Model Context Protocol)
- **🧠 Smart Memory**: Local SQLite-based semantic memory with deduplication
- **📋 Task Planning**: Automatic task breakdown for complex operations
- **🤖 Multi-Agent System**: Specialized agents for different domains
- **🔄 Real-time Updates**: Server-sent events for live progress tracking
- **🛡️ Safety Features**: Dangerous command detection, autonomy controls
- **🔌 External MCP Server Support**: Add custom MCP servers via JSON configuration

## Architecture

```
frontend/
├── server/
│   ├── agents/              # Specialized AI agents
│   │   ├── semantic-bash-agent.js    # Bash execution with context
│   │   ├── swe-agent-connected.js    # Software engineering agent
│   │   ├── task-planning-agent.js    # Task decomposition
│   │   ├── python-tools-agent.js     # MCP agent for Shopify tools
│   │   ├── external-mcp-agent.js     # MCP agent for external servers
│   │   └── documentation-mcp-agent.js # MCP agent for API docs
│   ├── memory/              # Local memory system
│   │   └── simple-local-memory.js    # SQLite + embeddings
│   ├── tools/               # Tool implementations
│   │   ├── bash-tool.js              # Safe bash execution
│   │   ├── mcp-client.js             # MCP integration
│   │   ├── mcp-server-manager.js     # External server management
│   │   ├── mcp-agent-router.js       # Intelligent MCP routing
│   │   └── view-image-tool.js       # Vision support
│   └── espressobot-orchestrator.js  # Main orchestrator
│
├── python-tools/
│   ├── mcp-server.py        # MCP server for Python tools
│   └── [27 tool implementations]
│
└── src/                     # React frontend
    └── features/chat/       # Chat interface
```

## Technology Stack

- **Backend**: Node.js, Express, Vite
- **AI/ML**: OpenAI agents SDK, GPT-4/O3 models
- **Database**: SQLite (memory), Prisma ORM
- **Tools**: Python, MCP (Model Context Protocol)
- **Frontend**: React, Tailwind CSS
- **Auth**: Google OAuth, JWT

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.8+
- OpenAI API key
- Shopify Admin API access

### Installation

```bash
# Clone the repository
git clone git@github.com:pranavchavda/espressobot.git
cd espressobot/frontend

# Install dependencies
npm install
pip install -r python-tools/requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```env
# Required
OPENAI_API_KEY=sk-...
SHOPIFY_SHOP_URL=https://your-store.myshopify.com
SHOPIFY_ACCESS_TOKEN=shpat_...

# Optional
PERPLEXITY_API_KEY=pplx-...
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=file:./prisma/dev.db
```

### Running the Application

```bash
# Development mode
npm run dev

# The app will be available at http://localhost:5173
```

## External MCP Server Configuration

### Adding External MCP Servers

EspressoBot supports adding external MCP servers (stdio or HTTP) via JSON configuration:

1. **Edit `mcp-servers.json`**:
```json
{
  "mcpServers": {
    "fetch": {
      "description": "MCP server for fetching web content",
      "enabled": true,
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-fetch"]
    },
    "your-server": {
      "description": "Your custom MCP server",
      "enabled": true,
      "type": "http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

2. **Hot Reload**: Changes are applied automatically without restarting the server

3. **Supported Server Types**:
   - **stdio**: Command-line MCP servers
   - **http**: REST API MCP servers

4. **Server Properties**:
   - `description`: Human-readable description
   - `enabled`: Toggle server on/off
   - `type`: Either "stdio" or "http"
   - For stdio: `command` and `args`
   - For http: `url`

### Built-in MCP Servers

- **Python Tools**: 27 Shopify operations (always available)
- **Shopify Dev**: API documentation and GraphQL introspection
- **External servers**: Any MCP server added via configuration

## Usage Examples

### Product Management
```
User: "Update the price of SKU ESP-001 to $49.99"
Bot: ✓ Updated price to $49.99
```

### Bulk Operations
```
User: "Set all Breville machines to 15% off"
Bot: ✓ Applied 15% discount to 12 products
```

### Image Analysis
```
User: [uploads screenshot] "Remove the commercial tag from these products"
Bot: ✓ Removed 'commercial' tag from 4 products shown in the image
```

### Complex Tasks
```
User: "Create a combo product with the Breville Barista Express and Smart Grinder"
Bot: ✓ Created combo COMBO-2501-BES870-BCG820
     ✓ Set combo price to $799.99 (10% discount)
     ✓ Generated combined product image
```

## MCP Tools Available

### Product Management (12 tools)
- `get_product` - Retrieve product details
- `create_product` - Create new products
- `update_pricing` - Modify prices
- `manage_tags` - Add/remove tags
- `add_product_images` - Image management
- And more...

### Operations (8 tools)
- `manage_inventory_policy` - Oversell settings
- `bulk_price_update` - Batch pricing
- `manage_redirects` - URL redirects
- `manage_map_sales` - MAP compliance
- And more...

### Integrations (7 tools)
- `perplexity_research` - Market research
- `send_review_request` - Yotpo reviews
- `upload_to_skuvault` - Inventory sync
- `memory_operations` - Knowledge storage
- And more...

## Shell Agency Architecture

EspressoBot uses a "Shell Agency" pattern where:
1. The orchestrator analyzes requests and plans execution
2. Bash agents are spawned dynamically for complex tasks
3. Agents can create custom tools on-the-fly
4. All agents share context through the memory system

This provides maximum flexibility while maintaining safety through:
- Command validation and sanitization
- Timeout controls (default 2 minutes)
- Dangerous command detection
- Audit logging

## Development

### Adding New Tools

1. **Python Tool** (via MCP):
```python
# python-tools/my_new_tool.py
def my_new_tool(param1: str, param2: int = 10):
    """Tool description for the AI"""
    # Implementation
    return result
```

2. **JavaScript Tool**:
```javascript
// server/tools/my-new-tool.js
export const myNewTool = tool({
  name: 'my_new_tool',
  description: 'What this tool does',
  parameters: z.object({
    param1: z.string()
  }),
  execute: async ({ param1 }) => {
    // Implementation
  }
});
```

### Testing

```bash
# Test MCP tools
node test-all-mcp-tools.js

# Test specific functionality
node tests/test-vision-agent.js
```

## Deployment

The application is designed to run on any Node.js hosting platform:

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Documentation

- [CLAUDE.md](CLAUDE.md) - Development instructions and architecture details
- [Tool Usage Guide](server/tool-docs/TOOL_USAGE_GUIDE.md) - Comprehensive tool documentation
- [Vision Solution](VISION_SOLUTION.md) - Image processing implementation

## License

Proprietary - iDrinkCoffee.com

## Acknowledgments

- Built with [OpenAI agents SDK](https://github.com/openai/agents)
- Uses [Model Context Protocol](https://modelcontextprotocol.io)
- Powered by GPT-4 and Claude