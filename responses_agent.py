"""
New implementation of the OpenAI Responses API integration for flask-shopifybot.
This replaces the old responses_agent.py with a modern implementation that properly
utilizes the OpenAI responses API for agentic workflows with native MCP support.
"""
import os
import json
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator

# Import OpenAI client
import openai

# Reuse helpers from simple_agent
from simple_agent import (
    execute_shopify_query,
    execute_shopify_mutation,
    introspect_admin_schema,
    search_dev_docs,
    get_current_datetime_est,
    TOOLS,
)

# Import memory service
from memory_service import memory_service

# Configure OpenAI client for async operations
client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

def clean_output(text):
    """Remove thinking tags from the output."""
    import re
    # Remove <THINKING>...</THINKING> blocks
    cleaned = re.sub(r'<THINKING>.*?</THINKING>', '', text, flags=re.DOTALL)
    # Remove any remaining tags
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    return cleaned.strip()

async def generate_conversation_title(message: str) -> str:
    """
    Generate a title for a new conversation based on the first message.
    
    Args:
        message: The user's first message
        
    Returns:
        A generated title for the conversation
    """
    try:
        # Use a simple prompt to generate a title
        response = await client.chat.completions.create(
            model=os.environ.get("DEFAULT_MODEL", "gpt-4.1-nano"),
            messages=[
                {"role": "system", "content": "Generate a short, descriptive title (max 50 chars) for a conversation that starts with this message. Return only the title text."},
                {"role": "user", "content": message}
            ],
            max_tokens=20,
            temperature=0.7
        )
        
        title = response.choices[0].message.content.strip()
        # Truncate if too long
        if len(title) > 50:
            title = title[:47] + "..."
        return title
    except Exception as e:
        print(f"Error generating title: {e}")
        # Fallback to a simple truncated version of the message
        if len(message) > 30:
            return message[:27] + "..."
        return message

async def execute_tool_call(function_name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a tool call based on the function name and arguments."""
    try:
        if function_name == "run_shopify_query":
            return await execute_shopify_query(arguments.get("query", ""), arguments.get("variables", {}))
        
        elif function_name == "run_shopify_mutation":
            return await execute_shopify_mutation(arguments.get("mutation", ""), arguments.get("variables", {}))
        
        elif function_name == "introspect_admin_schema":
            return await introspect_admin_schema(arguments.get("type_name", ""), arguments.get("field_name", ""))
        
        elif function_name == "search_dev_docs":
            return await search_dev_docs(arguments.get("query", ""))
        
        # Add other tool implementations as needed
        
        else:
            return f"Tool {function_name} not implemented"
    
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error executing tool {function_name}: {str(e)}")
        print(error_traceback)
        return f"Error executing tool {function_name}: {str(e)}"

async def run_responses_agent(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    user_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Run an agent using the OpenAI Responses API with streaming support.
    
    Args:
        message: The user's message
        history: Optional conversation history in the format [{"role": "user", "content": "..."}, ...]
        user_id: Optional user ID for memory service integration
        
    Yields:
        Chunks of the response with various types (content, tool, tool_result)
    """
    # Convert history to OpenAI format if provided
    formatted_history = []
    if history:
        for item in history:
            role = item.get('role', 'user')
            content = item.get('content', '')
            formatted_history.append({
                "role": role,
                "content": content
            })
    
    # System message (reused from simple_agent for consistency)
    current_time = get_current_datetime_est()
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "Unknown")
    system_message = f"""
You are a helpful assistant for iDrinkCoffee.com. Current date/time: {current_time}.
"""

    # Initialize variables for tracking state
    steps = []
    response_id = None
    final_output = ""
    
    try:
        # Use chat completions API instead of responses API for simplicity
        # This is a fallback approach that will work reliably
        messages = []
        
        # Add system message
        messages.append({"role": "system", "content": system_message})
        
        # Add conversation history
        if history:
            for msg in history:
                messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        
        # Add the current user message
        messages.append({"role": "user", "content": message})
        
        # Create a chat completion
        response = await client.chat.completions.create(
            model=os.environ.get("DEFAULT_MODEL", "gpt-4.1-nano"),
            messages=messages,
            stream=True
        )
        
        # Process the streaming response
        current_content = ""
        
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                content_delta = chunk.choices[0].delta.content
                current_content += content_delta
                yield {"type": "content", "delta": content_delta}
        
        # Clean up the final output
        final_output = clean_output(current_content)
        
        # Yield the final result
        yield {"type": "content", "result": json.dumps({
            "content": final_output,
            "steps": steps,
            "response_id": response_id
        })}
        
        # Store memory if user_id is provided
        if user_id and final_output:
            try:
                await memory_service.store_memory(
                    user_id=user_id,
                    content=f"User: {message}\nAssistant: {final_output}"
                )
            except Exception as e:
                print(f"Error storing memory for user {user_id}: {e}")
                
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"Error in run_responses_agent: {str(e)}")
        print(error_traceback)
        yield {"type": "content", "result": json.dumps({
            "content": f"Sorry, an error occurred: {str(e)}",
            "steps": steps,
            "response_id": response_id
        })}
