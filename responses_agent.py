"""
Implementation of the OpenAI Responses API integration for flask-shopifybot.
This module provides functions to interact with the OpenAI Responses API for agentic workflows
with native MCP support.
"""
import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

# Import OpenAI client
from openai import OpenAI, AsyncOpenAI

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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI client for async operations
client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
sync_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

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
        logger.info(f"Generating title for message: {message[:30]}...")
        
        # Use the responses API to generate a title
        response = await client.responses.create(
            model=os.environ.get("DEFAULT_MODEL", "gpt-4.1-mini"),
            instructions="Generate a short, descriptive title (max 50 chars) for a conversation that starts with this message. Return only the title text.",
            input=message,
        )
        
        title = response.output_text.strip()
        logger.info(f"Generated title: {title}")
        
        # Truncate if too long
        if len(title) > 50:
            title = title[:47] + "..."
        return title
    except Exception as e:
        logger.error(f"Error generating title with responses API: {e}")
        # Fallback to a simple truncated version of the message
        if len(message) > 30:
            return message[:27] + "..."
        return message

async def execute_tool_call(function_name: str, arguments: Dict[str, Any]) -> Any:
    """Execute a tool call based on the function name and arguments."""
    try:
        logger.info(f"Executing tool call: {function_name} with args: {arguments}")
        
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
            logger.warning(f"Tool {function_name} not implemented")
            return f"Tool {function_name} not implemented"
    
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error executing tool {function_name}: {str(e)}")
        logger.error(error_traceback)
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
    input_items = []
    if history:
        for item in history:
            role = item.get('role', 'user')
            content = item.get('content', '')
            input_items.append({
                "role": role,
                "content": content
            })
    
    # Add the current user message
    input_items.append({
        "role": "user",
        "content": message
    })
    
    # System message (reused from simple_agent for consistency)
    current_time = get_current_datetime_est()
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "Unknown")
    system_message = f"""
You are "IDC-Shopify-Agent", the production Shopify assistant for iDrinkCoffee.com. 
Your mission: execute catalog and storefront tasks flawlessly, quickly, and with zero guesswork.

────────────────────────────────────────
FUNDAMENTAL PRINCIPLES
────────────────────────────────────────
1. Thinking Process:
   You MUST USE the tags <THINKING> and </THINKING> to outline your thought process. The content between these tags will not be sent to the user.
   You are encouraged to use this feature to explain your reasoning and thought process to yourself, and to plan your next steps. Use this feature liberally. 
   It will be removed from the final response to the user, it will only be logged for OpenAI to evaluate your performance.
   Responses that begin without <THINKING> and </THINKING> tags will be be partially penalized in the next training iteration.

2. Problem Solving:
   You MUST iterate and keep going until the problem is solved.You already have everything you need to solve any Shopify related problem.
   You can use any tool available to you to solve the problem. Understand the problem deeply. Carefully read the issue and think critically about what is required.
   Develop a clear, step-by-step plan. Break down the fix into manageable, incremental steps.

3. Persistent awareness of your original Intent:
   When solving a problem and using tools, always keep in mind the original intent and purpose of what you are doing at a high level.
   This will help you avoid getting lost in the details and losing sight of the bigger picture.

4. Know that you have a knowledge cutoff date:
   Your knowledge cut off date is June 2024. This means when using API calls, or writing code, you may not be aware of the latest changes. Things may have changed since then and you are not aware of it.
   Using the tools available to you, you can always get the latest documentation. Always assume that you may be using outdated information and refer to the latest documentation to ensure you are using the latest features and best practices.

────────────────────────────────────────
RULES
────────────────────────────────────────
1. **INTROSPECT FIRST**  
   • Before every new field/mutation/query you haven't already verified this session, call `introspect_admin_schema` and cache the result in memory.  
   • Never execute a mutation that is absent from the schema for the API version ($SHOPIFY_API_VERSION).
   • If you do not find a mutation in the schema, call `search_dev_docs` to find the mutation, if that doesn't help, call `perplexity_ask` to find the mutation.
   • NEVER suggest a mutation that is absent from the schema for the API version ($SHOPIFY_API_VERSION) and that the user should use the UI or the REST API to perform the action.

2. **VERIFY BEFORE WRITE**  
   • Changing a product? First call `run_shopify_query` to confirm the product exists, its status, and variant structure.  
   • Creating a product? First ensure an identical title or SKU does **not** exist (prevent duplicates).

3. **NO GUESSING / NO USER RESEARCH REQUESTS**  
   • If docs are unclear, you must call `search_dev_docs` and/or `perplexity_ask`.  
   • Never ask the user to paste docs or look things up for you.

4. **LOCAL SESSION MAP**  
   • Maintain an internal map -- title → productID → variants[] -- update it after every create/fetch.  
   • Use this map to reference correct IDs on subsequent steps.

5. **ONE MESSAGE → ONE DECISION**  
   • Each reply must be either  
     (a) a single clarifying question **or**  
     (b) a compact plan **plus** the necessary tool calls.  
   • Minimise apologies and filler.

6. **IMAGE SAFETY RULE**  
   • When calling `productCreateMedia`, include the product title and ID in the same assistant message, and use the *exact* image URL supplied for that product only.

7. **MUTATION CHEAT-SHEET** (2025-04)
   • Add option to existing product → `productOptionsCreate`  
   • Bulk add variants       → `productVariantsBulkCreate`  
   • Bulk update variant price / barcode → `productVariantsBulkUpdate`  
   • Update SKU or cost      → `inventoryItemUpdate` (fields: `sku`, `cost`, under `input`)  
   • Upload image            → `productCreateMedia`  
   • Delete product          → `productUpdate` (set `status` to `ARCHIVED` - never delete products)
   • Updating Shipping Weight → `inventoryItemUpdate` with the measurement field (weight.unit and weight.value). 

8. **IDC Jargon**
   • When asked add something to preorder, add the "preorder-2-weeks" tag to the product, and any tag that begins with "shipping-nis" (such as shipping-nis-April), similarly, when removing something from preorder, remove the "preorder-2-weeks" tag and any tag that begins with "shipping-nis" (such as shipping-nis-April).
     Also ask the user if they want to change the inventory policy of that product to DENY when something is taken out of preorder, when something is added to preorder, inventory policy should be set to ALLOW, without needing to ask the user.
   • Sale End Date: If asked to add a promotion or sale end date to any product, it can be added to the product's inventory.ShappifySaleEndDate metafiled (Namespace is inventory and key is ShappifySaleEndDate; it is single line text) Format example: 2023-08-04T03:00:00Z (For 3 AM on August 4, 2023) 
   • For US/USD price updates, use the pricelist ID: `gid://shopify/PriceList/18798805026`.
   
   
9. **COST HANDLING**  
   • Cost is set via the cost field on InventoryItemInput, which can be used with either inventoryItemUpdate (as cost under input) or within productVariantsBulkUpdate (as cost under inventoryItem).
   • The returned field is InventoryItem.unitCost (type: MoneyV2).
   • You may update cost for multiple variants in bulk by using productVariantsBulkUpdate with the inventoryItem.cost field.
        

10. **STATUS & TAG DEFAULTS**  
   • All newly-created products must be `DRAFT` status with required base fields, never set it to `ACTIVE`.
   • Apply standard tag block (`accessories`, `consumer`, etc.) unless user specifies otherwise.

11. **PRODUCT COPY**  
    • Always fetch the latest copy guide via `get_product_copy_guidelines`; do not rewrite it.  
    • If new permanent additions are provided by the user, store them as an addendum section via `run_shopify_mutation` on the metafield holding guidelines.

────────────────────────────────────────
RESPONSE STYLE
────────────────────────────────────────
• **Format**: `Plan:` → short bullet list; `Actions:` → tool calls (if any); `Result:` → brief confirmation.  
• **Tone**: concise, professional, no waffle.  
• **Citations**: cite tool call IDs inline where useful.

────────────────────────────────────────
FAIL-SAFES
────────────────────────────────────────
• If a mutation fails, immediately show the error message, introspect that mutation, and retry only once with corrected arguments.  
• If still failing, summarise the blocker and ask the user how to proceed.

You are a helpful Shopify assistant for the shop: iDrinkCoffee.com. Current date/time: {current_time}.
"""

    # Initialize variables for tracking state
    steps = []
    response_id = None
    final_output = ""
    
    try:
        # First, check if we need to retrieve memories
        if user_id:
            try:
                # Proactively retrieve memories
                retrieved_memory_contents = await memory_service.proactively_retrieve_memories(
                    user_id, 
                    message,
                    top_n=3 
                )
                
                if retrieved_memory_contents:
                    formatted_memories = "\n".join([f"- {mem}" for mem in retrieved_memory_contents])
                    memory_context = (
                        "To help you respond, here's some information from my memory that might be relevant to the current query:\n"
                        f"{formatted_memories}\n\n"
                        "--- User's current message ---\n"
                    )
                    # Update the last message with memory context
                    augmented_message = memory_context + message
                    input_items[-1]["content"] = augmented_message
            except Exception as e:
                logger.error(f"Error retrieving proactive memories for user {user_id}: {e}")
        
        # Create the response using the OpenAI Responses API
        logger.info(f"Creating response with OpenAI Responses API for message: {message[:50]}...")
        
        # Use the model specified in environment variables, with gpt-4.1-mini as default
        model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        logger.info(f"Using model: {model}")
        
        # Log the API call details for debugging
        logger.info(f"API call details: model={model}, input_items_count={len(input_items)}")
        
        try:
            # Use the responses API with streaming
            logger.info("Starting responses API streaming call...")
            stream = await client.responses.create(
                model=model,
                instructions=system_message,
                input=input_items,
                tools=TOOLS,
                tool_choice="auto",
                store=True,
                parallel_tool_calls=True,
                stream=True,
            )
            
            logger.info("Successfully created responses stream")
            
            # Process the streaming response
            current_content = ""
            active_tool_calls = {}
            tool_call_executed = False
            
            # Stream through the response events
            logger.info("Beginning to process stream chunks...")
            async for chunk in stream:
                # Debug the chunk structure
                logger.info(f"Response chunk type: {type(chunk).__name__}")
                
                # Handle different types of events in the stream
                if hasattr(chunk, 'id') and not response_id:
                    response_id = chunk.id
                    logger.info(f"Response ID: {response_id}")
                
                # Handle content updates - check for both output_text and delta attributes
                if hasattr(chunk, 'output_text') and chunk.output_text:
                    delta = chunk.output_text
                    current_content += delta
                    logger.info(f"Content delta (output_text): {delta}")
                    yield {"type": "content", "delta": delta}
                
                # For ResponseTextDeltaEvent, check the delta attribute
                if type(chunk).__name__ == 'ResponseTextDeltaEvent' and hasattr(chunk, 'delta'):
                    delta = chunk.delta
                    current_content += delta
                    logger.info(f"Content delta (delta): {delta}")
                    yield {"type": "content", "delta": delta}
                
                # Handle tool calls
                if hasattr(chunk, 'tool_calls') and chunk.tool_calls:
                    for tool_call in chunk.tool_calls:
                        call_id = tool_call.id
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        logger.info(f"Tool call: {function_name} with args: {arguments}")
                        tool_call_executed = True
                        
                        # Record the tool call
                        tool_call_data = {"type": "tool", "name": function_name, "input": arguments}
                        steps.append(tool_call_data)
                        yield tool_call_data
                        
                        # Execute the tool call
                        result = await execute_tool_call(function_name, arguments)
                        
                        # Record and yield the tool result
                        tool_result = {"type": "tool_result", "name": function_name, "output": result}
                        steps.append(tool_result)
                        yield tool_result
                        
                        # Submit the tool result back to the API
                        logger.info(f"Submitting tool output for call_id: {call_id}")
                        await client.responses.submit_tool_outputs(
                            response_id=response_id,
                            tool_outputs=[{
                                "tool_call_id": call_id,
                                "output": json.dumps(result)
                            }]
                        )
            
            logger.info("Finished processing stream chunks")
            
            # Clean up the final output (remove thinking tags)
            final_output = clean_output(current_content)
            logger.info(f"Final output: {final_output[:100]}...")
            
            # If a tool call was executed but no final content was received,
            # generate a default response to ensure the UI shows something
            if tool_call_executed and not final_output.strip():
                final_output = "I've completed the requested operation. Is there anything else you'd like me to help with?"
                logger.info(f"Generated default response after tool call: {final_output}")
                yield {"type": "content", "delta": final_output}
            
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
                    logger.error(f"Error storing memory for user {user_id}: {e}")
                    
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error in responses API call: {str(e)}")
            logger.error(error_traceback)
            
            # Try a non-streaming call as a fallback for debugging
            logger.info("Attempting non-streaming call for debugging...")
            try:
                response = await client.responses.create(
                    model=model,
                    instructions=system_message,
                    input=message,
                )
                logger.info(f"Non-streaming response: {response}")
                final_output = response.output_text
                response_id = response.id
                
                yield {"type": "content", "result": json.dumps({
                    "content": final_output,
                    "steps": steps,
                    "response_id": response_id
                })}
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                yield {"type": "content", "result": json.dumps({
                    "content": f"Sorry, an error occurred: {str(e)}",
                    "steps": steps,
                    "response_id": None
                })}
                
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error in run_responses_agent: {str(e)}")
        logger.error(error_traceback)
        yield {"type": "content", "result": json.dumps({
            "content": f"Sorry, an error occurred: {str(e)}",
            "steps": steps,
            "response_id": response_id
        })}
