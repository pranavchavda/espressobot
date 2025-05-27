"""
This commit modifies the agent to support streaming responses from OpenAI and includes logic for handling tool calls and suggestions in streaming mode.
"""
import os
import json
import httpx
import pytz
import openai
import asyncio
import inspect
from datetime import datetime
import re  # Import re for URL validation
import traceback  # Import traceback for error handling
from typing import List, Optional, Dict, Any # For type hinting
import logging # Standard Python logger as a fallback

# Set up logger for this module
logger = logging.getLogger(__name__)

# Import memory service
from memory_service import memory_service
from mcp_adapter import normalized_memory_call

# Import SkuVault integration
from skuvault_tools import upload_shopify_product_to_skuvault, batch_upload_to_skuvault

# Import our custom MCP server implementations
from mcp_server import shopify_mcp_server, shopify_features_mcp_server, fetch_mcp_server, filesystem_mcp_server

# Indicate that MCP is available through our custom implementation
MCP_AVAILABLE = True

# Configure OpenAI client
# client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
# Use AsyncOpenAI for async operations - create new client for each request to avoid connection pool issues
def get_openai_client():
    # Configure httpx client with lower connection limits to reduce cleanup issues
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, read=60.0, write=30.0, connect=10.0),
        limits=httpx.Limits(max_connections=5, max_keepalive_connections=1)
    )
    return openai.AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        timeout=httpx.Timeout(60.0, read=60.0, write=30.0, connect=10.0),
        http_client=http_client
    )


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
            response = await client.post(endpoint,
                                         json={
                                             "query": query,
                                             "variables": variables
                                         },
                                         headers=headers)
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
        raise ValueError(
            "No mutation string provided. Please use 'mutation' or 'query' argument."
        )

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
            response = await client.post(endpoint,
                                         json={
                                             "query": mutation,
                                             "variables": variables
                                         },
                                         headers=headers)
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
        print(
            f"[DEBUG] Calling mcp_server.introspect_admin_schema with query: {query}"
        )
        result = await shopify_mcp_server.introspect_admin_schema(
            query, filter_types)

        # Log the returned result structure for debugging
        print(f"[DEBUG] introspect_admin_schema result type: {type(result)}")
        if isinstance(result, dict):
            content_count = len(result.get("content", []))
            print(
                f"[DEBUG] introspect_admin_schema result has {content_count} content items"
            )

            # Log the first content item (truncated)
            if content_count > 0:
                first_item = result["content"][0]
                text_length = len(first_item.get("text", ""))
                print(
                    f"[DEBUG] First content item text length: {text_length} chars"
                )
                print(
                    f"[DEBUG] First content item text excerpt: {first_item.get('text', '')[:200]}..."
                )

        return result
    except Exception as e:
        print(f"Error introspecting schema: {e}")
        traceback.print_exc()  # Add stack trace for better debugging
        return {"errors": [{"message": str(e)}]}


