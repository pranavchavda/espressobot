"""
Agent implementation using the OpenAI Responses API, mirroring simple_agent logic but
using the /v1/responses endpoint instead of chat completions.
"""
import os
import json
import asyncio
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, List, Optional

# Reuse helpers and client from simple_agent
from simple_agent import (
    client,
    execute_shopify_query,
    execute_shopify_mutation,
    introspect_admin_schema,
    search_dev_docs,
    get_current_datetime_est,
)

TOOLS = [
    {
      "type": "web_search_preview",
      "user_location": {
        "type": "approximate"
      },
      "search_context_size": "medium"
    },
    {
        "name": "run_shopify_query",
        "type": "function",
        "function": {
            "name": "run_shopify_query",
            "description": "Execute a Shopify GraphQL query to fetch data from the Shopify Admin API",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The GraphQL query string"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "name": "run_shopify_mutation",
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
        "name": "introspect_admin_schema",
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
        "name": "search_dev_docs",
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

async def run_responses_agent(
    message: str,
    previous_response_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run an agent using the Responses API in stateless mode.
    Returns a dict with 'steps', 'final_output', and 'response_id'.
    """
    # Build only the new user message; let the Responses API handle prior turns server-side
    input_items: List[Dict[str, Any]] = [{
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": message}],
    }]
    steps: List[Dict[str, Any]] = []
    resp_id = previous_response_id

    # Prepare system instructions
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
5. web_search_preview - Search the web for information as a last resort

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

    max_steps = 10
    step_count = 0
    final_output = ""
    while step_count < max_steps:
        step_count += 1
        response = client.responses.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            input=input_items,
            instructions=system_message,
            tools=TOOLS,
            tool_choice="auto",
            store=True,
            parallel_tool_calls=True,
            previous_response_id=resp_id,
        )
        resp_id = response.id
        function_calls = [
            o for o in response.output if getattr(o, "type", None) == "function_call"
        ]
        if function_calls:
            for fc in function_calls:
                call_id = fc.call_id
                fname = fc.name
                # Tell the API which function we're calling
                input_items.append({
                    "type": "function_call",
                    "call_id": call_id,
                    "name": fname,
                    "arguments": fc.arguments
                })
                args = json.loads(fc.arguments)
                steps.append({"type": "tool", "name": fname, "input": args})
                # Execute the actual tool
                if fname == "run_shopify_query":
                    result = await execute_shopify_query(args.get("query", ""), args.get("variables", {}))
                elif fname == "run_shopify_mutation":
                    result = await execute_shopify_mutation(args.get("query", ""), args.get("variables", {}))
                elif fname == "introspect_admin_schema":
                    try:
                        result = await introspect_admin_schema(args.get("query", ""), args.get("filter_types", ["all"]))
                    except Exception as e:
                        print(f"Error in introspect_admin_schema: {e}")
                        result = {"content": f"Error accessing Shopify schema: {str(e)}. Please try again later or check your connection."}
                elif fname == "search_dev_docs":
                    try:
                        result = await search_dev_docs(args.get("prompt", ""))
                    except Exception as e:
                        print(f"Error in search_dev_docs: {e}")
                        result = {"content": f"Error searching dev docs: {str(e)}. Please try again later or check your connection."}
                else:
                    result = {"error": f"Unknown function: {fname}"}
                steps.append({"type": "tool_result", "name": fname, "output": result})
                payload = result.model_dump() if hasattr(result, "model_dump") else result
                input_items.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(payload),
                })
            # Loop again so the model can generate its final answer
            continue
        # No more tools; pull out the assistant's final text
        final_output = response.output_text
        steps.append({"type": "final", "output": final_output})
        return {
            "steps": steps,
            "final_output": final_output,
            "response_id": resp_id
        }

    return {"steps": steps, "final_output": final_output}
