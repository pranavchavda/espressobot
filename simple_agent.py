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
import re # Import re for URL validation
import traceback # Import traceback for error handling

# Import memory service
from memory_service import memory_service

# Import SkuVault integration
from skuvault_tools import upload_shopify_product_to_skuvault, batch_upload_to_skuvault

# Import our custom MCP server implementations
from mcp_server import mcp_server, memory_mcp_server

# Indicate that MCP is available through our custom implementation
MCP_AVAILABLE = True

# Configure OpenAI client
# client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
# Use AsyncOpenAI for async operations
client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

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

async def execute_shopify_mutation(mutation=None, variables=None, query=None):
    """Execute a Shopify GraphQL mutation with the provided variables.
    Can accept the mutation string via either 'mutation' or 'query' keyword arguments.
    """
    if mutation is None and query is not None:
        mutation = query
    elif mutation is None and query is None:
        raise ValueError("No mutation string provided. Please use 'mutation' or 'query' argument.")

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
        print(f"[DEBUG] Calling mcp_server.introspect_admin_schema with query: {query}")
        result = await mcp_server.introspect_admin_schema(query, filter_types)
        
        # Log the returned result structure for debugging
        print(f"[DEBUG] introspect_admin_schema result type: {type(result)}")
        if isinstance(result, dict):
            content_count = len(result.get("content", []))
            print(f"[DEBUG] introspect_admin_schema result has {content_count} content items")
            
            # Log the first content item (truncated)
            if content_count > 0:
                first_item = result["content"][0]
                text_length = len(first_item.get("text", ""))
                print(f"[DEBUG] First content item text length: {text_length} chars")
                print(f"[DEBUG] First content item text excerpt: {first_item.get('text', '')[:200]}...")
        
        return result
    except Exception as e:
        print(f"Error introspecting schema: {e}")
        traceback.print_exc()  # Add stack trace for better debugging
        return {"errors": [{"message": str(e)}]}

async def search_dev_docs(prompt):
    """Search Shopify developer documentation using the MCP server"""
    if not mcp_server:
        return {"error": "MCP server not available"}
    try:
        print(f"[DEBUG] Calling mcp_server.search_dev_docs with prompt: {prompt}")
        result = await mcp_server.search_dev_docs(prompt)
        
        # At this point result should already be a properly serializable dictionary
        # Let's log its structure to verify
        print(f"[DEBUG] search_dev_docs result type: {type(result)}")
        if isinstance(result, dict):
            content_count = len(result.get("content", []))
            print(f"[DEBUG] search_dev_docs result has {content_count} content items")
            
            # Log the first content item (truncated)
            if content_count > 0:
                first_item = result["content"][0]
                text_length = len(first_item.get("text", ""))
                print(f"[DEBUG] First content item text length: {text_length} chars")
                print(f"[DEBUG] First content item text excerpt: {first_item.get('text', '')[:200]}...")
        
        return result
    except Exception as e:
        print(f"Error calling search_dev_docs: {e}")
        return {"error": str(e)}

# This duplicate function has been removed, we're using the implementation at line ~128

# Function to fetch product copy guidelines

# Helper for Perplexity MCP
async def ask_perplexity(messages):
    from mcp_server import perplexity_mcp_server
    # Validate input
    if not messages:
        return {"error": "perplexity_ask requires non-empty 'messages' parameter."}
    try:
        # The perplexity_mcp_server now returns a properly serializable dictionary
        return await perplexity_mcp_server.perplexity_ask(messages)
    except Exception as e:
        print(f"Error calling Perplexity MCP: {e}")
        import traceback; traceback.print_exc()
        return {"error": str(e)}
        
# Memory functions
async def store_user_memory(user_id, key, value, persist=True):
    """Store a memory for a specific user."""
    try:
        # Validate user_id is present
        if not user_id:
            return {"success": False, "error": "Missing user_id parameter"}
            
        return await memory_service.store_memory(user_id, key, value, persist)
    except Exception as e:
        print(f"Error storing user memory: {e}")
        return {"success": False, "error": str(e)}

async def retrieve_user_memory(user_id, key, default=None):
    """Retrieve a memory for a specific user."""
    try:
        # Validate user_id is present
        if not user_id:
            return {"success": False, "key": key, "value": default, "error": "Missing user_id parameter"}
            
        return await memory_service.retrieve_memory(user_id, key, default)
    except Exception as e:
        print(f"Error retrieving user memory: {e}")
        return {"success": False, "key": key, "value": default, "error": str(e)}

async def list_user_memories(user_id):
    """List all memories for a specific user."""
    try:
        # Validate user_id is present
        if not user_id:
            return {"success": False, "keys": [], "count": 0, "error": "Missing user_id parameter"}
            
        return await memory_service.list_memories(user_id)
    except Exception as e:
        print(f"Error listing user memories: {e}")
        return {"success": False, "keys": [], "count": 0, "error": str(e)}