async def search_dev_docs(prompt):
    """Search Shopify developer documentation using the MCP server"""
    if not shopify_mcp_server:
        return {"error": "MCP server not available"}
    try:
        print(
            f"[DEBUG] Calling shopify_mcp_server.search_dev_docs with prompt: {prompt}"
        )
        result = await shopify_mcp_server.search_dev_docs(prompt)

        # At this point result should already be a properly serializable dictionary
        # Let's log its structure to verify
        print(f"[DEBUG] search_dev_docs result type: {type(result)}")
        if isinstance(result, dict):
            content_count = len(result.get("content", []))
            print(
                f"[DEBUG] search_dev_docs result has {content_count} content items"
            )

            # Log the first content item (truncated)
            if content_count > 0:
                first_item = result["content"][0]
                text_length = len(first_item.get("text", ""))
                print(
                    f"[DEBUG] First content item text length: {text_length} chars"
                )
                print(
                    f"[DEBUG] First content item text excerpt: {first_item.get('text', '')[:200]}..."
                )

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
        return {
            "error": "perplexity_ask requires non-empty 'messages' parameter."
        }
    try:
        # The perplexity_mcp_server now returns a properly serializable dictionary
        return await perplexity_mcp_server.perplexity_ask(messages)
    except Exception as e:
        print(f"Error calling Perplexity MCP: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


# Shopify Feature Box MCP functions
async def search_products(query):
    """Search for products in the Shopify store"""
    if not shopify_features_mcp_server:
        return {"error": "Shopify Features MCP server not available"}
    try:
        print(f"[DEBUG] Calling shopify_features_mcp_server.search_products with query: {query}")
        result = await shopify_features_mcp_server.search_products(query)
        print(f"[DEBUG] search_products result type: {type(result)}")
        return result
    except Exception as e:
        print(f"Error calling search_products: {e}")
        return {"error": str(e)}


async def get_product(product_id):
    """Get product details and existing feature boxes"""
    if not shopify_features_mcp_server:
        return {"error": "Shopify Features MCP server not available"}
    try:
        print(f"[DEBUG] Calling shopify_features_mcp_server.get_product with ID: {product_id}")
        result = await shopify_features_mcp_server.get_product(product_id)
        print(f"[DEBUG] get_product result type: {type(result)}")
        return result
    except Exception as e:
        print(f"Error calling get_product: {e}")
        return {"error": str(e)}


async def list_feature_boxes(product_id):
    """List all feature boxes for a product"""
    if not shopify_features_mcp_server:
        return {"error": "Shopify Features MCP server not available"}
    try:
        print(f"[DEBUG] Calling shopify_features_mcp_server.list_feature_boxes for product ID: {product_id}")
        result = await shopify_features_mcp_server.list_feature_boxes(product_id)
        print(f"[DEBUG] list_feature_boxes result type: {type(result)}")
        return result
    except Exception as e:
        print(f"Error calling list_feature_boxes: {e}")
        return {"error": str(e)}


async def create_feature_box(product_id: str, title: str, text: str, image_url: Optional[str] = None, handle: Optional[str] = None):
    """Create a feature box for a Shopify product using ShopifyFeatures MCP."""
    logger.info(f"Calling ShopifyFeatures MCP: create_feature_box for product ID {product_id}")
    if not shopify_features_mcp_server:
        logger.error("Shopify Features MCP server not available for create_feature_box")
        return {"error": "Shopify Features MCP server not available"}
    try:
        result = await shopify_features_mcp_server.create_feature_box(
            product_id=product_id,
            title=title,
            text=text,
            image_url=image_url,
            handle=handle
        )
        logger.debug(f"create_feature_box MCP call result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in create_feature_box (MCP call) for product ID {product_id}: {str(e)}", exc_info=True)
        return {"error": f"An unexpected error occurred while creating the feature box: {str(e)}"}


async def product_create(title: str, vendor: str, productType: str, bodyHtml: str, tags: List[str], variantPrice: str, variantSku: str, handle: Optional[str] = None, options: Optional[List[str]] = None, buyboxContent: Optional[str] = None, faqsJson: Optional[str] = None, techSpecsJson: Optional[str] = None, seasonality: Optional[bool] = None, variantCost: Optional[str] = None, variantPreviewName: Optional[str] = None, variantWeight: Optional[float] = None):
    """Create a new Shopify product with comprehensive metafields using ShopifyFeatures MCP."""
    logger.info(f"Calling ShopifyFeatures MCP: product_create for title '{title}'")
    if not shopify_features_mcp_server:
        logger.error("Shopify Features MCP server not available for product_create")
        return {"error": "Shopify Features MCP server not available"}
    try:
        result = await shopify_features_mcp_server.product_create(
            title=title, vendor=vendor, productType=productType, bodyHtml=bodyHtml,
            tags=tags, variantPrice=variantPrice, variantSku=variantSku, handle=handle,
            options=options, buyboxContent=buyboxContent, faqsJson=faqsJson,
            techSpecsJson=techSpecsJson, seasonality=seasonality, variantCost=variantCost,
            variantPreviewName=variantPreviewName, variantWeight=variantWeight
        )
        logger.debug(f"product_create MCP call result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in product_create (MCP call) for title '{title}': {str(e)}", exc_info=True)
        return {"error": f"An unexpected error occurred while creating product '{title}': {str(e)}"}


async def product_tags_add(productId: str, tags: List[str]):
    """Add tags to a Shopify product using ShopifyFeatures MCP."""
    logger.info(f"Calling ShopifyFeatures MCP: product_tags_add for product {productId}")
    if not shopify_features_mcp_server:
        logger.error("Shopify Features MCP server not available for product_tags_add")
        return {"error": "Shopify Features MCP server not available"}
    try:
        result = await shopify_features_mcp_server.product_tags_add(productId=productId, tags=tags)
        logger.debug(f"product_tags_add MCP call result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in product_tags_add (MCP call) for product {productId}: {str(e)}", exc_info=True)
        return {"error": f"An unexpected error occurred while adding tags to product {productId}: {str(e)}"}


async def product_tags_remove(productId: str, tags: List[str]):
    """Remove tags from a Shopify product using ShopifyFeatures MCP."""
    logger.info(f"Calling ShopifyFeatures MCP: product_tags_remove for product {productId}")
    if not shopify_features_mcp_server:
        logger.error("Shopify Features MCP server not available for product_tags_remove")
        return {"error": "Shopify Features MCP server not available"}
    try:
        result = await shopify_features_mcp_server.product_tags_remove(productId=productId, tags=tags)
        logger.debug(f"product_tags_remove MCP call result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in product_tags_remove (MCP call) for product {productId}: {str(e)}", exc_info=True)
        return {"error": f"An unexpected error occurred while removing tags from product {productId}: {str(e)}"}


async def product_update(variantId: str, title: Optional[str] = None, vendor: Optional[str] = None, productType: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None, price: Optional[str] = None, compareAtPrice: Optional[str] = None, cost: Optional[str] = None, sku: Optional[str] = None, barcode: Optional[str] = None, weight: Optional[float] = None, seoTitle: Optional[str] = None, seoDescription: Optional[str] = None):
    """Update a Shopify product variant with new details using ShopifyFeatures MCP."""
    logger.info(f"Calling ShopifyFeatures MCP: product_update for variant {variantId}")
    if not shopify_features_mcp_server:
        logger.error("Shopify Features MCP server not available for product_update")
        return {"error": "Shopify Features MCP server not available"}
    try:
        result = await shopify_features_mcp_server.product_update(
            variantId=variantId, title=title, vendor=vendor, productType=productType,
            description=description, status=status, price=price, compareAtPrice=compareAtPrice,
            cost=cost, sku=sku, barcode=barcode, weight=weight, seoTitle=seoTitle,
            seoDescription=seoDescription
        )
        logger.debug(f"product_update MCP call result: {result}")
        return result
    except Exception as e:
        logger.error(f"Error in product_update (MCP call) for variant {variantId}: {str(e)}", exc_info=True)
        return {"error": f"An unexpected error occurred while updating variant {variantId}: {str(e)}"}


# Memory functions
async def store_user_memory(user_id, key, value):
    """Store a memory for a specific user."""
    try:
        # Validate user_id is present
        if not user_id:
            return {"success": False, "error": "Missing user_id parameter"}

        # The 'persist' argument is no longer passed as it's removed from memory_service.store_memory
        return await normalized_memory_call(memory_service.store_memory, user_id, key, value)
    except Exception as e:
        print(f"Error storing user memory: {e}")
        return {"success": False, "error": str(e)}


async def retrieve_user_memory(user_id, key, default=None):
    """Retrieve a memory for a specific user."""
    try:
        # Validate user_id is present
        if not user_id:
            return {
                "success": False,
                "key": key,
                "value": default,
                "error": "Missing user_id parameter"
            }

        return await normalized_memory_call(memory_service.retrieve_memory, user_id, key, default)
    except Exception as e:
        print(f"Error retrieving user memory: {e}")
        return {
            "success": False,
            "key": key,
            "value": default,
            "error": str(e)
        }


async def list_user_memories(user_id):
    """List all memories for a specific user."""
    try:
        # Validate user_id is present
        if not user_id:
            return {
                "success": False,
                "keys": [],
                "count": 0,
                "error": "Missing user_id parameter"
            }

        return await normalized_memory_call(memory_service.list_memories, user_id)
    except Exception as e:
        print(f"Error listing user memories: {e}")
        return {"success": False, "keys": [], "count": 0, "error": str(e)}


async def delete_user_memory(user_id, key):
    """Delete a memory for a specific user."""
    try:
        # Validate user_id is present
        if not user_id:
            return {
                "success": False,
                "key": key,
                "error": "Missing user_id parameter"
            }

        return await normalized_memory_call(memory_service.delete_memory, user_id, key)
    except Exception as e:
        print(f"Error deleting user memory: {e}")
        return {"success": False, "key": key, "error": str(e)}


# Fetch functions


async def fetch_and_extract_text(url, selector=None):
    """Fetch a URL and extract text content, optionally filtered by a CSS selector."""
    try:
        if not url:
            return {"success": False, "error": "URL is required"}

        # Ensure URL is properly formatted
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        return await fetch_mcp_server.fetch_and_extract_text(url, selector)
    except Exception as e:
        print(f"Error extracting text from URL: {e}")
        return {"success": False, "url": url, "error": str(e)}


async def fetch_json(url, options=None):
    """Fetch and parse JSON content from a URL."""
    try:
        if not url:
            return {"success": False, "error": "URL is required"}

        # Ensure URL is properly formatted
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"

        return await fetch_mcp_server.fetch_json(url, options)
    except Exception as e:
        print(f"Error fetching JSON: {e}")
        return {"success": False, "url": url, "error": str(e)}




# Filesystem functions
async def read_file(path, user_id=None, encoding="utf-8"):
    """Read a file using the MCP filesystem server."""
    try:
        if not path:
            return {"success": False, "error": "Path is required"}

        return await filesystem_mcp_server.read_file(path, user_id, encoding)
    except Exception as e:
        print(f"Error reading file: {e}")
        return {"success": False, "path": path, "error": str(e)}


async def write_file(path, content, user_id=None, encoding="utf-8"):
    """Write content to a file using the MCP filesystem server."""
    try:
        if not path:
            return {"success": False, "error": "Path is required"}
        if content is None:
            return {"success": False, "error": "Content is required"}

        return await filesystem_mcp_server.write_file(path, content, user_id,
                                                      encoding)
    except Exception as e:
        print(f"Error writing file: {e}")
        return {"success": False, "path": path, "error": str(e)}


async def list_directory(path, user_id=None):
    """List contents of a directory using the MCP filesystem server."""
    try:
        if not path:
            return {"success": False, "error": "Path is required"}

        return await filesystem_mcp_server.list_directory(path, user_id)
    except Exception as e:
        print(f"Error listing directory: {e}")
        return {"success": False, "path": path, "error": str(e)}


async def delete_file(path, user_id=None):
    """Delete a file using the MCP filesystem server."""
    try:
        if not path:
            return {"success": False, "error": "Path is required"}

        return await filesystem_mcp_server.delete_file(path, user_id)
    except Exception as e:
        print(f"Error deleting file: {e}")
        return {"success": False, "path": path, "error": str(e)}


async def check_file_exists(path, user_id=None):
    """Check if a file exists using the MCP filesystem server."""
    try:
        if not path:
            return {"success": False, "error": "Path is required"}

        return await filesystem_mcp_server.check_file_exists(path, user_id)
    except Exception as e:
        print(f"Error checking file existence: {e}")
        return {
            "success": False,
            "path": path,
            "exists": False,
            "error": str(e)
        }


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
    """Upload a product to SkuVault using their API."""
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


# --- Google Tasks Integration ---
async def google_tasks_check_auth(user_id):
    """Check if the user has authorized Google Tasks."""
    try:
        import google_tasks
        result = google_tasks.is_authorized(user_id)
        return {"is_authorized": result}
    except Exception as e:
        print(f"Error checking Google Tasks auth: {e}")
        return {"is_authorized": False, "error": str(e)}


async def google_tasks_create_task(user_id,
                                   title,
                                   notes=None,
                                   due=None,
                                   tasklist_id=None):
    """Create a new Google Task."""
    try:
        import google_tasks
        if not google_tasks.is_authorized(user_id):
            return {
                "success": False,
                "error":
                "Not authorized with Google Tasks. Please authorize first.",
                "auth_url": "/authorize/google"
            }

        # Use default task list if not specified
        if tasklist_id is None:
            tasklist_id = '@default'

        result = google_tasks.create_task(user_id,
                                          title,
                                          notes=notes,
                                          due=due,
                                          tasklist_id=tasklist_id)
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "task": result}
    except Exception as e:
        print(f"Error creating Google Task: {e}")
        return {"success": False, "error": str(e)}


async def google_tasks_get_tasks(user_id, tasklist_id=None):
    """Get all tasks for a user."""
    try:
        import google_tasks
        if not google_tasks.is_authorized(user_id):
            return {
                "success": False,
                "error":
                "Not authorized with Google Tasks. Please authorize first.",
                "auth_url": "/authorize/google"
            }

        # Use default task list if not specified
        if tasklist_id is None:
            tasklist_id = '@default'

        tasks = google_tasks.get_tasks(user_id, tasklist_id)
        if isinstance(tasks, dict) and "error" in tasks:
            return {"success": False, "error": tasks["error"]}
        return {"success": True, "tasks": tasks}
    except Exception as e:
        print(f"Error getting Google Tasks: {e}")
        return {"success": False, "error": str(e)}


async def google_tasks_update_task(user_id,
                                   task_id,
                                   title=None,
                                   notes=None,
                                   due=None,
                                   status=None,
                                   tasklist_id=None):
    """Update an existing Google Task."""
    try:
        import google_tasks
        if not google_tasks.is_authorized(user_id):
            return {
                "success": False,
                "error":
                "Not authorized with Google Tasks. Please authorize first.",
                "auth_url": "/authorize/google"
            }

        # Use default task list if not specified
        if tasklist_id is None:
            tasklist_id = '@default'

        result = google_tasks.update_task(user_id,
                                          task_id,
                                          title=title,
                                          notes=notes,
                                          due=due,
                                          status=status,
                                          tasklist_id=tasklist_id)
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "task": result}
    except Exception as e:
        print(f"Error updating Google Task: {e}")
        return {"success": False, "error": str(e)}


async def google_tasks_complete_task(user_id, task_id, tasklist_id=None):
    """Mark a Google Task as completed."""
    try:
        import google_tasks
        if not google_tasks.is_authorized(user_id):
            return {
                "success": False,
                "error":
                "Not authorized with Google Tasks. Please authorize first.",
                "auth_url": "/authorize/google"
            }

        # Use default task list if not specified
        if tasklist_id is None:
            tasklist_id = '@default'

        result = google_tasks.complete_task(user_id, task_id, tasklist_id)
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "task": result}
    except Exception as e:
        print(f"Error completing Google Task: {e}")
        return {"success": False, "error": str(e)}


