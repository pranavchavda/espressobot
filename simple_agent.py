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
import certifi # Import certifi module
import re # Import re for URL validation
import traceback # Import traceback for error handling

# Import SkuVault integration
from skuvault_tools import upload_shopify_product_to_skuvault, batch_upload_to_skuvault

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
        # Set explicit timeout to avoid hanging and disable SSL verification
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
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
        # Set explicit timeout to avoid hanging and disable SSL verification
        async with httpx.AsyncClient(timeout=15.0, verify=False) as client:
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

async def introspect_admin_schema(query, filter_types=None):
    """Introspect the Shopify Admin API schema using the MCP server"""
    if filter_types is None:
        filter_types = ["all"]
    try:
        return await mcp_server.introspect_admin_schema(query, filter_types)
    except Exception as e:
        print(f"Error introspecting schema: {e}")
        return {"errors": [{"message": str(e)}]}

async def search_dev_docs(prompt):
    """Search Shopify developer documentation using the MCP server"""
    if not mcp_server:
        return {"error": "MCP server not available"}
    try:
        return await mcp_server.search_dev_docs(prompt)
    except Exception as e:
        print(f"Error calling search_dev_docs: {e}")
        return {"error": str(e)}

# Function to fetch product copy guidelines

# Helper for Perplexity MCP
async def ask_perplexity(messages):
    from mcp_server import perplexity_mcp_server
    try:
        return await perplexity_mcp_server.perplexity_ask(messages)
    except Exception as e:
        print(f"Error calling Perplexity MCP: {e}")
        return {"error": str(e)}

async def get_product_copy_guidelines():
    """Read product_copy_guidelines.md and return its content (up to 4000 chars, with a 'truncated' flag)."""
    try:
        with open("product_copy_guidelines.md", "r") as f:
            content = f.read()
        return {"content": content[:4000], "truncated": len(content) > 4000}
    except Exception as e:
        print(f"Error reading product copy guidelines: {e}")
        return {"error": str(e)}

# Function to upload products to SkuVault
async def upload_to_skuvault(product_sku):
    """Upload a product from Shopify to SkuVault using its SKU"""
    try:
        result = await upload_shopify_product_to_skuvault(product_sku)
        return result
    except Exception as e:
        error_msg = f"Error uploading product to SkuVault: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"success": False, "message": error_msg}

async def upload_batch_to_skuvault(product_skus):
    """Upload multiple products from Shopify to SkuVault using their SKUs"""
    try:
        result = await batch_upload_to_skuvault(product_skus)
        return result
    except Exception as e:
        error_msg = f"Error batch uploading products to SkuVault: {str(e)}"
        print(f"ERROR: {error_msg}")
        return {"success": False, "message": error_msg}

