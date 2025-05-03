# Shopify Agent Flask

A Flask application that provides a Shopify assistant using the OpenAI API and Shopify Admin API. This application allows you to interact with your Shopify store using natural language commands and queries.

## Features

- Interactive chat interface
- Shopify Admin GraphQL API integration
- OpenAI Agents SDK with MCP integration
- Query and mutation support for Shopify operations

## Requirements

- Python 3.8+
- OpenAI API key
- Shopify Admin API access token
- Shopify store URL

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Copy the `.env` file from your previous project or create a new one with:
   ```
   OPENAI_API_KEY=your_openai_api_key
   SHOPIFY_ACCESS_TOKEN=your_shopify_access_token
   SHOPIFY_SHOP_URL=your-store.myshopify.com
   SHOPIFY_API_VERSION=2025-04
   ```

3. Run the Flask application:
   ```
   python app.py
   ```

4. Open your browser to http://localhost:5000 to access the chat interface.

## Usage

The application provides a simple chat interface where you can:

- Query your Shopify store: "Show me my recent orders"
- Create or update resources: "Update the title of product X to Y"
- Get information about your store: "How many products do I have in my store?"

The assistant automatically determines whether to perform a query or mutation operation based on your input.

## Project Structure

- `app.py` - Main Flask application
- `simple_agent.py` - OpenAI API implementation with Shopify integration
- `templates/index.html` - Chat interface template
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (not in version control)

## License

This project is private and confidential.
