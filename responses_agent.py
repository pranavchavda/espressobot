"""
Agent implementation using the OpenAI Responses API instead of Chat Completions API.
"""
import os
import json
from simple_agent import (
    execute_shopify_query,
    execute_shopify_mutation,
    introspect_admin_schema,
    search_dev_docs,
    TOOLS,
    client as openai_client,
)

async def run_responses_agent(message, history=None):
    """
    Run an agent using the OpenAI Responses API.
    """
    if history is None:
        history = []

    # Concatenate history into instructions for context
    history_text = "\n".join([
        f"{item.get('role', 'user').capitalize()}: {item.get('content', '')}" for item in history
    ])
    system_prompt = (
        "You are a helpful assistant for Shopify store admins. "
        "You can answer questions, run GraphQL queries, introspect the schema, and search docs."
    )
    if history_text:
        instructions = f"{system_prompt}\n\nConversation so far:\n{history_text}"
    else:
        instructions = system_prompt


    steps = []
    final_response = None

    try:
        response = openai_client.responses.create(
            model=os.environ.get('DEFAULT_MODEL', 'gpt-4.1-nano'),
            input=message,
            instructions=instructions,
            tools=TOOLS,
            tool_choice="auto",
            temperature=1.0,
            parallel_tool_calls=True,
        )
        # The output is a list of message objects; handle tool calls if present
        for output_msg in response.output:
            if hasattr(output_msg, 'tool_calls') and output_msg.tool_calls:
                for tool_call in output_msg.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    steps.append({
                        "type": "tool",
                        "name": function_name,
                        "input": function_args
                    })
                    print(f"Tool call: {function_name} with args: {function_args}")
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
                    if result and "errors" in result:
                        print(f"API error in {function_name}: {result['errors']}")
                    steps.append({
                        "type": "tool_result",
                        "name": function_name,
                        "output": result
                    })
                continue
            # If no tool calls, get the text output
            # output_msg.content is a list of objects (ResponseOutputText)
            if hasattr(output_msg, 'content') and output_msg.content:
                for part in output_msg.content:
                    # For OpenAI Python SDK, type is an attribute, not a dict key
                    if hasattr(part, 'type') and part.type == 'output_text':
                        final_response = getattr(part, 'text', None)
                        break
                if final_response:
                    break
    except Exception as e:
        import traceback
        print(f"Error in agent execution: {e}")
        print(traceback.format_exc())
        final_response = f"Sorry, an error occurred: {str(e)}"
    return {
        "final_output": final_response,
        "steps": steps
    }
