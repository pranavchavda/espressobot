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
    TOOLS,
    execute_shopify_query,
    execute_shopify_mutation,
    introspect_admin_schema,
    search_dev_docs,
    get_current_datetime_est,
)


async def run_responses_agent(
    message: str, history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Run an agent using the Responses API. Supports function/tool calls identically to simple_agent.
    Returns a dict with 'steps' and 'final_output'.
    """
    if history is None:
        history = []
    # Build input items from conversation history
    input_items: List[Dict[str, Any]] = []
    for item in history:
        role = item.get('role')
        content = item.get('content', '')
        if role == 'assistant':
            # Represent assistant messages as ResponseOutputMessageParam
            input_items.append({
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": content}],
                "status": "completed",
                "id": str(uuid4()),
            })
        else:
            # User messages
            input_items.append({
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": content}],
            })
    # Add current user message
    input_items.append({
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": message}],
    })

    # System instructions (passed separately)
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

    steps: List[Dict[str, Any]] = []
    step_count = 0
    max_steps = 10
    final_output = ""

    # Main agent loop: handle tool calls iteratively
    while step_count < max_steps:
        step_count += 1
        # Invoke the Responses API
        response = client.responses.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            input=input_items,
            instructions=system_message,
            tools=TOOLS,
            tool_choice="auto",
        )
        # Collect any new assistant messages and function calls
        function_calls = []
        for output in response.output:
            if getattr(output, "type", None) == "message":
                # Append assistant message to context
                try:
                    msg_param = output.model_dump()
                except Exception:
                    # Fallback to manual dict
                    msg_param = {
                        "type": output.type,
                        "role": output.role,
                        "content": [{"type": c.type, "text": c.text} for c in output.content],
                        "status": output.status,
                        "id": output.id,
                    }
                input_items.append(msg_param)
            elif getattr(output, "type", None) == "function_call":
                function_calls.append(output)
        # If there are function calls, execute them and feed results back
        if function_calls:
            for fc in function_calls:
                call_id = fc.call_id
                fname = fc.name
                args = json.loads(fc.arguments)
                steps.append({"type": "tool", "name": fname, "input": args})
                # Execute the actual tool
                if fname == "run_shopify_query":
                    result = await execute_shopify_query(args.get("query", ""), args.get("variables", {}))
                elif fname == "run_shopify_mutation":
                    result = await execute_shopify_mutation(args.get("query", ""), args.get("variables", {}))
                elif fname == "introspect_admin_schema":
                    result = await introspect_admin_schema(args.get("query", ""), args.get("filter_types", ["all"]))
                elif fname == "search_dev_docs":
                    result = await search_dev_docs(args.get("prompt", ""))
                else:
                    result = {"error": f"Unknown function: {fname}"}
                steps.append({"type": "tool_result", "name": fname, "output": result})
                # Feed function output back into context
                input_items.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(result),
                })
            # Continue loop to let model generate final answer
            continue
        # No tool calls: gather final assistant response
        texts: List[str] = []
        for output in response.output:
            if getattr(output, "type", None) == "message":
                for c in output.content:
                    if getattr(c, "type", None) == "output_text":
                        texts.append(c.text)
        final_output = "".join(texts)
        steps.append({"type": "final", "output": final_output})
        break

    return {"steps": steps, "final_output": final_output}