# EspressoBot v0.2 - Shopify Assistant

An AI-powered Shopify assistant built on the OpenAI Agents SDK, providing intelligent e-commerce operations for iDrinkCoffee.com.

## Architecture

EspressoBot v0.2 uses a clean multi-agent architecture based on the OpenAI CS Agents Demo:

- **Triage Agent**: Routes requests to specialized agents
- **Product Search Agent**: Finds products, handles searches and browsing
- **Product Editor Agent**: Modifies existing products (prices, tags, status)
- **Product Creator Agent**: Creates new products, combos, and variants
- **Inventory Manager Agent**: Manages stock, costs, and SkuVault integration
- **Analytics & Orders Agent**: Runs reports, analyzes data, handles orders
- **Task Manager Agent**: Coordinates complex multi-step operations

## Setup

### Prerequisites

- Python 3.8+
- Node.js 18+
- OpenAI API key
- Access to iDrinkCoffee Shopify tools in `/home/pranav/idc/tools`

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd espressobot-v2/python-backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure your OpenAI API key:
   ```bash
   # Edit the .env file and add your key:
   OPENAI_API_KEY=your-api-key-here
   ```

5. Start the backend server:
   ```bash
   python run.py
   # Or directly with uvicorn:
   # uvicorn api:app --reload --port 8000
   ```

### Frontend Setup

1. Navigate to the UI directory:
   ```bash
   cd espressobot-v2/ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open http://localhost:3000 in your browser

## Usage

### Basic Operations

- **Find Products**: "Show me all Lavazza espresso products"
- **Update Prices**: "Update the price of SKU LAV-001 to $24.99"
- **Create Products**: "Create a coffee bundle with these 3 products"
- **Check Inventory**: "What's the stock level for all grinders?"
- **Run Analytics**: "Show me sales for coffee beans last month"

### Complex Operations

For multi-step tasks, the Task Manager Agent will automatically activate:
- "Update prices for all espresso machines by 10%"
- "Add 'holiday-sale' tag to all products under $50"
- "Create open-box variants for all products with tag 'returns'"

## Tools Available

### Search & Discovery
- `search_products`: Search by title, SKU, vendor, tags
- `get_product`: Get detailed product information
- `perplexity_search`: Research product information

### Product Management
- `product_create_full`: Create new products
- `create_combo`: Create bundle products
- `create_open_box`: Create open-box variants
- `update_pricing`: Update product/variant prices
- `manage_tags`: Add/remove tags
- `update_product_status`: Change product status

### Inventory
- `manage_inventory_policy`: Set inventory policies
- `upload_to_skuvault`: Sync with warehouse
- `bulk_price_update`: Update multiple prices

### Analytics
- `run_graphql_query`: Custom GraphQL queries
- `run_graphql_mutation`: Custom GraphQL mutations

## Architecture Benefits

- **Clean Separation**: Each agent has a specific domain
- **Efficient Handoffs**: Agents transfer to the most appropriate specialist
- **Scalable**: Easy to add new agents or tools
- **Maintainable**: Simple structure, clear responsibilities
- **Real-time Updates**: Live agent activity visualization

## Development

### Adding New Tools

1. Add the Python tool to `/home/pranav/idc/tools/`
2. Create a wrapper in `python-backend/tools/shopify_tools.py`
3. Assign it to the appropriate agent
4. Update agent instructions if needed

### Adding New Agents

1. Create a new agent file in `python-backend/agents/`
2. Define the agent with appropriate tools and handoffs
3. Update the imports in `agents/__init__.py`
4. Add to triage agent's routing logic
5. Update `api.py` to include in the agents list

## Troubleshooting

- **"OPENAI_API_KEY not set"**: Add your key to the `.env` file
- **"Tool not found"**: Ensure the Python tools directory exists at `/home/pranav/idc/tools/`
- **Connection errors**: Check that both backend (port 8000) and frontend (port 3000) are running
- **Agent not responding**: Check the backend logs for errors

## Future Enhancements

- Product image handling
- Batch operations UI
- Export functionality
- Custom reporting dashboards
- Integration with more Shopify features