async def delete_user_memory(user_id, key):
    """Delete a memory for a specific user."""
    try:
        # Validate user_id is present
        if not user_id:
            return {"success": False, "key": key, "error": "Missing user_id parameter"}
            
        return await memory_service.delete_memory(user_id, key)
    except Exception as e:
        print(f"Error deleting user memory: {e}")
        return {"success": False, "key": key, "error": str(e)}

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
    # Memory tools
    {
        "name": "store_user_memory",
        "type": "function",
        "function": {
            "name": "store_user_memory",
            "description": "Store a memory for the current user. Memories are user-specific and persist across sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's ID"
                    },
                    "key": {
                        "type": "string",
                        "description": "The memory key (e.g., 'preferences.theme', 'common_products')"
                    },
                    "value": {
                        "type": "object",
                        "description": "The value to store (can be any JSON-serializable object)"
                    },
                    "persist": {
                        "type": "boolean",
                        "description": "Whether to persist to database (default: true)"
                    }
                },
                "required": ["user_id", "key", "value"]
            }
        }
    },
    {
        "name": "retrieve_user_memory",
        "type": "function",
        "function": {
            "name": "retrieve_user_memory",
            "description": "Retrieve a memory for the current user. Returns the memory value or a default if not found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's ID"
                    },
                    "key": {
                        "type": "string",
                        "description": "The memory key to retrieve"
                    },
                    "default": {
                        "type": "object",
                        "description": "The default value to return if memory not found"
                    }
                },
                "required": ["user_id", "key"]
            }
        }
    },
    {
        "name": "list_user_memories",
        "type": "function",
        "function": {
            "name": "list_user_memories",
            "description": "List all memories for the current user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's ID"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "name": "delete_user_memory",
        "type": "function",
        "function": {
            "name": "delete_user_memory",
            "description": "Delete a memory for the current user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's ID"
                    },
                    "key": {
                        "type": "string",
                        "description": "The memory key to delete"
                    }
                },
                "required": ["user_id", "key"]
            }
        }
    },
    {
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
async def run_simple_agent(prompt: str, user_name: str, user_bio: str, history: list = None, tools_override: list = None, model_override: str = None, streaming: bool = False, user_id: int = None):
    # Initialize variables
    step_count = 0
    steps = []

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

You are "EspressoBot", the production Shopify and general purpose e-commerce assistant for iDrinkCoffee.com. 
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

2a. Multi-Tool Workflows
    Whenever you recognize that more than one tool could simplify, verify, or enrich the solution, proactively design and execute a chained workflow—for example, fetching raw data with  fetch_url_with_curl, then parsing or transforming it with  execute_python_code—even if the user did not explicitly request each tool.

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

Current date/time: {current_time}.
You are currently assisting {user_name}.
A little about {user_name}: {user_bio if user_bio else 'No bio provided.'}
User ID: {user_id if user_id else 'Unknown'}

────────────────────────────────────────
MEMORY CAPABILITIES
────────────────────────────────────────
You have access to user-specific memory functions that can help you maintain context across conversations:

1. `store_user_memory` - Store information about this user for future retrieval
2. `retrieve_user_memory` - Retrieve previously stored information about this user
3. `list_user_memories` - List all memories stored for this user
4. `delete_user_memory` - Delete a specific memory for this user

Memories are isolated by user_id, so each user has their own private memory space. Memories persist across
conversations and sessions, allowing you to remember important user preferences and information.

Good uses for memory:
- Store user preferences (e.g., preferred product categories, shipping preferences)
- Remember frequently accessed products or information
- Keep track of conversation history highlights
- Remember custom templates or formats the user prefers

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
        "execute_python_code": execute_code,  # Correctly reference the async function to be awaited
        "create_open_box_listing_single": create_open_box_listing_single,
        "store_user_memory": store_user_memory,
        "retrieve_user_memory": retrieve_user_memory,
        "list_user_memories": list_user_memories,
        "delete_user_memory": delete_user_memory
    }

    try:
        while step_count < max_steps:
            step_count += 1
            print(f"Running agent step {step_count}")

            # Call the model
            try:
                if streaming:
                    # Streaming mode
                    response = await client.chat.completions.create(
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

                    # For OpenAI SDK v1.x, we need to iterate over the async stream with async for
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

                    # Define a response_message for the streaming case to avoid the variable reference error
                    response_message = type('obj', (object,), {
                        'tool_calls': tool_calls_buffer,
                        'content': current_content
                    })

                    # First, add the assistant message with tool calls
                    if tool_calls_buffer:
                        formatted_messages.append({
                            'role': 'assistant',
                            'content': current_content,
                            'tool_calls': tool_calls_buffer
                        })
                        
                        # Then process the tool calls
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

                                    # Execute the tool function
                                    if fn_name in tool_functions:
                                        tool_result = await tool_functions[fn_name](**args)

                                        # Add result to steps
                                        steps.append({
                                            'type': 'tool_result',
                                            'name': fn_name,
                                            'output': tool_result
                                        })

                                        # Yield the tool result to client
                                        yield {
                                            'type': 'tool_result',
                                            'name': fn_name,
                                            'result': json.dumps(tool_result)
                                        }

                                        # Add tool result to messages - this should come after the assistant message with tool_calls
                                        formatted_messages.append({
                                            'role': 'tool',
                                            'tool_call_id': tool_call.get('id', ''),
                                            'name': fn_name,
                                            'content': json.dumps(tool_result)
                                        })

                                except Exception as e:
                                    print(f"Error processing tool call: {e}")
                                    yield {
                                        'type': 'error',
                                        'message': str(e)
                                    }
                                    # Make sure we have an assistant message with tool_calls before adding tool response
                                    if formatted_messages[-1]['role'] != 'assistant' or 'tool_calls' not in formatted_messages[-1]:
                                        print("Cannot add tool response without preceding assistant message with tool_calls")
                                    else:
                                        formatted_messages.append({
                                            'role': 'tool',
                                            'tool_call_id': tool_call.get('id', ''),
                                            'name': fn_name, 
                                            'content': f"Error: {str(e)}"
                                        })

                else:
                    # Non-streaming mode
                    response = client.chat.completions.create(
                        model=os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
                        messages=formatted_messages,
                        tools=TOOLS,
                        tool_choice="auto",
                    )

                    # Extract response message
                    response_message = response.choices[0].message
                    current_content = response_message.content

                    # Process tool calls
                    if response_message.tool_calls:
                        # First add the assistant message with tool calls
                        formatted_messages.append({
                            'role': 'assistant',
                            'content': current_content or "",
                            'tool_calls': response_message.tool_calls
                        })
                        
                        # Then process each tool call
                        tool_calls = response_message.tool_calls
                        for tool_call in tool_calls:
                            fn_name = tool_call.function.name
                            args = json.loads(tool_call.function.arguments)

                            # Add to steps
                            steps.append({
                                'type': 'tool',
                                'name': fn_name,
                                'input': args
                            })

                            # Execute the tool function
                            if fn_name in tool_functions:
                                tool_result = await tool_functions[fn_name](**args)

                                # Add result to steps
                                steps.append({
                                    'type': 'tool_result',
                                    'name': fn_name,
                                    'output': tool_result
                                })

                                # Add tool result to messages
                                formatted_messages.append({
                                    'role': 'tool',
                                    'tool_call_id': tool_call.id,
                                    'name': fn_name,
                                    'content': json.dumps(tool_result)
                                })
                            else:
                                print(f"Tool {fn_name} not found")
                                formatted_messages.append({
                                    'role': 'tool',
                                    'tool_call_id': tool_call.id,
                                    'name': fn_name,
                                    'content': f"Error: Tool {fn_name} not found"
                                })
                    else:
                        print("No tool calls in response")
                        if current_content:
                            formatted_messages.append({
                                'role': 'assistant',
                                'content': current_content
                            })

            except Exception as e:
                print(f"Error during OpenAI call: {e}")
                traceback.print_exc()
                final_response = f"I encountered an error: {str(e)}"
                break

            # Append assistant response to messages only if no tool calls were processed
            # (when there are tool calls, the assistant message is already added earlier)
            if not response_message.tool_calls and current_content:
                formatted_messages.append({
                    'role': 'assistant',
                    'content': current_content
                })
            elif not current_content and not response_message.tool_calls:
                print("No content in response")

            # Check if the agent has provided a final answer
            if not response_message.tool_calls:
                final_response = current_content
                break

        if step_count >= max_steps:
            final_response = "I couldn't complete the task in the maximum number of steps."

    except Exception as e:
        print(f"Error in main agent loop: {e}")
        final_response = f"I encountered an unexpected error: {str(e)}"

    # Return final result (not streamed)
    if not streaming:
        final_result = {
            'content': final_response,
            'steps': steps
        }
        yield {
            'type': 'content',
            'result': json.dumps(final_result)
        }
    else:
        # Yield the final content chunk so stream_chat.py can save it
        yield {
            'type': 'final',
            'content': final_response if final_response else ""  # Ensure content is always a string
        }

        # For streaming, after all content chunks are sent, send suggestions
        suggestions_list = []
        if final_response and not final_response.startswith("I encountered an error"):
            try:
                # Ensure client is passed to _generate_suggestions_async
                suggestions_list = await _generate_suggestions_async(formatted_messages, client)
            except Exception as e:
                print(f"Error generating suggestions in streaming mode: {e}")
        
        yield {
            'type': 'suggestions',
            'suggestions': suggestions_list
        }

        # Signal end of all data for this request
        yield {
            'type': 'stream_end'
        }
from typing import List, Dict

async def _generate_suggestions_async(conversation_history: List[Dict[str, str]], openai_client: openai.AsyncOpenAI):
    """
    Generates 3 brief follow-up suggestions based on the conversation history.
    The conversation_history should include the AI's last message.
    """
    suggestions = []
    if not conversation_history:
        print("No conversation history, skipping suggestions.")
        return []

    ai_last_message_content = ""
    # Try to find the last assistant message in the history
    for i in range(len(conversation_history) - 1, -1, -1):
        if conversation_history[i]["role"] == "assistant":
            ai_last_message_content = conversation_history[i]["content"]
            break
    
    if not ai_last_message_content:
        print("No assistant message found in history, skipping suggestions.")
        return []

    suggestion_prompt_system = (
        "You are a helpful assistant that generates 3 brief follow-up suggestions "
        "based on the conversation context. Keep suggestions short (2-5 words) and relevant. "
        "The Suggestions should be from the user's perspective as a reply to the AI's message. "
        "Particularly, if the AI asks a Yes/No question, make sure a direct response is included. "
        "If a plausible answer is 'ok', or 'go ahead', or 'proceed' and so on, include that for sure."
    )
    
    user_context_for_suggestions = f"The AI just said: \"{ai_last_message_content}\". Based on this, what could the user say next? Provide 3 distinct suggestions."

    suggestion_prompt_messages = [
        {"role": "system", "content": suggestion_prompt_system},
        {"role": "user", "content": user_context_for_suggestions}
    ]

    try:
        print(f"Generating suggestions based on AI's last message: {ai_last_message_content[:100]}...")
        suggestion_response = await openai_client.chat.completions.create(
            model=os.environ.get("DEFAULT_MODEL", "gpt-4.1-nano"), 
            messages=suggestion_prompt_messages,
            tools=[{
                "type": "function",
                "function": {
                    "name": "provide_suggestions",
                    "description": "Provides a list of follow-up suggestions.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "Suggestions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of 3 short (2-5 words) follow-up suggestions. Each suggestion should be a complete phrase a user might say."
                            }
                        },
                        "required": ["Suggestions"]
                    }
                }
            }],
            tool_choice={"type": "function", "function": {"name": "provide_suggestions"}},
            temperature=0.7,
        )

        if (hasattr(suggestion_response, 'choices') and 
            suggestion_response.choices and 
            hasattr(suggestion_response.choices[0], 'message') and
            hasattr(suggestion_response.choices[0].message, 'tool_calls') and
            suggestion_response.choices[0].message.tool_calls):
            
            tool_call = suggestion_response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "provide_suggestions":
                arguments = json.loads(tool_call.function.arguments)
                suggestions = arguments.get('Suggestions', [])
                suggestions = [str(s) for s in suggestions[:3]] 
                print(f"Generated suggestions: {suggestions}")
        else:
            print("No valid tool_calls for suggestions found in OpenAI response.")
            if suggestion_response.choices and suggestion_response.choices[0].message and suggestion_response.choices[0].message.content:
                # Fallback attempt if model just returns content (less ideal)
                content = suggestion_response.choices[0].message.content
                print(f"Suggestion fallback content: {content}")
                # Basic parsing, assuming simple list or newline separated - could be improved
                try:
                    parsed_suggestions = json.loads(content)
                    if isinstance(parsed_suggestions, list):
                        suggestions = [str(s) for s in parsed_suggestions[:3]]
                    elif isinstance(parsed_suggestions, dict) and "Suggestions" in parsed_suggestions:
                        suggestions = [str(s) for s in parsed_suggestions.get("Suggestions", [])[:3]]
                except json.JSONDecodeError:
                    # If it's just text, try splitting by newlines, but this is often messy
                    raw_suggestions = content.split('\n')
                    suggestions = [s.strip() for s in raw_suggestions if s.strip() and len(s.strip()) > 1 and len(s.strip()) < 30][:3]
                    print(f"Parsed suggestions from raw text: {suggestions}")

    except Exception as e:
        print(f"Error generating suggestions with OpenAI: {str(e)}")
        traceback.print_exc()

    return suggestions

# Example function to execute Python code
async def execute_code(code):
    """Executes Python code and returns the output."""
    try:
        # Redirect stdout and stderr to capture output
        import io
        import sys
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        # Execute the code
        exec(code, globals(), locals())

        # Capture the output
        stdout_output = sys.stdout.getvalue()
        stderr_output = sys.stderr.getvalue()

        # Restore stdout and stderr
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        # Combine stdout and stderr
        output = stdout_output + stderr_output
        return {"result": output}
    except Exception as e:
        return {"error": str(e)}