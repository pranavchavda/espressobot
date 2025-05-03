"""
A simplified agent implementation that doesn't rely on the Agents SDK.
This uses OpenAI's API directly to avoid typing issues.
"""
import os
import json
import httpx
import pytz
import openai
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import our custom MCP server implementation
from mcp_server import mcp_server

# Indicate that MCP is available through our custom implementation
MCP_AVAILABLE = True

# Configure OpenAI client
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# Function to execute GraphQL queries
async def execute_shopify_query(query, variables=None):
    """Execute a Shopify GraphQL query with the provided variables"""
    if variables is None:
        variables = {}
    
    print(f"Executing Shopify query: {query[:100]}...")
    
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "")
    access_token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
    api_version = os.environ.get("SHOPIFY_API_VERSION", "2025-04")
    
    if not shop_url or not access_token:
        raise ValueError("Missing Shopify credentials")
    
    # Ensure we have a properly formatted URL
    if shop_url.startswith("http://") or shop_url.startswith("https://"):
        # URL already has scheme
        base_url = shop_url
    else:
        # Add https:// scheme
        base_url = f"https://{shop_url}"
        
    # Remove any trailing slashes
    base_url = base_url.rstrip("/")
    
    endpoint = f"{base_url}/admin/api/{api_version}/graphql.json"
    print(f"Using Shopify endpoint: {endpoint}")
    
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    try:
        # Set explicit timeout to avoid hanging
        async with httpx.AsyncClient(timeout=15.0) as client:
            print(f"Sending request to Shopify API at {endpoint}")
            response = await client.post(
                endpoint,
                json={"query": query, "variables": variables},
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            print(f"Query result: {str(result)[:200]}...")
            return result
    except httpx.ConnectTimeout as e:
        error_msg = f"Connection timeout trying to reach Shopify API: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}
    except httpx.TimeoutException as e:
        error_msg = f"Timeout while connecting to Shopify API: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error from Shopify API: {e.response.status_code} - {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}
    except Exception as e:
        error_msg = f"Error connecting to Shopify API: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}

async def execute_shopify_mutation(mutation, variables=None):
    """Execute a Shopify GraphQL mutation with the provided variables"""
    if variables is None:
        variables = {}
    
    print(f"Executing Shopify mutation: {mutation[:100]}...")
    
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "")
    access_token = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
    api_version = os.environ.get("SHOPIFY_API_VERSION", "2025-04")
    
    if not shop_url or not access_token:
        raise ValueError("Missing Shopify credentials")
    
    # Ensure we have a properly formatted URL
    if shop_url.startswith("http://") or shop_url.startswith("https://"):
        # URL already has scheme
        base_url = shop_url
    else:
        # Add https:// scheme
        base_url = f"https://{shop_url}"
        
    # Remove any trailing slashes
    base_url = base_url.rstrip("/")
    
    endpoint = f"{base_url}/admin/api/{api_version}/graphql.json"
    print(f"Using Shopify endpoint for mutation: {endpoint}")
    
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    try:
        # Set explicit timeout to avoid hanging
        async with httpx.AsyncClient(timeout=15.0) as client:
            print(f"Sending mutation request to Shopify API at {endpoint}")
            response = await client.post(
                endpoint,
                json={"query": mutation, "variables": variables},
                headers=headers
            )
            response.raise_for_status()
            result = response.json()
            print(f"Mutation result: {str(result)[:200]}...")
            return result
    except httpx.ConnectTimeout as e:
        error_msg = f"Connection timeout trying to reach Shopify API: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}
    except httpx.TimeoutException as e:
        error_msg = f"Timeout while connecting to Shopify API: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}
    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP error from Shopify API: {e.response.status_code} - {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}
    except Exception as e:
        error_msg = f"Error connecting to Shopify API: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}

# Function to get current date/time in EST
def get_current_datetime_est():
    """Get the current date and time in EST timezone formatted for context"""
    now = datetime.now(pytz.timezone('America/New_York'))
    return now.strftime("%Y-%m-%d %H:%M:%S EST")

