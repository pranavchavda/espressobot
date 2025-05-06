import os
import json
from typing import Dict, Any, List, Optional
from agents import Agent, Runner, Tool
import httpx
import certifi
from datetime import datetime
import pytz

# Function to execute GraphQL queries
async def execute_shopify_query(args):
    print(f"Executing Shopify query with args: {args}")
    query = args.get("query", "")
    variables = args.get("variables", {})

    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "")
    access_token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
    api_version = os.environ.get("SHOPIFY_API_VERSION", "2025-04")

    if not shop_url or not access_token:
        raise ValueError("Missing Shopify credentials")

    endpoint = f"https://{shop_url}/admin/api/{api_version}/graphql.json"

    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }

    try:
        async with httpx.AsyncClient(verify=certifi.where()) as client:
            response = await client.post(
                endpoint,
                json={"query": query, "variables": variables},
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"Shopify GraphQL error: {e}")
        raise ValueError(f"Shopify API error: {str(e)}")

# Create the Shopify assistant agent
def create_shopify_agent():
    """Create a Shopify assistant agent with appropriate tools and instructions"""
    # Get current date/time in EST for context
    now = datetime.now(pytz.timezone('America/New_York'))
    current_date_time_est = now.strftime("%Y-%m-%d %H:%M:%S EST")

    # Create tools with simple schema definitions
    # Query tool for fetching data
    query_tool = Tool(
        name="run_shopify_query",
        description="Execute a Shopify GraphQL query to fetch data from the Shopify Admin API.",
        function=execute_shopify_query,
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "variables": {"type": "object"}
            },
            "required": ["query"]
        }
    )

    # Mutation tool for modifying data
    mutation_tool = Tool(
        name="run_shopify_mutation",
        description="Execute a Shopify GraphQL mutation to modify data in the Shopify Admin API.",
        function=execute_shopify_query,  # Same function for both tools
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "variables": {"type": "object"}
            },
            "required": ["query"]
        }
    )

    return Agent(
        name="ShopifyAssistant",
        instructions=f"""You are an AI assistant helping users interact with the Shopify Admin API for the shop '{os.environ.get("SHOPIFY_SHOP_URL", "")}'. 

Current date and time: {current_date_time_est}. Use this for any date-related calculations unless the user specifies otherwise (e.g., 'last year', 'yesterday').

IMPORTANT:
- For any Shopify API operations, use the appropriate tool: run_shopify_query for fetching data, run_shopify_mutation for modifying data.
- If a request requires prerequisite information (e.g., finding a product ID before updating it), first query for the missing information before attempting mutations.
- Make sure all GraphQL queries and mutations are valid for the Shopify Admin API version '{os.environ.get("SHOPIFY_API_VERSION", "2025-04")}'.
- Format all dates according to ISO 8601 (YYYY-MM-DD) when used in queries/mutations.
- Look for information in context and conversation history before querying the API.
- Keep responses concise and informative.
- Use shopify-dev-mcp for documentation and schema exploration when you're uncertain about API details.""",
        tools=[query_tool, mutation_tool],
        mcp_servers=["shopify-dev-mcp"]
    )

async def run_shopify_agent(message, history=None):
    """Run the Shopify agent with a user message and optional history"""
    history = history or []

    # Transform the message history to the format expected by the agent
    formatted_history = []
    for msg in history:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, (list, dict)):
            content = json.dumps(content)
        formatted_history.append({"role": role, "content": content})

    agent = create_shopify_agent()

    # Run the agent
    result = await Runner.run(agent, message, history=formatted_history)

    return result