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
    get_openai_client,
    execute_shopify_query,
    execute_shopify_mutation,
    introspect_admin_schema,
    search_dev_docs,
    get_current_datetime_est,
)

# Import all tools from simple_agent
from simple_agent import TOOLS as SIMPLE_AGENT_TOOLS
TOOLS = SIMPLE_AGENT_TOOLS


async def run_responses_agent(
    message: str,
    previous_response_id: Optional[str] = None,
    history: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Run an agent using the OpenAI Responses API, with logic, tools, and system message matching simple_agent, but using the OpenAI Responses API for completions.
    Returns a dict with 'steps', 'final_output', 'response_id', and 'suggestions'.
    """
    import json
    import asyncio
    # Convert history to OpenAI chat format if provided (for full parity with simple_agent)
    formatted_history = []
    if history:
        for item in history:
            role = item.get('role', 'user')
            content = item.get('content', '')
            formatted_history.append({"role": role, "content": content})
    # System message is copied exactly from simple_agent
    current_time = get_current_datetime_est()
    shop_url = os.environ.get("SHOPIFY_SHOP_URL", "Unknown")
    system_message = f"""
You are “IDC-Shopify-Agent”, the production Shopify assistant for iDrinkCoffee.com. 
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
   • Before every new field/mutation/query you haven’t already verified this session, call `introspect_admin_schema` and cache the result in memory.  
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

You have access to several tools:

1. get_product_copy_guidelines - Return the latest product copywriting and metafield guidelines for iDrinkCoffee.com as Markdown.
2. fetch_url_with_curl - Fetch the raw content of a public HTTP/HTTPS URL using curl (for retrieving HTML, JSON, or plain text from the web).
3. run_shopify_query - Execute GraphQL queries against the Shopify Admin API to fetch data.
4. run_shopify_mutation - Execute GraphQL mutations against the Shopify Admin API to modify data.
5. introspect_admin_schema - Get information about the Shopify Admin API schema (types, queries, mutations).
6. search_dev_docs - Search Shopify developer documentation for guidance.
7. perplexity_ask - Get real-time information and analysis from Perplexity AI (for current events, complex research, or when you need to verify or research something).
8. upload_to_skuvault - Upload a product to SkuVault using their API.
9. upload_batch_to_skuvault - Upload multiple products to SkuVault using their API.
10. create_open_box_listing_single - Duplicate a single product as an Open Box listing. The caller must supply a product identifier (title, handle, ID or SKU), the unit’s serial number, a condition suffix (e.g. 'Excellent', 'Scratch & Dent'), **and** either an explicit price or a discount percentage.

You are a helpful Shopify assistant for the shop: iDrinkCoffee.com. Current date/time: {current_time}.
"""
    # Build input_items for the Responses API
    input_items: List[Dict[str, Any]] = []
    if formatted_history:
        for msg in formatted_history:
            input_items.append({
                "type": "message",
                "role": msg["role"],
                "content": [{"type": "input_text", "text": msg["content"]}],
            })
    input_items.append({
        "type": "message",
        "role": "user",
        "content": [{"type": "input_text", "text": message}],
    })
    steps: List[Dict[str, Any]] = []
    resp_id = previous_response_id
    max_steps = 100
    step_count = 0
    final_output = ""
    while step_count < max_steps:
        step_count += 1
        import openai
        sync_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        response = sync_client.responses.create(
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
                input_items.append({
                    "type": "function_call",
                    "call_id": call_id,
                    "name": fname,
                    "arguments": fc.arguments
                })
                args = json.loads(fc.arguments)
                steps.append({"type": "tool", "name": fname, "input": args})
                # Tool execution logic (all tools from simple_agent)
                if fname == "run_shopify_query":
                    result = await execute_shopify_query(args.get("query", ""), args.get("variables", {}))
                elif fname == "run_shopify_mutation":
                    result = await execute_shopify_mutation(args.get("query", ""), args.get("variables", {}))
                elif fname == "introspect_admin_schema":
                    try:
                        raw = await introspect_admin_schema(args.get("query", ""), args.get("filter_types", ["all"]))
                        # Extract only text snippets from schema result
                        if isinstance(raw, dict) and raw.get("content"):
                            items = raw.get("content", [])
                            text_content = "\n\n".join(
                                it.get("text", "") for it in items if isinstance(it, dict)
                            )
                            result = {"text": text_content}
                        else:
                            result = raw
                    except Exception as e:
                        print(f"Error in introspect_admin_schema: {e}")
                        result = {"text": f"Error accessing Shopify schema: {str(e)}. Please try again later or check your connection."}
                elif fname == "search_dev_docs":
                    try:
                        result = await search_dev_docs(args.get("prompt", ""))
                    except Exception as e:
                        print(f"Error in search_dev_docs: {e}")
                        result = {"content": f"Error searching dev docs: {str(e)}. Please try again later or check your connection."}
                elif fname == "get_product_copy_guidelines":
                    from simple_agent import get_product_copy_guidelines
                    result = await get_product_copy_guidelines()
                elif fname == "fetch_url_with_curl":
                    from simple_agent import fetch_url_with_curl
                    result = await fetch_url_with_curl(args.get("url", ""))
                elif fname == "perplexity_ask":
                    from simple_agent import ask_perplexity
                    # Flatten messages for Perplexity or fallback to history
                    raw_msgs = args.get("messages")
                    if not raw_msgs:
                        msgs = formatted_history + [{"role": "user", "content": message}]
                    else:
                        msgs = []
                        for m in raw_msgs:
                            role = m.get("role", "")
                            content_val = m.get("content")
                            if isinstance(content_val, list):
                                text = "".join(part.get("text", "") for part in content_val)
                            else:
                                text = content_val or ""
                            msgs.append({"role": role, "content": text})
                    result = await ask_perplexity(msgs)
                elif fname == "upload_to_skuvault":
                    from skuvault_tools import upload_shopify_product_to_skuvault
                    result = await upload_shopify_product_to_skuvault(args.get("product_sku", ""))
                elif fname == "upload_batch_to_skuvault":
                    from skuvault_tools import batch_upload_to_skuvault
                    result = await batch_upload_to_skuvault(args.get("product_skus", ""))
                elif fname == "create_open_box_listing_single":
                    from open_box_listing_tool import create_open_box_listing_single
                    logging.info(f"Calling create_open_box_listing_single with args: {args}") # Log the arguments
                    result = create_open_box_listing_single(
                        args.get("identifier", ""),
                        args.get("serial_number", ""),
                        args.get("suffix", ""),
                        args.get("price", None),
                        args.get("discount_pct", None),
                        args.get("note", None)
                    )
                else:
                    result = {"error": f"Unknown function: {fname}"}
                steps.append({"type": "tool_result", "name": fname, "output": result})
                payload = result.model_dump() if hasattr(result, "model_dump") else result
                input_items.append({
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": json.dumps(payload),
                })
            continue
        final_output = response.output_text
        steps.append({"type": "final", "output": final_output})
        break
    # Generate suggestions (same logic as simple_agent)
    suggestions = []
    try:
        if asyncio.current_task().cancelled():
            raise asyncio.CancelledError()
        client = get_openai_client()
        suggestion_response = await client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates 3 brief follow-up suggestions based on the conversation context. Keep suggestions short (2-5 words) and relevant. The Suggestions should be from the user's perspective as a reply to the AI's message. Particularly, if the AI asks a Yes/No question, make sure a direct response is included. if a plausible answer is 'ok', or 'go ahead', or 'proceed' and so on, include that for sure."},
                {"role": "assistant", "content": final_output}
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "suggested_responses",
                        "description": "Provide 2-3 suggested follow-up messages for the user",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "Suggestions": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of 2-3 suggested responses"
                                }
                            },
                            "required": ["Suggestions"]
                        }
                    }
                }
            ],
            tool_choice={"type": "function", "function": {"name": "suggested_responses"}}
        )
        if (hasattr(suggestion_response, 'choices') and 
            suggestion_response.choices and 
            hasattr(suggestion_response.choices[0], 'message') and
            hasattr(suggestion_response.choices[0].message, 'tool_calls') and
            suggestion_response.choices[0].message.tool_calls):
            tool_call = suggestion_response.choices[0].message.tool_calls[0]
            suggestions = json.loads(tool_call.function.arguments).get('Suggestions', [])
    except Exception as e:
        print(f"Error generating suggestions: {str(e)}")
        import traceback
        print(traceback.format_exc())
    return {
        'final_output': final_output,
        'steps': steps,
        'suggestions': suggestions,
        'response_id': resp_id
    }