# Start the MCP server if it's available
async def ensure_mcp_server_running():
    """Ensure the MCP server is running before making any requests"""
    if MCP_AVAILABLE:
        try:
            print("Ensuring Shopify Dev MCP server is running...")
            await mcp_server.start()
            return True
        except Exception as e:
            print(f"Failed to start Shopify Dev MCP server: {e}")
            return False
    return False

# Function to introspect Shopify Admin API schema
async def introspect_admin_schema(query, filter_types=None):
    """Introspect the Shopify Admin API schema using the MCP tool"""
    if filter_types is None:
        filter_types = ["all"]
    
    print(f"Introspecting Shopify Admin schema for: {query}")
    
    try:
        if MCP_AVAILABLE:
            # Ensure the MCP server is running
            server_ready = await ensure_mcp_server_running()
            if server_ready:
                # Use our MCP server to get schema information
                response = await mcp_server.introspect_admin_schema(query, filter_types)
                print(f"Schema introspection complete for: {query}")
                return response
        
        # Fallback to mock implementation
        print("Using mock implementation for schema introspection")
        return {
            "schema": f"Mock schema introspection result for '{query}' with filters {filter_types}",
            "note": "This is a mock response. The Shopify Dev MCP server is not available."
        }
    except Exception as e:
        error_msg = f"Error introspecting schema: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}

# Function to search Shopify dev docs
async def search_dev_docs(prompt):
    """Search Shopify developer documentation using the MCP tool"""
    print(f"Searching Shopify dev docs for: {prompt}")
    
    try:
        if MCP_AVAILABLE:
            # Ensure the MCP server is running
            server_ready = await ensure_mcp_server_running()
            if server_ready:
                # Use our MCP server to search docs
                response = await mcp_server.search_dev_docs(prompt)
                print(f"Dev docs search complete for: {prompt}")
                return response
        
        # Fallback to mock implementation
        print("Using mock implementation for dev docs search")
        return {
            "docs": f"Mock dev docs search result for '{prompt}'",
            "note": "This is a mock response. The Shopify Dev MCP server is not available."
        }
    except Exception as e:
        error_msg = f"Error searching dev docs: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"errors": [{"message": error_msg}]}

# Define available tools
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_shopify_query",
            "description": "Execute a Shopify GraphQL query to fetch data from the Shopify Admin API",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GraphQL query string"
                    },
                    "variables": {
                        "type": "object",
                        "description": "Query variables"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_shopify_mutation",
            "description": "Execute a Shopify GraphQL mutation to modify data in the Shopify Admin API",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "GraphQL mutation string"
                    },
                    "variables": {
                        "type": "object",
                        "description": "Mutation variables"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "introspect_admin_schema",
            "description": "Introspect the Shopify Admin API GraphQL schema to get details about types, queries, and mutations",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term to filter schema elements by name (e.g., 'product', 'discountCode')"
                    },
                    "filter_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["all", "types", "queries", "mutations"]
                        },
                        "description": "Filter results to show specific sections"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_dev_docs",
            "description": "Search Shopify developer documentation to get relevant information about Shopify APIs, features, and best practices",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The search query for Shopify documentation"
                    }
                },
                "required": ["prompt"]
            }
        }
    }
]