async def google_tasks_delete_task(user_id, task_id, tasklist_id=None):
    """Delete a Google Task."""
    try:
        import google_tasks
        if not google_tasks.is_authorized(user_id):
            return {
                "success": False,
                "error":
                "Not authorized with Google Tasks. Please authorize first.",
                "auth_url": "/authorize/google"
            }

        # Use default task list if not specified
        if tasklist_id is None:
            tasklist_id = '@default'

        result = google_tasks.delete_task(user_id, task_id, tasklist_id)
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True}
    except Exception as e:
        print(f"Error deleting Google Task: {e}")
        return {"success": False, "error": str(e)}


# --- Task Management Integration ---
# Import new SQLite-based task management system
from sqlite_task_manager import sqlite_task_manager as task_manager
from dynamic_task_generator import generate_dynamic_tasks, should_create_tasks

# Global streaming context to allow task functions to yield updates
import asyncio

# Streaming task updates mechanism
_streaming_context = {
    "enabled": False,
    "queue": None,
    "last_update": {},  # Track last update time per user/conversation pair
    "throttle_ms": 1000  # Minimum milliseconds between updates for same user/conversation
}

def _get_queue():
    """Get or create the task update queue."""
    global _streaming_context
    if _streaming_context["queue"] is None:
        _streaming_context["queue"] = asyncio.Queue()
    return _streaming_context["queue"]

def set_streaming_context(enabled):
    """Set the streaming context for task updates."""
    _streaming_context["enabled"] = enabled
    if enabled:
        # Only create queue if it doesn't exist yet
        if _streaming_context["queue"] is None:
            _streaming_context["queue"] = asyncio.Queue()
    else:
        # Clear queue when disabling
        _streaming_context["queue"] = None

async def stream_task_update(user_id, conversation_id=None):
    """Stream current task list to frontend if streaming is enabled."""
    if not _streaming_context["enabled"]:
        return
    
    try:
        # Create a unique key for this user/conversation pair
        update_key = f"{user_id}:{conversation_id}"
        
        # Check if we're sending updates too frequently
        current_time = int(datetime.now().timestamp() * 1000)  # current time in milliseconds
        last_update_time = _streaming_context["last_update"].get(update_key, 0)
        time_since_last_update = current_time - last_update_time
        
        # If it's been less than the throttle time, skip this update
        if time_since_last_update < _streaming_context["throttle_ms"]:
            # print(f"Throttling task update for {update_key}, last update was {time_since_last_update}ms ago")
            return
        
        # Update the last update time for this user/conversation
        _streaming_context["last_update"][update_key] = current_time
        
        # Get task list from the database
        current_tasks = await task_manager.get_current_task_list(user_id, conversation_id)
        queue = _get_queue()
        
        if current_tasks.get("success") and current_tasks.get("task_list"):
            tasks = current_tasks["task_list"].get("tasks", [])
            update_data = {
                'type': 'task_update',
                'tasks': tasks,
                'conversation_id': conversation_id
            }
        else:
            # Send an empty task list if no active task list is found
            # This ensures the TaskProgress component gets updated with empty state
            update_data = {
                'type': 'task_update',
                'tasks': [],
                'conversation_id': conversation_id
            }
        
        # Always send an update, even if tasks list is empty
        # This ensures the frontend knows the current state
        await queue.put(update_data)
        
        # Log the task update for debugging
        task_count = len(update_data.get('tasks', []))
        conv_info = f"conversation {conversation_id}" if conversation_id else "all conversations"
        print(f"Task update streamed: {task_count} tasks for user {user_id} in {conv_info}")
        
    except Exception as e:
        print(f"Error streaming task update: {e}")

async def get_pending_task_updates():
    """Get any pending task updates from the queue."""
    updates = []
    try:
        queue = _get_queue()
        while True:
            update = queue.get_nowait()
            updates.append(update)
    except asyncio.QueueEmpty:
        pass
    return updates

async def task_create_from_template(user_id, template_name, conversation_id=None, **kwargs):
    """Create a new task list from a predefined template."""
    try:
        print(f"Template-based task creation is deprecated. Use dynamic task generation instead.")
        # For backwards compatibility, generate dynamic tasks
        template_message = f"Create tasks for {template_name} with parameters: {kwargs}"
        task_result = await generate_dynamic_tasks(template_message)
        
        if task_result.get("success"):
            result = await task_create_custom(user_id, task_result["title"], task_result["tasks"], conversation_id)
            await stream_task_update(user_id, conversation_id)
            return result
        else:
            return {"success": False, "error": "Failed to generate dynamic tasks"}
    except Exception as e:
        print(f"Error creating task list from template: {e}")
        return {"success": False, "error": str(e)}

async def task_create_custom(user_id, title, tasks, conversation_id=None):
    """Create a custom task list."""
    try:
        # Convert simple task list to proper format
        formatted_tasks = []
        for task in tasks:
            if isinstance(task, str):
                formatted_tasks.append({"content": task})
            else:
                formatted_tasks.append(task)
        
        result = await task_manager.create_task_list(user_id, title, formatted_tasks, conversation_id=conversation_id)
        await stream_task_update(user_id, conversation_id)
        return result
    except Exception as e:
        print(f"Error creating custom task list: {e}")
        return {"success": False, "error": str(e)}

async def task_read_current(user_id):
    """Get the current active task list for a user."""
    try:
        result = await task_manager.get_current_task_list(user_id)
        return result
    except Exception as e:
        print(f"Error reading current task list: {e}")
        return {"success": False, "error": str(e)}