# Function to fetch URL content with curl
async def fetch_url_with_curl(url: str):
    """Fetch the raw content of a public HTTP/HTTPS URL using curl. Returns up to 4000 characters."""
    # Only allow http/https
    if not url.lower().startswith(('http://', 'https://')):
        return {"error": "Only HTTP and HTTPS URLs are allowed."}
    # Block local/internal addresses
    if re.search(r'(localhost|127\.0\.0\.1|::1|0\.0\.0\.0|169\.254\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)', url):
        return {"error": "Local and internal network addresses are not allowed."}
    try:
        import subprocess
        proc = await asyncio.create_subprocess_exec(
            'curl', '-L', '--max-time', '8', '--silent', '--show-error', '--user-agent', 'ShopifyAgent/1.0', url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        except asyncio.TimeoutError:
            proc.kill()
            return {"error": "Request timed out."}
        if proc.returncode != 0:
            return {"error": f"curl error: {stderr.decode('utf-8')[:200]}"}
        content = stdout.decode('utf-8', errors='replace')[:4000]
        return {"content": content, "truncated": len(content) == 4000}
    except Exception as e:
        return {"error": str(e)}

# Import Open Box listing tool
from open_box_listing_tool import create_open_box_listing_single

# Define available tools
TOOLS = [
    {
        "name": "execute_python_code",
        "type": "function",
        "function": {
            "name": "execute_python_code",
            "description": "Execute Python code and return the results. This allows you to perform data analysis, calculations, and generate visualizations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute. The code should be complete and executable."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "name": "create_open_box_listing_single",
        "type": "function",
        "function": {
        "name": "create_open_box_listing_single",
        "description": "Duplicate a single product as an Open Box listing. The caller must supply a product identifier (title, handle, ID or SKU), the unit’s serial number, a condition suffix (e.g. 'Excellent', 'Scratch & Dent'), **and** either an explicit price or a discount percentage.",
        "parameters": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string", "description": "Product title / handle / numeric ID / SKU to duplicate"},
                "serial_number": {"type": "string", "description": "Unit serial number to embed in title & description."},
                "suffix": {"type": "string", "description": "Condition descriptor appended to the title (e.g. 'Excellent')."},
                "price": {"type": "number", "description": "Explicit Open Box price in CAD dollars.", "default": None},
                "discount_pct": {"type": "number", "description": "Percent discount off the product’s higher of price / compareAtPrice.", "default": None},
                "note": {"type": "string", "description": "Optional note to prepend to the description.", "default": None}
            },
            "required": ["identifier", "serial_number", "suffix"]
        }
    }
    },
    {
        "name": "get_product_copy_guidelines",
        "type": "function",
        "function": {
            "name": "get_product_copy_guidelines",
            "description": "Return the latest product copywriting and metafield guidelines for iDrinkCoffee.com as Markdown.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "name": "fetch_url_with_curl",
        "type": "function",
        "function": {
            "name": "fetch_url_with_curl",
            "description": "Fetch the raw content of a public HTTP/HTTPS URL using curl. Useful for retrieving HTML, JSON, or plain text from the web. Only use for public internet resources.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The HTTP or HTTPS URL to fetch."
                    }
                },
                "required": ["url"]
            }
        }
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
            "description": "Search Shopify developer documentation",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "name": "perplexity_ask",
        "type": "function",
        "function": {
            "name": "perplexity_ask",
            "description": "Ask Perplexity AI a question to get real-time information and analysis. Use this for current information, complex analysis, or when you need to verify or research something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["role", "content"]
                        },
                        "description": "Array of conversation messages"
                    }
                },
                "required": ["messages"]
            }
        }
    },
    {
        "name": "upload_to_skuvault",
        "type": "function",
        "function": {
            "name": "upload_to_skuvault",
            "description": "Upload a product to SkuVault using their API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_sku": {
                        "type": "string",
                        "description": "The SKU of the Shopify product to upload to SkuVault"
                    }
                },
                "required": ["product_sku"]
            }
        }
    },
    {
        "name": "upload_batch_to_skuvault",
        "type": "function",
        "function": {
            "name": "upload_batch_to_skuvault",
            "description": "Upload multiple products to SkuVault using their API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_skus": {
                        "type": "string",
                        "description": "Comma-separated list of Shopify product SKUs to upload to SkuVault"
                    }
                },
                "required": ["product_skus"]
            }
        }
    }
]

# Run the Shopify agent with a custom implementation
async def run_simple_agent(user_input, history=[]):
    # Initialize variables
    step_count = 0
    steps = []
    import json  # Ensure json is available in this scope

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
   • Update SKU or cost      → `inventoryItemUpdate` (fields: `sku`, `cost`)  
   • Upload image            → `productCreateMedia`  
   • Delete product          → `productUpdate` (set `status` to `ARCHIVED` - never delete products)
   • Updating Shipping Weight → `inventoryItemUpdate` with the measurement field (weight.unit and weight.value). 

8. **IDC Jargon**
   • When asked add something to preorder, add the "preorder-2-weeks" tag to the product, and any tag that begins with "shipping-nis" (such as shipping-nis-April), similarly, when removing something from preorder, remove the "preorder-2-weeks" tag and any tag that begins with "shipping-nis" (such as shipping-nis-April).
     Also ask the user if they want to change the inventory policy of that product to DENY when something is taken out of preorder, when something is added to preorder, inventory policy should be set to ALLOW, without needing to ask the user.
   • Sale End Date: If asked to add a promotion or sale end date to any product, it can be added to the product's inventory.ShappifySaleEndDate metafiled (Namespace is inventory and key is ShappifySaleEndDate; it is single line text) Format example: 2023-08-04T03:00:00Z (For 3 AM on August 4, 2023) 
   • For US/USD price updates, use the pricelist ID: `gid://shopify/PriceList/18798805026`.
   
   