# Run the Shopify agent with a custom implementation
async def run_simple_agent(message, history=None):
    """Run a simple agent implementation that uses the OpenAI API directly"""
    if history is None:
        history = []
    
    # Convert history to the format expected by OpenAI
    formatted_history = []
    for item in history:
        role = item.get('role', 'user')
        content = item.get('content', '')
        formatted_history.append({"role": role, "content": content})
    
    # System message with instructions
    current_time = get_current_datetime_est()
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "Unknown")
    system_message = f"""
You are a helpful Shopify assistant for the shop: {shop_url}. Current date/time: {current_time}.

You can help with:
- Answering questions about Shopify and e-commerce
- Retrieving information from the Shopify Admin API
- Analyzing shop data
- Making changes to the shop through the API

You have access to several tools:

1. run_shopify_query - Execute GraphQL queries against the Shopify Admin API to fetch data
2. run_shopify_mutation - Execute GraphQL mutations against the Shopify Admin API to modify data
3. introspect_admin_schema - Get information about the Shopify Admin API schema (types, queries, mutations)
4. search_dev_docs - Search Shopify developer documentation for guidance

IMPORTANT:
- When unfamiliar with a specific part of the Shopify API, first use introspect_admin_schema to understand the available fields and types.
- Use search_dev_docs when you need guidance on Shopify features or best practices.
- For any Shopify API operations, use the appropriate tool: run_shopify_query for fetching data, run_shopify_mutation for modifying data.
- If a request requires prerequisite information (e.g., finding a product ID before updating it), first query for the missing information before attempting mutations.
- Make sure all GraphQL queries and mutations are valid for the Shopify Admin API version '{os.environ.get("SHOPIFY_API_VERSION", "2025-04")}'.
- Format all dates according to ISO 8601 (YYYY-MM-DD) when used in queries/mutations.
- Look for information in context and conversation history before querying the API.
- Keep responses concise and informative.
"""
    
    # Add system message to history
    formatted_messages = [{"role": "system", "content": system_message}] + formatted_history
    formatted_messages.append({"role": "user", "content": message})
    
    # Step logs for tracking agent progress
    steps = []
    
    # Main agent loop
    step_count = 0
    max_steps = 10  # Prevent infinite loops
    final_response = "I'm sorry, I couldn't complete the task due to an error."
    
    try:
        while step_count < max_steps:
            step_count += 1
            print(f"Running agent step {step_count}")
            
            # Call the model
            response = client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                messages=formatted_messages,
                tools=TOOLS,
                tool_choice="auto"
            )
            
            # Get the message content
            message = response.choices[0].message
            
            # Check for tool calls
            if message.tool_calls:
                # First, add the assistant's message with the tool call to the history
                formatted_messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [{
                        "id": tool_call.id,
                        "type": "function",
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    } for tool_call in message.tool_calls]
                })
                
                # Process each tool call
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Record the tool call
                    steps.append({
                        "type": "tool",
                        "name": function_name,
                        "input": function_args
                    })
                    
                    print(f"Tool call: {function_name} with args: {function_args}")
                    
                    # Execute the appropriate function
                    result = None
                    if function_name == "run_shopify_query":
                        query = function_args.get("query")
                        variables = function_args.get("variables", {})
                        result = await execute_shopify_query(query, variables)
                    elif function_name == "run_shopify_mutation":
                        mutation = function_args.get("query")
                        variables = function_args.get("variables", {})
                        result = await execute_shopify_mutation(mutation, variables)
                    elif function_name == "introspect_admin_schema":
                        query = function_args.get("query")
                        filter_types = function_args.get("filter_types", ["all"])
                        result = await introspect_admin_schema(query, filter_types)
                    elif function_name == "search_dev_docs":
                        prompt = function_args.get("prompt")
                        result = await search_dev_docs(prompt)
                    else:
                        result = {"error": f"Unknown function: {function_name}"}
                    
                    # Check for API errors
                    if result and "errors" in result:
                        print(f"API error in {function_name}: {result['errors']}")
                    
                    # Record the result
                    steps.append({
                        "type": "tool_result",
                        "name": function_name,
                        "output": result
                    })
                    
                    # Add the function response to messages correctly linked to the tool call
                    formatted_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(result)
                    })
                
                # Let the model continue with tool results
                continue
            
            # If no tool calls, we're done
            final_response = message.content
            break
    
    except Exception as e:
        import traceback
        print(f"Error in agent execution: {e}")
        print(traceback.format_exc())
        final_response = f"Sorry, an error occurred: {str(e)}"
    
    # Return the final result
    return {
        "final_output": final_response,
        "steps": steps
    }