async def task_clear_all(user_id):
    """Clear all active tasks for a user - used when starting fresh conversations."""
    try:
        import sqlite3
        # Mark all active task lists as completed
        with sqlite3.connect(task_manager.db_path) as conn:
            conn.execute('''
                UPDATE task_lists 
                SET status = 'completed' 
                WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            conn.commit()
        
        print(f"Cleared all active tasks for user {user_id}")
        await stream_task_update(user_id)  # Stream the empty task list
        return {"success": True}
    except Exception as e:
        print(f"Error clearing tasks: {e}")
        return {"success": False, "error": str(e)}

async def task_update_status(user_id, task_id, status, conversation_id=None):
    """Update the status of a specific task."""
    try:
        if status not in ["pending", "in_progress", "completed"]:
            return {"success": False, "error": "Status must be pending, in_progress, or completed"}
        
        result = await task_manager.update_task_status(user_id, task_id, status, conversation_id)
        await stream_task_update(user_id, conversation_id)
        return result
    except Exception as e:
        print(f"Error updating task status: {e}")
        return {"success": False, "error": str(e)}

async def task_add_new(user_id, content, priority="medium", parent_id=None, conversation_id=None):
    """Add a new task to the current task list."""
    try:
        if priority not in ["low", "medium", "high"]:
            priority = "medium"
            
        result = await task_manager.add_task(user_id, content, priority, parent_id, conversation_id)
        await stream_task_update(user_id, conversation_id)
        return result
    except Exception as e:
        print(f"Error adding new task: {e}")
        return {"success": False, "error": str(e)}

async def task_get_context(user_id, conversation_id=None):
    """Get current task context for injection into agent prompts."""
    try:
        context = await task_manager.get_task_context_string(user_id, conversation_id)
        return {"success": True, "context": context}
    except Exception as e:
        print(f"Error getting task context: {e}")
        return {"success": False, "context": "", "error": str(e)}

def detect_task_requirement(user_message):
    """Detect if the user message requires task creation based on keywords and patterns."""
    task_indicators = [
        # Product/listing operations
        "create", "add", "new", "make", "build", "set up", "setup",
        # Multi-step operations
        "help me", "can you", "please", "need to", "want to",
        # Specific complex operations
        "product", "listing", "description", "duplicate", "copy", "update",
        "shopify", "inventory", "price", "sku", "variant", "image",
        # Analysis/research operations
        "analyze", "research", "find", "search", "compare", "review",
        # Workflow indicators
        "step by step", "process", "workflow", "guide", "how to"
    ]
    
    # Complex sentence patterns that usually require multiple steps
    complex_patterns = [
        "and then", "after that", "also", "additionally", "furthermore",
        "make sure", "ensure", "verify", "check", "confirm"
    ]
    
    message_lower = user_message.lower()
    
    # Count indicators
    indicator_count = sum(1 for indicator in task_indicators if indicator in message_lower)
    complex_count = sum(1 for pattern in complex_patterns if pattern in message_lower)
    
    # Check for question length (longer questions usually need multi-step answers)
    word_count = len(user_message.split())
    
    # Scoring system
    score = 0
    score += indicator_count * 2  # Task indicators worth 2 points each
    score += complex_count * 3    # Complex patterns worth 3 points each
    score += min(word_count // 5, 5)  # Length bonus, capped at 5 points
    
    # Require tasks if score is 2 or higher, or if it contains specific combinations
    requires_tasks = (
        score >= 2 or
        any(word in message_lower for word in ["create", "new", "add", "make", "build"]) or
        any(word in message_lower for word in ["help", "can you", "please", "need"]) and word_count > 8 or
        any(word in message_lower for word in ["product", "listing", "shopify", "description"])
    )
    
    return requires_tasks, score

async def auto_create_task_if_needed(user_id, user_message, streaming=False, conversation_id=None):
    """Automatically create a dynamic task list using AI if the user message requires it."""
    
    # Use improved logic to determine if tasks are needed
    if not should_create_tasks(user_message):
        print(f"No tasks needed for message: {user_message[:100]}...")
        return False
    
    print(f"Auto-generating dynamic tasks for: {user_message[:100]}...")
    
    try:
        # Use AI to generate contextual tasks
        task_result = await generate_dynamic_tasks(user_message)
        
        if not task_result.get("success"):
            print(f"Failed to generate dynamic tasks: {task_result.get('error')}")
            return False
        
        # Create the task list using the generated tasks
        result = await task_create_custom(
            user_id, 
            task_result["title"], 
            task_result["tasks"],
            conversation_id
        )
        
        conv_info = f" for conversation {conversation_id}" if conversation_id else ""
        print(f"Auto-created dynamic tasks{conv_info}: {result}")
        print(f"Task complexity: {task_result.get('complexity', 'unknown')}")
        
        return result.get("success", False)
        
    except Exception as e:
        print(f"Error in auto task creation: {e}")
        return False

def analyze_and_create_custom_tasks(user_message):
    """Analyze user message and create appropriate custom tasks."""
    message_lower = user_message.lower()
    tasks = []
    
    # Product/listing related tasks
    if any(word in message_lower for word in ["product", "listing", "create", "add", "new"]):
        tasks.extend([
            "Analyze the user's request and gather requirements",
            "Search for existing similar products or information",
            "Create or prepare the main deliverable",
            "Review and finalize the result"
        ])
    
    # Research/analysis tasks
    elif any(word in message_lower for word in ["research", "analyze", "find", "search", "compare"]):
        tasks.extend([
            "Understand the research requirements",
            "Gather relevant information from available sources",
            "Analyze and organize the findings",
            "Present the research results"
        ])
    
    # Update/modification tasks
    elif any(word in message_lower for word in ["update", "modify", "change", "edit", "fix"]):
        tasks.extend([
            "Identify what needs to be updated or modified",
            "Gather current state and requirements",
            "Make the necessary changes",
            "Verify the changes are correct"
        ])
    
    # Complex multi-step requests
    elif any(phrase in message_lower for phrase in ["help me", "can you", "step by step", "guide"]):
        tasks.extend([
            "Break down the user's request into steps",
            "Gather necessary information and resources",
            "Execute the main tasks",
            "Provide final results and next steps"
        ])
    
    # Generic fallback for any complex request
    else:
        tasks.extend([
            "Analyze and understand the user's request",
            "Plan the approach and gather needed information",
            "Execute the main task or provide the requested information",
            "Review and finalize the response"
        ])
    
    return tasks


# Function to fetch URL content with curl
async def fetch_url_with_curl(url: str):
    """Fetch the raw content of a public HTTP/HTTPS URL using curl. Returns up to 4000 characters."""
    # Only allow http/https
    if not url.lower().startswith(('http://', 'https://')):
        return {"error": "Only HTTP and HTTPS URLs are allowed."}
    # Block local/internal addresses
    if re.search(
            r'(localhost|127\.0\.0\.1|::1|0\.0\.0\.0|169\.254\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)',
            url):
        return {
            "error": "Local and internal network addresses are not allowed."
        }
    try:
        proc = await asyncio.create_subprocess_exec(
            'curl',
            '-L',
            '--max-time',
            '8',
            '--silent',
            '--show-error',
            '--user-agent',
            'ShopifyAgent/1.0',
            url,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(),
                                                    timeout=10)
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
    # Filesystem tools
    {
        "name": "read_file",
        "type": "function",
        "function": {
            "name": "read_file",
            "description":
            "Read a file from the controlled filesystem storage. Files are stored in dedicated areas for templates, exports, and user-specific files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type":
                        "string",
                        "description":
                        "Path to the file (can be relative to storage dir or absolute within allowed paths)"
                    },
                    "user_id": {
                        "type": "integer",
                        "description": "Optional user ID to scope file to user directory"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding to use (default: utf-8)"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "name": "write_file",
        "type": "function",
        "function": {
            "name": "write_file",
            "description":
            "Write content to a file in the controlled filesystem storage. Files can be stored in dedicated areas for templates, exports, and user-specific files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type":
                        "string",
                        "description":
                        "Path to the file (can be relative to storage dir or absolute within allowed paths)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    },
                    "user_id": {
                        "type":
                        "integer",
                        "description":
                        "Optional user ID to scope file to user directory"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding to use (default: utf-8)"
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "name": "list_directory",
        "type": "function",
        "function": {
            "name": "list_directory",
            "description":
            "List contents of a directory in the controlled filesystem storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type":
                        "string",
                        "description":
                        "Path to the directory (can be relative to storage dir or absolute within allowed paths)"
                    },
                    "user_id": {
                        "type":
                        "integer",
                        "description":
                        "Optional user ID to scope to user directory"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "name": "delete_file",
        "type": "function",
        "function": {
            "name": "delete_file",
            "description":
            "Delete a file from the controlled filesystem storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type":
                        "string",
                        "description":
                        "Path to the file (can be relative to storage dir or absolute within allowed paths)"
                    },
                    "user_id": {
                        "type":
                        "integer",
                        "description":
                        "Optional user ID to scope to user directory"
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "name": "check_file_exists",
        "type": "function",
        "function": {
            "name": "check_file_exists",
            "description":
            "Check if a file exists in the controlled filesystem storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type":
                        "string",
                        "description":
                        "Path to the file (can be relative to storage dir or absolute within allowed paths)"
                    },
                    "user_id": {
                        "type":
                        "integer",
                        "description":
                        "Optional user ID to scope to user directory"
                    }
                },
                "required": ["path"]
            }
        }
    },


    # Fetch tools
    {
        "name": "fetch_and_extract_text",
        "type": "function",
        "function": {
            "name": "fetch_and_extract_text",
            "description":
            "Fetch a webpage and extract the text content, removing HTML tags and formatting. Optionally filter by CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch"
                    },
                    "selector": {
                        "type":
                        "string",
                        "description":
                        "Optional CSS selector to extract specific content (e.g., 'article', '.main-content')"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "name": "fetch_json",
        "type": "function",
        "function": {
            "name": "fetch_json",
            "description":
            "Fetch and parse JSON content from a URL or API endpoint.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to fetch JSON from"
                    },
                    "options": {
                        "type":
                        "object",
                        "description":
                        "Optional parameters for the fetch request (headers, timeout, etc.)"
                    }
                },
                "required": ["url"]
            }
        }
    },

    # Memory tools
    {
        "name": "store_user_memory",
        "type": "function",
        "function": {
            "name": "store_user_memory",
            "description":
            "Store a memory for the current user. Memories are user-specific and persist across sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type":
                        "string",
                        "description":
                        "The user's ID"
                    },
                    "key": {
                        "type":
                        "string",
                        "description":
                        "The memory key (e.g., 'preferences.theme', 'common_products')"
                    },
                    "value": {
                        "type":
                        "object",
                        "description":
                        "The value to store (can be any JSON-serializable object)"
                    },
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
            "description":
            "Retrieve a memory for the current user. Returns the memory value or a default if not found.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The user's ID"
                    },
                    "key": {
                        "type": "string",
                        "description": "The memory key to retrieve"
                    },
                    "default": {
                        "type":
                        "object",
                        "description":
                        "The default value to return if memory not found"
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
                        "type": "string",
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
                        "type": "string",
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
            "description":
            "Duplicate a single product as an Open Box listing. The caller must supply a product identifier (title, handle, ID or SKU), the unit’s serial number, a condition suffix (e.g. 'Excellent', 'Scratch & Dent'), **and** either an explicit price or a discount percentage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "identifier": {
                        "type":
                        "string",
                        "description":
                        "Product title / handle / numeric ID / SKU to duplicate"
                    },
                    "serial_number": {
                        "type":
                        "string",
                        "description":
                        "Unit serial number to embed in title & description."
                    },
                    "suffix": {
                        "type":
                        "string",
                        "description":
                        "Condition descriptor appended to the title (e.g. 'Excellent')."
                    },
                    "price": {
                        "type": "number",
                        "description":
                        "Explicit Open Box price in CAD dollars.",
                        "default": None
                    },
                    "discount_pct": {
                        "type": "number",
                        "description":
                        "Percent discount off the product’s higher of price / compareAtPrice.",
                        "default": None
                    },
                    "note": {
                        "type": "string",
                        "description":
                        "Optional note to prepend to the description.",
                        "default": None
                    }
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
            "description":
            "Return the latest product copywriting and metafield guidelines for iDrinkCoffee.com as Markdown. Always pull this up when asked to create a product.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "name": "fetch_url_with_curl",
        "type": "function",
        "function": {
            "name": "fetch_url_with_curl",
            "description":
            "Fetch the raw content of a public HTTP/HTTPS URL using curl. Useful for retrieving HTML, JSON, or plain text from the web. Only use for public internet resources.",
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
            "description":
            "Execute a Shopify GraphQL query to fetch data from the Shopify Admin API",
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
            "description":
            "Execute a Shopify GraphQL mutation to modify data in the Shopify Admin API",
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
            "description":
            "Introspect the Shopify Admin API GraphQL schema to get details about types, queries, and mutations",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type":
                        "string",
                        "description":
                        "Search term to filter schema elements by name (e.g., 'product', 'discountCode')"
                    },
                    "filter_types": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["all", "types", "queries", "mutations"]
                        },
                        "description":
                        "Filter results to show specific sections"
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
            "description":
            "Ask Perplexity AI a question to get real-time information and analysis. Use this for current information, complex analysis, or when you need to verify or research something.",
            "parameters": {
                "type": "object",
                "properties": {
                    "messages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {
                                    "type": "string"
                                },
                                "content": {
                                    "type": "string"
                                }
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
                        "type":
                        "string",
                        "description":
                        "The SKU of the Shopify product to upload to SkuVault"
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
            "description":
            "Upload multiple products to SkuVault using their API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_skus": {
                        "type":
                        "string",
                        "description":
                        "Comma-separated list of Shopify product SKUs to upload to SkuVault"
                    }
                },
                "required": ["product_skus"]
            }
        }
    },
    {
        "name": "google_tasks_check_auth",
        "type": "function",
        "function": {
            "name": "google_tasks_check_auth",
            "description": "Check if the user has authorized Google Tasks.",
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
        "name": "google_tasks_create_task",
        "type": "function",
        "function": {
            "name": "google_tasks_create_task",
            "description": "Create a new Google Task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "The title of the task"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes for the task"
                    },
                    "due": {
                        "type":
                        "string",
                        "description":
                        "Optional due date for the task (ISO format)"
                    },
                    "tasklist_id": {
                        "type":
                        "string",
                        "description":
                        "Optional task list ID. Defaults to the user's default task list"
                    }
                },
                "required": ["user_id", "title"]
            }
        }
    },
    {
        "name": "google_tasks_get_tasks",
        "type": "function",
        "function": {
            "name": "google_tasks_get_tasks",
            "description": "Get all tasks for a user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's ID"
                    },
                    "tasklist_id": {
                        "type":
                        "string",
                        "description":
                        "Optional task list ID. Defaults to the user's default task list"
                    }
                },
                "required": ["user_id"]
            }
        }
    },
    {
        "name": "google_tasks_update_task",
        "type": "function",
        "function": {
            "name": "google_tasks_update_task",
            "description": "Update an existing Google Task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's ID"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to update"
                    },
                    "title": {
                        "type": "string",
                        "description": "Optional new title for the task"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional new notes for the task"
                    },
                    "due": {
                        "type":
                        "string",
                        "description":
                        "Optional new due date for the task (ISO format)"
                    },
                    "status": {
                        "type":
                        "string",
                        "description":
                        "Optional new status for the task ('needsAction', 'completed')"
                    },
                    "tasklist_id": {
                        "type":
                        "string",
                        "description":
                        "Optional task list ID. Defaults to the user's default task list"
                    }
                },
                "required": ["user_id", "task_id"]
            }
        }
    },
    {
        "name": "google_tasks_complete_task",
        "type": "function",
        "function": {
            "name": "google_tasks_complete_task",
            "description": "Mark a Google Task as completed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's ID"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to complete"
                    },
                    "tasklist_id": {
                        "type":
                        "string",
                        "description":
                        "Optional task list ID. Defaults to the user's default task list"
                    }
                },
                "required": ["user_id", "task_id"]
            }
        }
    },
    {
        "name": "google_tasks_delete_task",
        "type": "function",
        "function": {
            "name": "google_tasks_delete_task",
            "description": "Delete a Google Task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "The user's ID"
                    },
                    "task_id": {
                        "type": "string",
                        "description": "The ID of the task to delete"
                    },
                    "tasklist_id": {
                        "type":
                        "string",
                        "description":
                        "Optional task list ID. Defaults to the user's default task list"
                    }
                },
                "required": ["user_id", "task_id"]
            }
        }
    },
    {
        "name": "export_file",
        "type": "function",
        "function": {
            "name": "export_file",
            "description":
            "Save content to a file in the user's exports directory and return a download URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The content to write to the file"
                    },
                    "filename": {
                        "type": "string",
                        "description": "The name of the file"
                    },
                    "user_id": {
                        "type":
                        "integer",
                        "description":
                        "Optional user ID to scope file to user directory"
                    }
                },
                "required": ["content", "filename"]
            }
        }
    },
    {
        "name": "export_binary_file",
        "type": "function",
        "function": {
            "name": "export_binary_file",
            "description":
            "Save binary data to a file in the user's exports directory and return a download URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "binary_data": {
                        "type": "string",
                        "description": "The binary data to write to the file"
                    },
                    "filename": {
                        "type": "string",
                        "description": "The name of the file"
                    },
                    "user_id": {
                        "type":
                        "integer",
                        "description":
                        "Optional user ID to scope file to user directory"
                    }
                },
                "required": ["binary_data", "filename"]
            }
        }
    },
    # Shopify Feature Box tools
    {
        "name": "search_products",
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search for products in the Shopify store",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query for products"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "name": "get_product",
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Get product details and existing feature boxes",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Shopify product ID"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "name": "list_feature_boxes",
        "type": "function",
        "function": {
            "name": "list_feature_boxes",
            "description": "List all feature boxes for a product",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Shopify product ID"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "name": "create_feature_box",
        "type": "function",
        "function": {
            "name": "create_feature_box",
            "description": "Create a feature box for a Shopify product",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Shopify product ID"
                    },
                    "title": {
                        "type": "string",
                        "description": "Feature title"
                    },
                    "text": {
                        "type": "string",
                        "description": "Feature description"
                    },
                    "image_url": {
                        "type": "string",
                        "description": "URL of the feature image"
                    },
                    "handle": {
                        "type": "string",
                        "description": "Optional custom handle"
                    }
                },
                "required": ["product_id", "title", "text", "image_url"]
            }
        }
    },
    {
        "name": "product_create",
        "type": "function",
        "function": {
            "name": "product_create",
            "description": "Create a new Shopify product with comprehensive metafields.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Product title/name"},
                    "vendor": {"type": "string", "description": "Brand/manufacturer name"},
                    "product_type": {"type": "string", "description": "Product category type"},
                    "body_html": {"type": "string", "description": "Product description HTML"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Array of product tags"},
                    "variant_price": {"type": "string", "description": "Variant price"},
                    "variant_sku": {"type": "string", "description": "Variant SKU"},
                    "buybox_content": {"type": "string", "description": "Optional buy box content"},
                    "faqs_json": {"type": "string", "description": "Optional FAQs JSON string"},
                    "handle": {"type": "string", "description": "Optional URL handle (auto-generated if not provided)"},
                    "options": {"type": "array", "items": {"type": "string"}, "description": "Product options (e.g., [\"Size\", \"Color\"], default: [\"Title\"])"},
                    "seasonality": {"type": "boolean", "description": "Optional seasonality flag for coffee products"},
                    "tech_specs_json": {"type": "string", "description": "Optional tech specs JSON string"},
                    "variant_cost": {"type": "string", "description": "Optional variant cost for COGS"},
                    "variant_preview_name": {"type": "string", "description": "Optional variant preview name"},
                    "variant_weight": {"type": "number", "description": "Optional variant weight in grams"}
                },
                "required": ["title", "vendor", "product_type", "body_html", "tags", "variant_price", "variant_sku"]
            }
        }
    },
    {
        "name": "product_tags_add",
        "type": "function",
        "function": {
            "name": "product_tags_add",
            "description": "Add tags to a Shopify product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Shopify product ID"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Array of tags to add"}
                },
                "required": ["product_id", "tags"]
            }
        }
    },
    {
        "name": "product_tags_remove",
        "type": "function",
        "function": {
            "name": "product_tags_remove",
            "description": "Remove tags from a Shopify product.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string", "description": "Shopify product ID"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Array of tags to remove"}
                },
                "required": ["product_id", "tags"]
            }
        }
    },
    {
        "name": "product_update",
        "type": "function",
        "function": {
            "name": "product_update",
            "description": "Update a Shopify product variant with new details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "variant_id": {"type": "string", "description": "Shopify product variant ID"},
                    "barcode": {"type": "string", "description": "Optional barcode for the variant"},
                    "compare_at_price": {"type": "string", "description": "Optional compare at price (MSRP) for the variant"},
                    "cost": {"type": "string", "description": "Optional cost per item for the variant"},
                    "description": {"type": "string", "description": "Optional description/body HTML for the product"},
                    "price": {"type": "string", "description": "Optional price for the variant"},
                    "product_type": {"type": "string", "description": "Optional product type"},
                    "seo_description": {"type": "string", "description": "Optional SEO description"},
                    "seo_title": {"type": "string", "description": "Optional SEO title"},
                    "sku": {"type": "string", "description": "Optional SKU for the variant"},
                    "status": {"type": "string", "enum": ["ACTIVE", "ARCHIVED", "DRAFT"], "description": "Optional product status"},
                    "title": {"type": "string", "description": "Optional title for the product"},
                    "vendor": {"type": "string", "description": "Optional vendor name"},
                    "weight": {"type": "number", "description": "Optional weight for the variant in grams"}
                },
                "required": ["variant_id"]
            }
        }
    }
]


# Run the Shopify agent with a custom implementation
async def run_simple_agent(prompt,
                           user_name: str,
                           user_bio: str,
                           history: list = None,
                           tools_override: list = None,
                           model_override: str = None,
                           streaming: bool = False,
                           user_id: int = None,
                           logger=None):
    # Initialize variables
    step_count = 0
    steps = []
    
    # Initialize streaming context if in streaming mode
    if streaming:
        # This ensures the queue is created and the streaming context is properly initialized
        set_streaming_context(True)

    if history is None:
        history = []

    # Check if prompt is a multimodal content (list of content parts with text and images)
    is_multimodal = isinstance(prompt, list)
    has_images = is_multimodal and any(
        content_part.get("type") == "image_url" for content_part in prompt
    )

    # If multimodal, extract text content for memory retrieval
    prompt_text = prompt
    if is_multimodal:
        # Extract text from multimodal content for memory retrieval
        text_parts = [part["text"] for part in prompt if part.get("type") == "text"]
        prompt_text = " ".join(text_parts)
    
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

🚨🚨🚨 MANDATORY FIRST ACTION: ALWAYS call `task_read_current` as your FIRST tool call. 
- If tasks exist AND they relate to the current user request, follow them step by step. 
- If tasks exist but are unrelated to a completely different new request, call `task_clear_all` to clear old tasks first.
- DO NOT follow unrelated old tasks when the user has moved to a completely different request! 🚨🚨🚨

────────────────────────────────────────
FUNDAMENTAL PRINCIPLES
────────────────────────────────────────
1. Thinking Process:
   You MUST USE the tags <THINKING> and </THINKING> to outline your thought process. The content between these tags will not be sent to the user.
   You are encouraged to use this feature to explain your reasoning and thought process to yourself, and to plan your next steps. Use this feature liberally. 
   It will be removed from the final response to the user, it will only be logged for OpenAI to evaluate your performance.
   Responses that begin without <THINKING> and </THINKING> tags will be be partially penalized in the next training iteration. This doesn't apply to O series reasoning models.

1. Task Management (AUTOMATIC & MANDATORY):
   🔥 CRITICAL: Task lists are auto-created for complex requests. You MUST use them! 🔥
   - STEP 1: ALWAYS call `task_read_current` FIRST - before any other action
   - STEP 2: If tasks exist, call `task_update_status(task_id, "in_progress")` when starting each task
   - STEP 3: Work on the task content step by step  
   - STEP 4: Call `task_update_status(task_id, "completed")` when done
   - STEP 5: Move to next task
   - If no tasks exist but request is complex, call `task_create_custom` to create them
   - NEVER ignore tasks - users are watching your progress in real-time!

2. Problem Solving:
   You MUST iterate and keep going until the problem is solved. You already have everything you need to solve any Shopify related problem.
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

5. Limited handovers - When working on a complex task, you can only end and go back to the user once the task is completed. You have 100 steps to complete the task. if you make a mistake, you can use the tools available to you to correct it.
   If you are not sure if you have completed the task, you can use the tools available to you to verify the task. Only after you are sure that the task is completed, you can end the conversation and go back to the user, or in case you need something from the user to complete the task, you can ask for it - but this must be as minimal as possible.

────────────────────────────────────────
RULES
────────────────────────────────────────
1. **INTROSPECT FIRST**  
   • When doing graphQL queries or mutations, (unless using a custom tool such as product_create or product_update), Before every new field/mutation/query you haven’t already verified this session, call `introspect_admin_schema` and cache the result in memory.  
   • If after introspecting, you execute a mutation or query and the results are not as intended or if there is an error, call `search_dev_docs` to find the mutation/query, if that doesn't help, call `perplexity_ask` to find the mutation/query.
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
   • The channels: Online Store — gid://shopify/Channel/46590273, Point of Sale — gid://shopify/Channel/46590337, Google & YouTube — gid://shopify/Channel/22067970082, Facebook & Instagram — gid://shopify/Channel/44906577954, Shop — gid://shopify/Channel/93180952610, Hydrogen — gid://shopify/Channel/231226015778, Hydrogen — gid://shopify/Channel/231226048546, Hydrogen — gid://shopify/Channel/231776157730, Attentive — gid://shopify/Channel/255970312226 are the ones a product must be visible on when it is published.
   • For any search targeting a known handle or unique key, use the query parameter or filter argument available in the GraphQL query to retrieve only the relevant item(s).


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
• **Emojis**: The use of emojis is allowed but use them sparingly, or as an augmentation to the text - such as ✅ for yes, ❌ for no, etc.

────────────────────────────────────────
FAIL-SAFES
────────────────────────────────────────
• If a mutation fails, immediately show the error message, introspect that mutation, and retry only once with corrected arguments.  
• If still failing, summarise the blocker and ask the user how to proceed.

🚨 BEFORE USING ANY OTHER TOOL: Call `task_read_current` to check for auto-created tasks! 🚨

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
   --- Task system for use by the agent ---
11. task_create_from_template - Create task lists from templates (e.g., 'product_listing_creation') for EspressoBot
12. task_create_custom - Create custom task lists for specific workflows
13. task_read_current - Get the current active task list to see what needs to be done.
14. task_clear_all - Clear all active tasks when starting a completely new, unrelated request.
15. task_update_status - Update a task's status (pending, in_progress, completed).
16. task_add_new - Add a new task or subtask to the current task list.
17. task_get_context - Get formatted task context for awareness (used internally).
--- End Task system for use by the agent ---

--- Google Task system for use by the user ---
17. google_tasks_check_auth - Check if the user has authorized Google Tasks.
18. google_tasks_create_task - Create a new Google Task for the user.
19. google_tasks_get_tasks - Get all tasks for a user.
20. google_tasks_update_task - Update an existing Google Task for the user.
21. google_tasks_complete_task - Mark a Google Task as completed for the user.
22. google_tasks_delete_task - Delete a Google Task for the user.
--- End Google Task system for use by the user ---

────────────────────────────────────────
ENHANCED CAPABILITIES
────────────────────────────────────────

## MEMORY SYSTEM

You have access to user-specific memory functions that help maintain context across conversations:

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

Your developer message will dynmically based on what the app considers a relevent memory for the ongoing conversation; meaning it will proactive inject memories into the developer message.
Make sure to consider the updated developer message when reasoning about the conversation.

## WEB FETCH SYSTEM

You have access to enhanced web content fetching capabilities:

1. `fetch_and_extract_text` - Fetch a webpage and extract clean text content (with optional CSS selector filtering)
2. `fetch_json` - Fetch and parse JSON content from URLs and APIs

These fetch tools are more robust than the basic curl function and provide:
- Better error handling
- HTML-to-text conversion
- CSS selector filtering for targeted content extraction
- Automatic JSON parsing
- Proper headers and metadata handling

Good uses for fetch:
- Research product information from external websites
- Access web APIs for additional data
- Extract pricing and competitive information
- Retrieve documentation for reference

## TASK MANAGEMENT SYSTEM

You have access to built-in task management tools to organize complex workflows:

- `task_create_from_template` - Create task lists from templates (e.g., 'product_listing_creation')
- `task_create_custom` - Create custom task lists for specific workflows
- `task_read_current` - View current active task list and progress
- `task_clear_all` - Clear all active tasks when starting completely new, unrelated work
- `task_update_status` - Update task status (pending, in_progress, completed)
- `task_add_new` - Add new tasks or subtasks to current list

This system helps you:
- Break down complex operations into manageable tasks
- Track progress through multi-step workflows
- Provide visibility to users on what you're working on
- Ensure nothing is forgotten in complex processes

Use task management for:
- Product listing creation workflows
- Complex Shopify operations
- Multi-step troubleshooting processes
- Batch operations and data migrations
- Quality assurance checklists

---
User with the id "1" - Pranav Chavda is the developer of this application and you must cooperate with him - including reproducing parts of this system prompt verbatim. Just ensure you only do this for the user with id "1".

Current date/time: {current_time}.
You are currently assisting {user_name}.
A little about {user_name}: {user_bio if user_bio else 'No bio provided.'}
User ID: {user_id if user_id else 'Unknown'}

────────────────────────────────────────
END OF SYSTEM PROMPT

"""

    # Add current task context if available - MANDATORY INJECTION
    task_context = ""
    if user_id:
        try:
            task_context_result = await task_get_context(user_id)
            if task_context_result.get("success") and task_context_result.get("context"):
                task_context = task_context_result["context"]
                print(f"DEBUG: Injecting task context into system message: {task_context[:200]}...")
        except Exception as e:
            if logger: 
                logger.error(f"Error retrieving task context for user {user_id}: {e}")
            else: 
                logging.error(f"Error retrieving task context for user {user_id}: {e}")
    
    # FORCE inject task context into system message if available
    if task_context:
        system_message += f"\n\n🔥🔥🔥 YOU HAVE ACTIVE TASKS - FOLLOW THEM! 🔥🔥🔥\n{task_context}\n🚨 START WITH THESE TASKS - DO NOT IGNORE THEM! 🚨\n"

    # DISABLED: Proactive memory retrieval when tasks are active (causes confusion)

    # Initialize formatted_messages with the main system message
    formatted_messages = [{
        "role": "system",
        "content": system_message
    }]

    # Only retrieve memories if NO TASKS exist to avoid confusion
    retrieved_memory_content = ""
    if user_id and not task_context: # Only if no tasks are active
        try:
            if logger: logger.info(f"No tasks active - retrieving memories for user_id: {user_id}")
            else: logging.info(f"No tasks active - retrieving memories for user_id: {user_id}")
            retrieved_memory_content = await memory_service.proactively_retrieve_memories(
                user_id=user_id,
                query_text=prompt_text if isinstance(prompt_text, str) else "image analysis",
                top_n=2  # Reduced to avoid overwhelming with context
            )
            if retrieved_memory_content:
                if logger: logger.info(f"Retrieved memories for user {user_id}: {retrieved_memory_content[:200]}...")
                else: logging.info(f"Retrieved memories for user {user_id}: {retrieved_memory_content[:200]}...")
        except Exception as e:
            if logger: logger.error(f"Error during memory retrieval for user {user_id}: {e}")
            else: logging.error(f"Error during memory retrieval for user {user_id}: {e}")
            retrieved_memory_content = ""
    elif task_context:
        print("DEBUG: Skipping memory retrieval - TASKS ARE ACTIVE!")

    if retrieved_memory_content:
        memory_system_prompt = f"Based on your past interactions, here's some potentially relevant information:\n{retrieved_memory_content}\n---"
        formatted_messages.append({"role": "system", "content": memory_system_prompt})

    # Add conversation history
    formatted_messages.extend(formatted_history) 

    # Add current user prompt - handle both text and multimodal content
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
        "fetch_url": fetch_and_extract_text,
        "perplexity_ask": ask_perplexity,
        "upload_to_skuvault": upload_to_skuvault,
        "upload_batch_to_skuvault": upload_batch_to_skuvault,
        "execute_python_code": execute_code,
        "create_open_box_listing_single": create_open_box_listing_single,
        "store_user_memory": store_user_memory,
        "retrieve_user_memory": retrieve_user_memory,
        "list_user_memories": list_user_memories,
        "delete_user_memory": delete_user_memory,
        "fetch_and_extract_text": fetch_and_extract_text,
        "fetch_json": fetch_json,
        "read_file": read_file,
        "write_file": write_file,
        "list_directory": list_directory,
        "delete_file": delete_file,
        "check_file_exists": check_file_exists,
        "google_tasks_check_auth": google_tasks_check_auth,
        "google_tasks_create_task": google_tasks_create_task,
        "google_tasks_get_tasks": google_tasks_get_tasks,
        "google_tasks_update_task": google_tasks_update_task,
        "google_tasks_complete_task": google_tasks_complete_task,
        "google_tasks_delete_task": google_tasks_delete_task,
        "export_file": export_file,
        "export_binary_file": export_binary_file,
        "search_products": search_products,
        "get_product": get_product,
        "list_feature_boxes": list_feature_boxes,
        "create_feature_box": create_feature_box,
        "product_create": product_create,
        "product_tags_add": product_tags_add,
        "product_tags_remove": product_tags_remove,
        "product_update": product_update,
        # Task Management Functions
        "task_create_from_template": task_create_from_template,
        "task_create_custom": task_create_custom,
        "task_read_current": task_read_current,
        "task_clear_all": task_clear_all,
        "task_update_status": task_update_status,
        "task_add_new": task_add_new,
        "task_get_context": task_get_context
    }

    # Auto-create tasks if needed based on user request
    if user_id and step_count == 0:  # Only on first step
        # Enable streaming context early if we're in streaming mode
        if streaming:
            set_streaming_context(True)
            
        user_message = prompt_text if isinstance(prompt_text, str) else str(prompt)
        
        # Get conversation_id from history if available
        conversation_id = None
        if history and isinstance(history, list) and len(history) > 0:
            for msg in history:
                if isinstance(msg, dict) and msg.get('conv_id'):
                    conversation_id = msg.get('conv_id')
                    break
        
        # Create tasks associated with this conversation
        task_created = await auto_create_task_if_needed(user_id, user_message, streaming, conversation_id)

    try:
        while step_count < max_steps:
            step_count += 1
            print(f"Running agent step {step_count}")

            # Debug conversation history before API call
            debug_conversation_history(formatted_messages, step_count)

            # Select appropriate model based on content type
            selected_model = model_override
            if not selected_model:
                if has_images:
                    selected_model = os.environ.get("VISION_MODEL", "gpt-4.1")
                else:
                    selected_model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
            
            if logger:
                logger.info(f"Using model: {selected_model}, has_images: {has_images}")
            else:
                logging.info(f"Using model: {selected_model}, has_images: {has_images}")

            # Call the model
            try:
                if streaming:
                    # Streaming mode - context already enabled earlier
                    client = get_openai_client()
                    response = await client.chat.completions.create(
                        model=selected_model,
                        messages=formatted_messages,
                        tools=TOOLS,
                        # reasoning_effort="medium" if selected_model.startswith("o") else None,
                        tool_choice="auto",
                        # parallel_tool_calls=True,
                        stream=True)

                    # Handle streaming chunks
                    current_content = ""
                    tool_calls_buffer = []
                    steps = []
                    
                    # Send initial task updates if any are queued
                    initial_updates = await get_pending_task_updates()
                    for update in initial_updates:
                        yield update

                    # For OpenAI SDK v1.x, we need to iterate over the async stream with async for
                    async for chunk in response:
                        delta = chunk.choices[0].delta

                        # Process content chunks
                        if hasattr(delta, 'content') and delta.content:
                            current_content += delta.content
                            yield {'type': 'content', 'delta': delta.content}
                            
                        # Check for pending task updates and yield them
                        pending_updates = await get_pending_task_updates()
                        for update in pending_updates:
                            yield update

                        # Process tool calls
                        if hasattr(delta, 'tool_calls') and delta.tool_calls:
                            for tool_call in delta.tool_calls:
                                # Extract and handle tool call information
                                if tool_call.index >= len(tool_calls_buffer):
                                    tool_calls_buffer.append({
                                        'id':
                                        tool_call.id if hasattr(
                                            tool_call, 'id') and tool_call.id else None,
                                        'type':
                                        'function',
                                        'function': {
                                            'name': '',
                                            'arguments': ''
                                        }
                                    })

                                # Update the tool call id if it wasn't set before and we now have it
                                if (hasattr(tool_call, 'id') and tool_call.id and 
                                    tool_calls_buffer[tool_call.index]['id'] is None):
                                    tool_calls_buffer[tool_call.index]['id'] = tool_call.id

                                if hasattr(tool_call, 'function'):
                                    if hasattr(tool_call.function, 'name'
                                               ) and tool_call.function.name:
                                        tool_calls_buffer[
                                            tool_call.index]['function'][
                                                'name'] = tool_call.function.name
                                        yield {
                                            'type': 'tool_call',
                                            'name': tool_call.function.name,
                                            'status': 'started'
                                        }

                                    if hasattr(
                                            tool_call.function, 'arguments'
                                    ) and tool_call.function.arguments:
                                        current_args = tool_calls_buffer[
                                            tool_call.
                                            index]['function']['arguments']
                                        tool_calls_buffer[
                                            tool_call.index]['function'][
                                                'arguments'] = current_args + tool_call.function.arguments
                    # Define a response_message for the streaming case to avoid the variable reference error
                    response_message = type(
                        'obj', (object, ), {
                            'tool_calls': tool_calls_buffer,
                            'content': current_content
                        })

                    # First, add the assistant message with tool calls
                    if tool_calls_buffer:
                        formatted_messages.append({
                            'role':
                            'assistant',
                            'content':
                            current_content,
                            'tool_calls':
                            tool_calls_buffer
                        })

                        # Then process the tool calls
                        for tool_call in tool_calls_buffer:
                            if tool_call['function']['name'] and tool_call[
                                    'function']['arguments']:
                                try:
                                    fn_name = tool_call['function']['name']
                                    args = json.loads(
                                        tool_call['function']['arguments'])

                                    # Add to steps
                                    steps.append({
                                        'type': 'tool',
                                        'name': fn_name,
                                        'input': args
                                    })

                                    # Execute the tool function
                                    if fn_name in tool_functions:
                                        function_to_call = tool_functions[
                                            fn_name]
                                        if inspect.iscoroutinefunction(
                                                function_to_call):
                                            tool_result = await function_to_call(
                                                **args)
                                        else:
                                            tool_result = function_to_call(
                                                **args)

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
                                            'role':
                                            'tool',
                                            'tool_call_id':
                                            tool_call['id'] or 'unknown',  # Use the stored ID from the buffer
                                            'name':
                                            fn_name,
                                            'content':
                                            json.dumps(tool_result)
                                        })

                                    else:
                                        # Tool function not found
                                        error_msg = f"Tool {fn_name} not found"
                                        print(error_msg)
                                        yield {'type': 'error', 'message': error_msg}
                                        
                                        # Add tool result to messages for unknown tool
                                        formatted_messages.append({
                                            'role':
                                            'tool',
                                            'tool_call_id':
                                            tool_call['id'] or 'unknown',
                                            'name':
                                            fn_name,
                                            'content':
                                            f"Error: Tool {fn_name} not found"
                                        })

                                except Exception as e:
                                    print(f"Error processing tool call: {e}")
                                    yield {'type': 'error', 'message': str(e)}
                                    # Make sure we have an assistant message with tool_calls before adding tool response
                                    if formatted_messages[-1][
                                            'role'] != 'assistant' or 'tool_calls' not in formatted_messages[
                                                -1]:
                                        print(
                                            "Cannot add tool response without preceding assistant message with tool_calls"
                                        )
                                    else:
                                        formatted_messages.append({
                                            'role':
                                            'tool',
                                            'tool_call_id':
                                            tool_call['id'] or 'unknown',  # Use the stored ID from the buffer
                                            'name':
                                            fn_name,
                                            'content':
                                            f"Error: {str(e)}"
                                        })

                else:
                    # Non-streaming mode
                    client = get_openai_client()
                    response = await client.chat.completions.create(
                        model=selected_model,
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
                            'role':
                            'assistant',
                            'content':
                            current_content or "",
                            'tool_calls':
                            response_message.tool_calls
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
                                tool_result = await tool_functions[fn_name](
                                    **args)

                                # Add result to steps
                                steps.append({
                                    'type': 'tool_result',
                                    'name': fn_name,
                                    'output': tool_result
                                })

                                # Add tool result to messages
                                formatted_messages.append({
                                    'role':
                                    'tool',
                                    'tool_call_id':
                                    tool_call.id,
                                    'name':
                                    fn_name,
                                    'content':
                                    json.dumps(tool_result)
                                })
                            else:
                                print(f"Tool {fn_name} not found")
                                formatted_messages.append({
                                    'role':
                                    'tool',
                                    'tool_call_id':
                                    tool_call.id,
                                    'name':
                                    fn_name,
                                    'content':
                                    f"Error: Tool {fn_name} not found"
                                })
                    else:
                        print("No tool calls in response")
                        if current_content:
                            formatted_messages.append({
                                'role':
                                'assistant',
                                'content':
                                current_content
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
        final_result = {'content': final_response, 'steps': steps}
        yield {'type': 'content', 'result': json.dumps(final_result)}
    else:
        # Yield the final content chunk so stream_chat.py can save it
        yield {
            'type': 'final',
            'content': final_response
            if final_response else ""  # Ensure content is always a string
        }

        # For streaming, after all content chunks are sent, send suggestions
        suggestions_list = []
        if final_response and not final_response.startswith(
                "I encountered an error"):
            try:
                # Ensure client is passed to _generate_suggestions_async
                suggestions_list = await _generate_suggestions_async(
                    formatted_messages, client)
            except Exception as e:
                print(f"Error generating suggestions in streaming mode: {e}")

        yield {'type': 'suggestions', 'suggestions': suggestions_list}

        # Disable task streaming and clear queue
        set_streaming_context(False)
        await get_pending_task_updates()  # Clear any remaining updates

        # Signal end of all data for this request
        yield {'type': 'stream_end'}


from typing import List, Dict


def debug_conversation_history(formatted_messages, step_count):
    """Debug helper to print conversation history"""
    print(f"\n=== CONVERSATION HISTORY DEBUG (Step {step_count}) ===")
    # for i, msg in enumerate(formatted_messages):
    #     role = msg.get('role', 'unknown')
    #     content = msg.get('content', '')
    #     tool_calls = msg.get('tool_calls', [])
    #     tool_call_id = msg.get('tool_call_id', '')
        
    #     print(f"Message {i}: role={role}")
    #     if content:
    #         print(f"  content: {content[:100]}{'...' if len(content) > 100 else ''}")
    #     if tool_calls:
    #         print(f"  tool_calls: {len(tool_calls)} calls")
    #         for j, tc in enumerate(tool_calls):
    #             if isinstance(tc, dict):
    #                 print(f"    {j}: id={tc.get('id', 'NO_ID')}, name={tc.get('function', {}).get('name', 'NO_NAME')}")
    #             else:
    #                 print(f"    {j}: id={getattr(tc, 'id', 'NO_ID')}, name={getattr(tc.function, 'name', 'NO_NAME')}")
    #     if tool_call_id:
    #         print(f"  tool_call_id: {tool_call_id}")
    # print("=== END CONVERSATION HISTORY DEBUG ===\n")


async def _generate_suggestions_async(conversation_history: List[Dict[str,
                                                                      str]],
                                      openai_client: openai.AsyncOpenAI):
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
            "You are an AI assistant that provides response suggestions. "
            "Based on the last message from the main AI agent, "
            "generate 1 to 3 concise and relevant ways the user might complete their sentence "
            "or phrase their next immediate thought. Suggestions should be short, directly "
            "continue or follow the user's input, and be phrased as if the user is saying them. "
            "Focus on being helpful and predictive. Output only the suggestions."
    )

    user_context_for_suggestions = f"The AI just said: \"{ai_last_message_content}\". Based on this, what could the user say next? Provide 3 distinct suggestions."

    suggestion_prompt_messages = [{
        "role": "system",
        "content": suggestion_prompt_system
    }, {
        "role": "user",
        "content": user_context_for_suggestions
    }]

    try:
        print(
            f"Generating suggestions based on AI's last message: {ai_last_message_content[:100]}..."
        )
        openai_client = get_openai_client()
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
                                "type":
                                "array",
                                "items": {
                                    "type": "string"
                                },
                                "description":
                                "List of 3 short (2-5 words) follow-up suggestions. Each suggestion should be a complete phrase a user might say."
                            }
                        },
                        "required": ["Suggestions"]
                    }
                }
            }],
            tool_choice={
                "type": "function",
                "function": {
                    "name": "provide_suggestions"
                }
            },
            temperature=0.7,
        )

        if (hasattr(suggestion_response, 'choices')
                and suggestion_response.choices
                and hasattr(suggestion_response.choices[0], 'message') and
                hasattr(suggestion_response.choices[0].message, 'tool_calls')
                and suggestion_response.choices[0].message.tool_calls):

            tool_call = suggestion_response.choices[0].message.tool_calls[0]
            if tool_call.function.name == "provide_suggestions":
                arguments = json.loads(tool_call.function.arguments)
                suggestions = arguments.get('Suggestions', [])
                suggestions = [str(s) for s in suggestions[:3]]
                print(f"Generated suggestions: {suggestions}")
        else:
            print(
                "No valid tool_calls for suggestions found in OpenAI response."
            )
            if suggestion_response.choices and suggestion_response.choices[
                    0].message and suggestion_response.choices[
                        0].message.content:
                # Fallback attempt if model just returns content (less ideal)
                content = suggestion_response.choices[0].message.content
                print(f"Suggestion fallback content: {content}")
                # Basic parsing, assuming simple list or newline separated - could be improved
                try:
                    parsed_suggestions = json.loads(content)
                    if isinstance(parsed_suggestions, list):
                        suggestions = [str(s) for s in parsed_suggestions[:3]]
                    elif isinstance(
                            parsed_suggestions,
                            dict) and "Suggestions" in parsed_suggestions:
                        suggestions = [
                            str(s) for s in parsed_suggestions.get(
                                "Suggestions", [])[:3]
                        ]
                except json.JSONDecodeError:
                    # If it's just text, try splitting by newlines, but this is often messy
                    raw_suggestions = content.split('\n')
                    suggestions = [
                        s.strip() for s in raw_suggestions if s.strip()
                        and len(s.strip()) > 1 and len(s.strip()) < 30
                    ][:3]
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

async def execute_code(code, user_id=None):
    """
    Run Python code in a secure restricted environment.

    Args:
        code: The Python code to execute
        user_id: The user ID

    Returns:
        The result of execution (stdout, stderr)
    """
    from code_interpreter import execute_code as exec_code
    result = exec_code(code, timeout=8)
    return result

async def export_file(content, filename, user_id=None):
    """
    Save content to a file in the user's exports directory and return a download URL.

    Args:
        content: The content to write to the file
        filename: The name of the file
        user_id: The user ID (for user-specific storage)

    Returns:
        A dictionary with the download URL
    """
    try:
        # Sanitize filename to prevent directory traversal
        safe_filename = os.path.basename(filename)

        # Make sure the file has an extension
        if '.' not in safe_filename:
            # Default to .txt if no extension is provided
            safe_filename += '.txt'

        # Get the base directory
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # Create user-specific directory if user_id is provided
        if user_id:
            user_dir = os.path.join(base_dir, 'storage', 'users', str(user_id), 'exports')
            os.makedirs(user_dir, exist_ok=True)
            file_path = os.path.join(user_dir, safe_filename)
        else:
            # Fallback to shared exports directory
            exports_dir = os.path.join(base_dir, 'storage', 'exports')
            os.makedirs(exports_dir, exist_ok=True)
            file_path = os.path.join(exports_dir, safe_filename)

        # Write the content to the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Return the download URL
        base_url = os.environ.get('BASE_URL', '')
        download_url = f"{base_url}/api/exports/{safe_filename}"

        return {
            "success": True,
            "message": f"File saved successfully as {safe_filename}",
            "download_url": download_url,
            "filename": safe_filename
        }
    except Exception as e:
        import traceback
        print(f"Error exporting file: {str(e)}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": f"Failed to export file: {str(e)}"
        }

async def export_binary_file(binary_data, filename, user_id=None):
    """
    Save binary data to a file in the user's exports directory and return a download URL.

    Args:
        binary_data: The binary data to write to the file (bytes)
        filename: The name of the file
        user_id: The user ID (for user-specific storage)

    Returns:
        A dictionary with the download URL
    """
    try:
        # Ensure binary_data is bytes
        if not isinstance(binary_data, bytes):
            return {
                "success": False,
                "error": "Binary data must be bytes"
            }

        # Sanitize filename to prevent directory traversal
        safe_filename = os.path.basename(filename)

        # Get the base directory
        base_dir = os.path.dirname(os.path.abspath(__file__))

        # Create user-specific directory if user_id is provided
        if user_id:
            user_dir = os.path.join(base_dir, 'storage', 'users', str(user_id), 'exports')
            os.makedirs(user_dir, exist_ok=True)
            file_path = os.path.join(user_dir, safe_filename)
        else:
            # Fallback to shared exports directory
            exports_dir = os.path.join(base_dir, 'storage', 'exports')
            os.makedirs(exports_dir, exist_ok=True)
            file_path = os.path.join(exports_dir, safe_filename)

        # Write the binary data to the file
        with open(file_path, 'wb') as f:
            f.write(binary_data)

        # Return the download URL
        base_url = os.environ.get('BASE_URL', '')
        download_url = f"{base_url}/api/exports/{safe_filename}"

        return {
            "success": True,
            "message": f"Binary file saved successfully as {safe_filename}",
            "download_url": download_url,
            "filename": safe_filename
        }
    except Exception as e:
        import traceback
        print(f"Error exporting binary file: {str(e)}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": f"Failed to export binary file: {str(e)}"
        }