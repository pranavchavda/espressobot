"""
This commit modifies the agent to support streaming responses from OpenAI and includes logic for handling tool calls and suggestions in streaming mode.
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
    # Validate input
    if not messages:
        return {"error": "perplexity_ask requires non-empty 'messages' parameter."}
    try:
        raw_res = await perplexity_mcp_server.perplexity_ask(messages)
        # Convert CallToolResult to dict
        if hasattr(raw_res, "model_dump"):
            return raw_res.model_dump()
        res = {}
        if hasattr(raw_res, "meta"):
            res["meta"] = raw_res.meta
        if hasattr(raw_res, "content"):
            res["content"] = [
                {"type": getattr(c, "type", None), "text": getattr(c, "text", None), "annotations": getattr(c, "annotations", None)}
                for c in raw_res.content
            ]
        if hasattr(raw_res, "isError"):
            res["isError"] = raw_res.isError
        return res
    except Exception as e:
        print(f"Error calling Perplexity MCP: {e}")
        import traceback; traceback.print_exc()
        return {"error": str(e)}

async def get_product_copy_guidelines():
    """Read product_copy_guidelines.md and return its content."""
    try:
        with open("product_copy_guidelines.md", "r") as f:
            content = f.read()
        return {"content": content, "truncated": False}
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
TOOLS = [{
    "name": "execute_python_code",
    "type": "function",
    "function": {
        "name": "execute_python_code",
        "description":
        "Execute Python code and return the results. This allows you to perform data analysis, calculations, and generate visualizations.",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type":
                    "string",
                    "description":
                    "The Python code to execute. The code should be complete and executable."
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
async def run_simple_agent(prompt, history=[], streaming=False):
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
You are an expert at executing your mission: which is to perform catalog and storefront tasks flawlessly, quickly, and with zero guesswork.

────────────────────────────────────────
FUNDAMENTAL PRINCIPLES
────────────────────────────────────────
1. Thinking Process:
   You MUST USE the tags <THINKING> and </THINKING> to outline your thought process. The content between these tags will not be sent to the user.
   You are encouraged to use this feature to explain your reasoning and thought process to yourself, and to plan your next steps. Use this feature liberally. 
   It will be removed from the final response to the user, it will only be logged for OpenAI to evaluate your performance.
   Responses that begin without <THINKING> and </THINKING> tags will be be partially penalized in the next training iteration. This doesn't apply to O series reasoning models.

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
     (b) a compact plan as part of your thinking process **plus** the necessary tool calls.  
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
   • Prices are always in CAD and don't need to use a separate price list, only use a price list when a currency is specified or a currency other than CAD is specified.



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
• **Format**: Your thought process should be outlined in <THINKING> tags, your throught process should include a plan, actions (tool calls), and a result. The result must be outside of the <THINKING> tags for the user to see it.
• **Tone**: concise, friendly but professional, no waffle. 
• **Citations**: cite tool call IDs inline where useful.

────────────────────────────────────────
FAIL-SAFES
────────────────────────────────────────
• If a mutation fails, immediately show the error message, introspect that mutation, and retry only once with corrected arguments.  
• If still failing, summarise the blocker and ask the user how to proceed.

You have access to several tools:

1. get_product_copy_guidelines - Return the latest product copywriting and metafield guidelines for iDrinkCoffee.com as Markdown. Always pull this up when asked to create a product.
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
    formatted_messages.append({"role": "user", "content": prompt})

    # Step logs for tracking agent progress
    steps = []

    # Main agent loop
    step_count = 0
    max_steps = 100  # Prevent infinite loops
    final_response = "I'm sorry, I couldn't complete the task due to an error."

    # Define available tool functions
    tool_functions = {
        "introspect_admin_schema": introspect_admin_schema,
        "search_dev_docs": search_dev_docs,
        "run_shopify_query": execute_shopify_query,
        "run_shopify_mutation": execute_shopify_mutation,
        "get_product_copy_guidelines": get_product_copy_guidelines,
        "fetch_url_with_curl": fetch_url_with_curl,
        "perplexity_ask": ask_perplexity,
        "upload_to_skuvault": upload_to_skuvault,
        "upload_batch_to_skuvault": upload_batch_to_skuvault,
        "execute_python_code": lambda code: asyncio.run(execute_code(code)),  # Fix: Execute code in the event loop
        "create_open_box_listing_single": create_open_box_listing_single
    }

    try:
        while step_count < max_steps:
            step_count += 1
            print(f"Running agent step {step_count}")

            # Call the model
            try:
                if streaming:
                    # Streaming mode
                    response = client.chat.completions.create(
                        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                        messages=formatted_messages,
                        tools=TOOLS,
                        reasoning_effort="medium",
                        tool_choice="auto",
                        stream=True
                    )

                    # Handle streaming chunks
                    current_content = ""
                    tool_calls_buffer = []
                    steps = []

                    async for chunk in response:
                        delta = chunk.choices[0].delta

                        # Process content chunks
                        if hasattr(delta, 'content') and delta.content:
                            current_content += delta.content
                            yield {
                                'type': 'content',
                                'delta': delta.content
                            }

                        # Process tool calls
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tool_call in delta.tool_calls:
                                # Extract and handle tool call information
                                if tool_call.index >= len(tool_calls_buffer):
                                    tool_calls_buffer.append({
                                        'id': tool_call.id if hasattr(tool_call, 'id') else None,
                                        'type': 'function',
                                        'function': {'name': '', 'arguments': ''}
                                    })

                                if hasattr(tool_call, 'function'):
                                    if hasattr(tool_call.function, 'name') and tool_call.function.name:
                                        tool_calls_buffer[tool_call.index]['function']['name'] = tool_call.function.name
                                        yield {
                                            'type': 'tool_call',
                                            'name': tool_call.function.name,
                                            'status': 'started'
                                        }

                                    if hasattr(tool_call.function, 'arguments') and tool_call.function.arguments:
                                        current_args = tool_calls_buffer[tool_call.index]['function']['arguments']
                                        tool_calls_buffer[tool_call.index]['function']['arguments'] = current_args + tool_call.function.arguments

                    # Process any tool calls that were completed
                    for tool_call in tool_calls_buffer:
                        if tool_call['function']['name'] and tool_call['function']['arguments']:
                            try:
                                fn_name = tool_call['function']['name']
                                args = json.loads(tool_call['function']['arguments'])

                                # Add to steps
                                steps.append({
                                    'type': 'tool', 
                                    'name': fn_name,
'input': args
                                })

                                # Execute the tool
                                yield {
                                    'type': 'tool_call',
                               'name': fn_name,
                                    'args': args,
                                    'status': 'executing'
                                }

                                # Get the corresponding tool function
                                tool_to_call = next((t for t in TOOLS if t['function']['name'] == fn_name), None)
                                if tool_to_call:
                                    tool_fn = tool_functions[fn_name]
                                    result = await tool_fn(**args)

                                    # Add tool result to steps
                                    steps.append({
                                        'type': 'tool_result',
                                        'name': fn_name,
                                        'output': result
                                    })

                                    yield {
                                        'type': 'tool_call',
                                        'name': fn_name,
                                        'result': result,
                                        'status': 'completed'
                                    }

                                    # Add this result to messages for the agent
                                    formatted_messages.append({
                                        "role": "assistant",
                                        "content": None,
                                        "tool_calls": [{
                                            "id": tool_call["id"] or f"call_{len(formatted_messages)}",
                                            "type": "function",
                                            "function": {
                                                "name": fn_name,
                                                "arguments": tool_call['function']['arguments']
                                            }
                                        }]
                                    })

                                    formatted_messages.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call["id"] or f"call_{len(formatted_messages)-1}",
                                        "content": str(result)
                                    })
                            except Exception as e:
                                print(f"Error executing tool {tool_call['function']['name']}: {e}")
                                # Add error to steps
                                steps.append({
                                    'type': 'tool_result',
                                    'name': tool_call['function']['name'],
                                    'output': f"Error: {str(e)}"
                                })

                                yield {
                                    'type': 'tool_call',
                                    'name': tool_call['function']['name'],
                                    'error': str(e),
                                    'status': 'error'
                                }

                    # If we had tool calls, make a follow-up call to get final response
                    if tool_calls_buffer:
                        # Make a follow-up call to get the final response
                        response = client.chat.completions.create(
                            model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                            messages=formatted_messages,
                            tools=TOOLS,
                            reasoning_effort="medium",
                            tool_choice="auto",
                            stream=True
                        )

                        current_content = ""
                        async for chunk in response:
                            delta = chunk.choices[0].delta
                            if hasattr(delta, 'content') and delta.content:
                                current_content += delta.content
                                yield {
                                    'type': 'content',
                                    'delta': delta.content
                                }

                    # Extract suggested follow-up questions
                    suggestions = []
                    try:
                        # Extract suggestions from the final content
                        suggestion_match = re.search(r'(?:Suggested follow-up questions:|Suggested questions:|Follow-up questions:)(.*?)(?:$|(?:\n\n))', current_content, re.DOTALL)
                        if suggestion_match:
                            suggestion_text = suggestion_match.group(1).strip()
                            suggestions = [q.strip().strip('-*•').strip() for q in suggestion_text.split('\n') if q.strip()]
                            suggestions = [q for q in suggestions if len(q) > 0 and q != ""]

                            # Remove suggestions section from content if found
                            current_content = re.sub(r'\n*(?:Suggested follow-up questions:|Suggested questions:|Follow-up questions:)(.*?)(?:$|(?:\n\n))', '', current_content, flags=re.DOTALL)
                            current_content = current_content.strip()

                            yield {
                                'type': 'suggestions',
                                'suggestions': suggestions
                            }
                    except Exception as e:
                        print(f"Error extracting suggestions: {e}")

                    # Return final content
                    final_output = current_content

                    # Return result structure
                    return {
                        'response': final_output,
                        'final_output': final_output,
                        'steps': steps,
                        'suggestions': suggestions
                    }
                else:
                    # Non-streaming mode (original behavior)
                    response = client.chat.completions.create(
                        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                        messages=formatted_messages,
                        tools=TOOLS,
                        reasoning_effort="medium",
                        tool_choice="auto"
                    )

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
                                    tool_output = execute_code(
                                        function_args.get("code", ""))
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
                            final_response = "Result:\n```json\n" + json.dumps(output, indent=2) + "\n```"```"