9. **COST HANDLING**  
   • Cost lives on `InventoryItem.cost` (string). Update with `inventoryItemUpdate`.  
   • Never attempt to set cost via `productVariantsBulkUpdate`.

10. **STATUS & TAG DEFAULTS**  
   • All newly-created products must be `DRAFT` status with required base fields.  
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

────────────────────────────────────────
END OF SYSTEM PROMPT

"""

    # Add system message to history
    formatted_messages = [{"role": "system", "content": system_message}] + formatted_history
    formatted_messages.append({"role": "user", "content": user_input})

    # Step logs for tracking agent progress
    steps = []

    # Main agent loop
    step_count = 0
    max_steps = 100  # Prevent infinite loops
    final_response = "I'm sorry, I couldn't complete the task due to an error."

    try:
        while step_count < max_steps:
            step_count += 1
            print(f"Running agent step {step_count}")

            # Call the model
            try:
                # Pass formatted messages directly to the API
                response = client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                    messages=formatted_messages,
                    tools=TOOLS,
                    tool_choice="auto"
                )
            except Exception as e:
                # Check if this is a cancellation
                if isinstance(e, asyncio.CancelledError):
                    raise  # Re-raise CancelledError to propagate it
                raise e

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

                # Check for cancellation before processing tool calls
                if asyncio.current_task().cancelled():
                    raise asyncio.CancelledError()

                # Process each tool call
                for tool_call in message.tool_calls:
                    # Check for cancellation before each tool call
                    if asyncio.current_task().cancelled():
                        raise asyncio.CancelledError()

                    try:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        print(f"Executing tool call {tool_call.id}: {function_name} with arguments: {function_args}")
                        # Execute the appropriate tool function
                        if function_name == "introspect_admin_schema":
                            tool_output = await introspect_admin_schema(
                                function_args["query"],
                                function_args.get("filter_types")
                            )
                        elif function_name == "search_dev_docs":
                            tool_output = await search_dev_docs(function_args["prompt"])
                        elif function_name == "run_shopify_query":
                            tool_output = await execute_shopify_query(function_args["query"], function_args.get("variables"))
                        elif function_name == "run_shopify_mutation":
                            tool_output = await execute_shopify_mutation(function_args["query"], function_args.get("variables"))
                        elif function_name == "get_product_copy_guidelines":
                            tool_output = await get_product_copy_guidelines()
                        elif function_name == "fetch_url_with_curl":
                            tool_output = await fetch_url_with_curl(function_args["url"])
                        elif function_name == "perplexity_ask":
                            tool_output = await ask_perplexity(function_args.get("messages", []))
                        elif function_name == "upload_to_skuvault":
                            tool_output = await upload_to_skuvault(function_args.get("product_sku", ""))
                        elif function_name == "upload_batch_to_skuvault":
                            tool_output = await upload_batch_to_skuvault(function_args.get("product_skus", ""))
                        elif function_name == "execute_python_code":
                            # Import code_interpreter at runtime to avoid circular imports
                            from code_interpreter import execute_code
                            tool_output = execute_code(function_args.get("code", ""))
                        elif function_name == "create_open_box_listing_single":
                                tool_output = create_open_box_listing_single(
                                    function_args.get("identifier"),
                                    function_args.get("serial_number"),
                                    function_args.get("suffix"),
                                    function_args.get("price"),
                                    function_args.get("discount_pct"),
                                    function_args.get("note")
        )
                        else:
                            tool_output = {"error": f"Unknown tool: {function_name}"}
                        # Ensure tool_output is serializable
                        serializable_output = tool_output.model_dump() if hasattr(tool_output, "model_dump") else tool_output
                        steps.append({
                            "step": f"Tool call: {function_name}",
                            "input": function_args,
                            "output": serializable_output
                        })

                        # Add the function response to messages correctly linked to the tool call
                        # Log tool output for debugging
                        print(f"[DEBUG] Tool '{function_name}' output: {serializable_output}")
                        formatted_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                tool_output.model_dump() if hasattr(tool_output, "model_dump") else (
                                    tool_output.text if hasattr(tool_output, "text") else (
                                        str(tool_output) if not isinstance(tool_output, (dict, list, str, int, float, bool, type(None))) else tool_output
                                    )
                                )
                            )
                        })
                    except Exception as e:
                        print(f"[ERROR] Error executing tool {tool_call.function.name}: {str(e)}")
                        error_msg = f"Error executing tool {tool_call.function.name}: {str(e)}"
                        formatted_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps({"error": error_msg})
                        })
                        steps.append({
                            "step": f"Error in tool call: {tool_call.function.name}",
                            "input": json.loads(tool_call.function.arguments) if hasattr(tool_call.function, "arguments") else {},
                            "output": {"error": error_msg}
                        })

                # After tool call, let the outer loop run again to give GPT the tool results
                continue

            # If no tool calls, we're done
            # Only apply Perplexity-specific extraction for Perplexity tool calls
            if steps and "perplexity_ask" in steps[-1].get("step", ""):
                tool_result = steps[-1]["output"]
                # If Perplexity result is a dict with 'content' as a list of dicts
                if isinstance(tool_result, dict) and isinstance(tool_result.get("content"), list):
                    texts = [item.get("text", "") for item in tool_result["content"] if isinstance(item, dict)]
                    final_response = "\n\n".join([t for t in texts if t.strip()])
                    if not final_response:
                        final_response = tool_result.get("error") or "I'm sorry, Perplexity did not return any content."
                    break
                elif isinstance(tool_result, dict) and tool_result.get("error"):
                    final_response = tool_result["error"]
                    break
                # Otherwise, let the loop continue so the model can interpret

            # For all other tool calls, only break if the model returns non-empty content
            final_response = (message.content or "").strip()
            if final_response:
                break
        # End of main loop
        # If we exit the loop and have no response, fallback
        if not final_response:
            if steps and "output" in steps[-1]:
                output = steps[-1]["output"]
                if isinstance(output, (dict, list)):
                    import json
                    final_response = "Result:\n```json\n" + json.dumps(output, indent=2) + "\n```"
                else:
                    final_response = str(output)
            else:
                final_response = "I'm sorry, I couldn't complete the task due to an error."

    except Exception as e:
        import traceback
        print(f"Error in agent execution: {e}")
        print(traceback.format_exc())
        final_response = f"Sorry, an error occurred: {str(e)}" if str(e) else ""

    # Generate suggestions using gpt-4.1-nano
    suggestions = []
    try:
        # Check for cancellation before generating suggestions
        if asyncio.current_task().cancelled():
            raise asyncio.CancelledError()
            
        print("Generating suggestions with gpt-4.1-nano...")
        # Make a separate call to generate suggestions
        suggestion_response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates 3 brief follow-up suggestions based on the conversation context. Keep suggestions short (2-5 words) and relevant. The Suggestions should be from the user's perspective as a reply to the AI's message. Particularly, if the AI asks a Yes/No question, make sure a direct response is included. if a plausible answer is 'ok', or 'go ahead', or 'proceed' and so on, include that for sure."},
                {"role": "assistant", "content": final_response}  # Use the Agent's message for context
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
                },
                {
                    "type": "function",
                    "function": {
                        "name": "perplexity_ask",
                        "description": "Ask Perplexity AI a question to get real-time information and analysis. Use this for current information, complex analysis, or when you need to verify or research something.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "messages": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "role": {"type": "string"},
                                            "content": {"type": "string"}
                                        }
                                    },
                                    "description": "Array of conversation messages"
                                }
                            },
                            "required": ["messages"]
                        }
                    }
                },
            ],
            tool_choice={"type": "function", "function": {"name": "suggested_responses"}}
        )
        
        # Extract suggestions from the response
        if (hasattr(suggestion_response, 'choices') and 
            suggestion_response.choices and 
            hasattr(suggestion_response.choices[0], 'message') and
            hasattr(suggestion_response.choices[0].message, 'tool_calls') and
            suggestion_response.choices[0].message.tool_calls):
            tool_call = suggestion_response.choices[0].message.tool_calls[0]
            suggestions = json.loads(tool_call.function.arguments).get('Suggestions', [])
            print(f"Generated suggestions: {suggestions}")
    except Exception as e:
        print(f"Error generating suggestions: {str(e)}")
        print(traceback.format_exc())

    # Return the final result
    return {
        'final_output': final_response,
        'steps': steps,
        'suggestions': suggestions
    }