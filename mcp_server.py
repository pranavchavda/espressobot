"""
Module for handling MCP server connections for Shopify Dev MCP, Perplexity Ask, and other services.

This module provides a hybrid approach:
1. When MCP packages (mcp-client, mcp-server-fetch, etc.) are available, it will use them for full functionality.
2. When the packages are not available, it falls back to simplified implementations that use direct API calls or direct Python operations.

To enable full MCP functionality, ensure the relevant MCP server packages and client libraries are installed.
Example optional packages in requirements.txt:
- mcp-client>=0.1.0
- mcp-server-fetch>=0.1.0
- server-perplexity-ask (via npx)
- @shopify/dev-mcp (via npx)
- @modelcontextprotocol/server-sequential-thinking (via npx)

The simplified implementations don't require external MCP dependencies but may have limited functionality.
"""
import os
from dotenv import load_dotenv
load_dotenv() # Load environment variables at the very beginning
import asyncio
import json
import logging
from typing import List, Optional, Dict, Any # For type hinting
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import timedelta

# MCP Core and related imports
from agents.mcp.server import MCPServerStdio
from mcp.client.session import ClientSession as MCPClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
# # Note: mcp.client.stdio is imported within FetchMCPServer where needed

# Tool-specific or Fallback imports
import httpx 
from bs4 import BeautifulSoup 
import openai
import re

# Local/Project specific imports
from simple_memory import memory_server as memory_mcp_server

# Setup logging
logger = logging.getLogger(__name__)

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# ---------------------------------------------------------------------------
# Monkeypatch: Increase default read_timeout_seconds for all MCP tool calls.
# ---------------------------------------------------------------------------

def _patch_mcp_client_timeout(default_seconds: int = 60) -> None:
    """Monkey-patch ``ClientSession.call_tool`` to use a longer default timeout.
    The upstream ``pydantic-ai`` library does not expose an easy way to change
    the 5-second timeout that bubbles up from ``modelcontextprotocol``'s
    ``BaseSession``.  To avoid forking the library, we patch the method at
    runtime so **every** tool invocation will wait *at least* ``default_seconds``
    seconds before failing with a timeout – unless the caller explicitly
    overrides ``read_timeout_seconds``.
    """

    # Prevent double-patching in case this module is imported multiple times.
    if getattr(MCPClientSession, "_timeout_patched", False):
        return

    original_call_tool = MCPClientSession.call_tool

    async def call_tool_with_timeout(
        self,  # type: ignore[override]
        name: str,
        arguments: Dict[str, Any] | None = None,
        read_timeout_seconds: timedelta | None = None,
    ):
        if read_timeout_seconds is None:
            read_timeout_seconds = timedelta(seconds=default_seconds)
        return await original_call_tool(
            self,
            name=name,
            arguments=arguments,
            read_timeout_seconds=read_timeout_seconds,
        )

    MCPClientSession.call_tool = call_tool_with_timeout  # type: ignore[assignment]
    MCPClientSession._timeout_patched = True  # type: ignore[attr-defined]

# Apply the patch as soon as the module is imported.
_patch_mcp_client_timeout(default_seconds=60)  # Increase timeout to 60 seconds

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ShopifyMCPServer:
    """
    A class to handle communication with a local Shopify Dev MCP server instance.
    This spawns an npx process running @shopify/dev-mcp to provide schema information
    and documentation search capabilities using MCP.
    """
    def __init__(self):
        # Ensure XDG_CONFIG_HOME is set to prevent unbound variable errors
        if "XDG_CONFIG_HOME" not in os.environ:
            os.environ["XDG_CONFIG_HOME"] = os.path.expanduser("~/.config")
        
        # Params for local Shopify Dev MCP server
        self.params = {
            "command": "npx", 
            "args": ["-y", "@shopify/dev-mcp@latest"],
            "env": os.environ.copy()  # Explicitly pass environment variables
        }
        self.cache = True
    
    async def introspect_admin_schema(self, query, filter_types=None):
        """Query the Shopify Admin API schema using the MCP server"""
        if filter_types is None:
            filter_types = ["all"]
        try:
            logger.debug(f"Starting introspect_admin_schema with query: {query}")
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                logger.debug(f"MCPServerStdio context entered for schema introspection")
                raw_result = await server.call_tool(
                    "introspect_admin_schema", {"query": query, "filter": filter_types}
                )
                
                logger.debug(f"Raw introspect_admin_schema result type: {type(raw_result)}")
                
                result = {
                    "meta": getattr(raw_result, "meta", None),
                    "content": [],
                    "isError": getattr(raw_result, "isError", False)
                }
                
                if hasattr(raw_result, "content"):
                    for content_item in raw_result.content:
                        text_content = getattr(content_item, "text", "")
                        logger.debug(f"Schema content item type: {getattr(content_item, 'type', None)}, length: {len(text_content)} chars")
                        result["content"].append({
                            "type": getattr(content_item, "type", None),
                            "text": text_content,
                            "annotations": getattr(content_item, "annotations", None)
                        })
                
                logger.debug(f"Final introspect_admin_schema result content items: {len(result['content'])}")
                return result
        except Exception as e:
            logger.error(f"Error in introspect_admin_schema: {e}", exc_info=True)
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"## Matching GraphQL Types for '{query}':\nError connecting to Shopify MCP server: {str(e)}\n\nPlease check the Shopify Admin API documentation for accurate schema information.",
                    "annotations": None
                }],
                "isError": True # Indicate error state
            }
    
    async def search_dev_docs(self, prompt):
        """Search Shopify developer documentation using the MCP server"""
        try:
            logger.debug(f"Starting search_dev_docs with prompt: {prompt[:50]}...")
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                logger.debug(f"MCPServerStdio context entered for dev docs search")
                raw_result = await server.call_tool(
                    "search_dev_docs", {"prompt": prompt}
                )
                
                logger.debug(f"Raw search_dev_docs result type: {type(raw_result)}")

                result = {
                    "meta": getattr(raw_result, "meta", None),
                    "content": [],
                    "isError": getattr(raw_result, "isError", False)
                }
                
                if hasattr(raw_result, "content"):
                    for content_item in raw_result.content:
                        text_content = getattr(content_item, "text", "")
                        logger.debug(f"Docs content item type: {getattr(content_item, 'type', None)}, length: {len(text_content)} chars")
                        result["content"].append({
                            "type": getattr(content_item, "type", None),
                            "text": text_content,
                            "annotations": getattr(content_item, "annotations", None)
                        })
                
                logger.debug(f"Final search_dev_docs result content items: {len(result['content'])}")
                return result
        except Exception as e:
            logger.error(f"Error in search_dev_docs: {e}", exc_info=True)
            # Fallback response using the mock structure
            return self._get_mock_docs_response(prompt, error_message=str(e))

    def _get_mock_docs_response(self, prompt, error_message=None):
        """Get a mock documentation response, potentially including an error message."""
        error_text = f"\nError connecting to Shopify MCP server: {error_message}\n" if error_message else ""
        mock_content = f"""## Search Results for '{prompt}':{error_text}
The Shopify MCP server for documentation search is currently unavailable or encountered an error. 
Please refer to the [official Shopify documentation](https://shopify.dev/docs) directly.

For quick reference, common topics include:
- Shopify Admin API (GraphQL & REST)
- Theme development (Liquid, Dawn)
- App development (App Bridge, Polaris)
"""
        return {
            "meta": None,
            "content": [{
                "type": "text",
                "text": mock_content,
                "annotations": None
            }],
            "isError": True if error_message else False
        }

    def stop(self):
        """Stop the MCP server process (no-op; context manager handles teardown)"""
        pass

# Create a singleton instance for Shopify MCP
shopify_mcp_server = ShopifyMCPServer() # Renamed from mcp_server to avoid conflict if 'mcp_server' is a generic name

class ShopifyFeaturesMCPServer:
    """
    A class to handle communication with the Shopify Feature Box MCP server.
    This spawns an npx process running @pranavchavda/shopify-feature-box-mcp to provide
    feature box management capabilities for Shopify product pages.
    """
    def __init__(self):
        # Check environment variables
        access_token = os.getenv('SHOPIFY_ACCESS_TOKEN')
        shop_url = os.getenv('SHOPIFY_SHOP_URL')
        print(f"[DEBUG ShopifyFeaturesMCPServer.__init__] Python sees SHOPIFY_ACCESS_TOKEN: '{access_token}'")
        print(f"[DEBUG ShopifyFeaturesMCPServer.__init__] Python sees SHOPIFY_SHOP_URL: '{shop_url}'")

        # Pass environment variables to subprocess
        subprocess_env = os.environ.copy()
        subprocess_env.update({
            'SHOPIFY_ACCESS_TOKEN': access_token or '',
            'SHOPIFY_SHOP_URL': shop_url or '',
            'XDG_CONFIG_HOME': os.path.expanduser('~/.config'),
        })
        print(f"[DEBUG ShopifyFeaturesMCPServer.__init__] Python sees XDG_CONFIG_HOME for subprocess: '{subprocess_env['XDG_CONFIG_HOME']}'")

        self.params = {
            "command": "npx",
            "args": ["@pranavchavda/shopify-feature-box-mcp"],
            "env": subprocess_env
        }
        self.cache = False
        self.default_timeout = 120.0  # Increase to 2 minutes
    
    async def search_products(self, query):
        """Search for products in the Shopify store"""
        try:
            logger.debug(f"Starting search_products with query: {query}")
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache, client_session_timeout_seconds=self.default_timeout) as server:
                logger.debug(f"MCPServerStdio context entered for product search")
                raw_result = await server.call_tool(
                    "search_products", {"query": query}
                )
                
                logger.debug(f"Raw search_products result type: {type(raw_result)}")
                
                result = {
                    "meta": getattr(raw_result, "meta", None),
                    "content": [],
                    "isError": getattr(raw_result, "isError", False)
                }
                
                if hasattr(raw_result, "content"):
                    for content_item in raw_result.content:
                        text_content = getattr(content_item, "text", "")
                        logger.debug(f"Product search content item type: {getattr(content_item, 'type', None)}, length: {len(text_content)} chars")
                        result["content"].append({
                            "type": getattr(content_item, "type", None),
                            "text": text_content,
                            "annotations": getattr(content_item, "annotations", None)
                        })
                
                logger.debug(f"Final search_products result content items: {len(result['content'])}")
                return result
        except Exception as e:
            logger.error(f"Error in search_products: {e}", exc_info=True)
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"Error searching for products: {str(e)}",
                    "annotations": None
                }],
                "isError": True
            }
    
    async def get_product(self, product_id):
        """Get product details and existing feature boxes"""
        try:
            logger.debug(f"Starting get_product with ID: {product_id}")
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache, client_session_timeout_seconds=self.default_timeout) as server:
                logger.debug(f"MCPServerStdio context entered for get_product")
                raw_result = await server.call_tool(
                    "get_product", {"productId": product_id}
                )
                
                logger.debug(f"Raw get_product result type: {type(raw_result)}")
                
                result = {
                    "meta": getattr(raw_result, "meta", None),
                    "content": [],
                    "isError": getattr(raw_result, "isError", False)
                }
                
                if hasattr(raw_result, "content"):
                    for content_item in raw_result.content:
                        text_content = getattr(content_item, "text", "")
                        logger.debug(f"Get product content item type: {getattr(content_item, 'type', None)}, length: {len(text_content)} chars")
                        result["content"].append({
                            "type": getattr(content_item, "type", None),
                            "text": text_content,
                            "annotations": getattr(content_item, "annotations", None)
                        })
                
                logger.debug(f"Final get_product result content items: {len(result['content'])}")
                return result
        except Exception as e:
            logger.error(f"Error in get_product: {e}", exc_info=True)
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"Error getting product details: {str(e)}",
                    "annotations": None
                }],
                "isError": True
            }
    
    async def list_feature_boxes(self, product_id):
        """List all feature boxes for a product"""
        try:
            logger.debug(f"Starting list_feature_boxes for product ID: {product_id}")
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache, client_session_timeout_seconds=self.default_timeout) as server:
                logger.debug(f"MCPServerStdio context entered for list_feature_boxes")
                raw_result = await server.call_tool(
                    "list_feature_boxes", {"productId": product_id}
                )
                
                logger.debug(f"Raw list_feature_boxes result type: {type(raw_result)}")
                
                result = {
                    "meta": getattr(raw_result, "meta", None),
                    "content": [],
                    "isError": getattr(raw_result, "isError", False)
                }
                
                if hasattr(raw_result, "content"):
                    for content_item in raw_result.content:
                        text_content = getattr(content_item, "text", "")
                        logger.debug(f"Feature boxes list content item type: {getattr(content_item, 'type', None)}, length: {len(text_content)} chars")
                        result["content"].append({
                            "type": getattr(content_item, "type", None),
                            "text": text_content,
                            "annotations": getattr(content_item, "annotations", None)
                        })
                
                logger.debug(f"Final list_feature_boxes result content items: {len(result['content'])}")
                return result
        except Exception as e:
            logger.error(f"Error in list_feature_boxes: {e}", exc_info=True)
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"Error listing feature boxes: {str(e)}",
                    "annotations": None
                }],
                "isError": True
            }
    
    async def create_feature_box(self, product_id, title, text, image_url, handle=None):
        """Create a feature box for a Shopify product"""
        try:
            logger.debug(f"Starting create_feature_box for product ID: {product_id}")
            
            args = {
                "productId": product_id,
                "title": title,
                "text": text,
                "imageUrl": image_url
            }
            if handle:
                args["handle"] = handle
            
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache, client_session_timeout_seconds=self.default_timeout) as server:
                logger.debug(f"MCPServerStdio context entered for create_feature_box")
                raw_result = await server.call_tool("create_feature_box", args)
                
                logger.debug(f"Raw create_feature_box result type: {type(raw_result)}")
                
                result = {
                    "meta": getattr(raw_result, "meta", None),
                    "content": [],
                    "isError": getattr(raw_result, "isError", False)
                }
                
                if hasattr(raw_result, "content"):
                    for content_item in raw_result.content:
                        text_content = getattr(content_item, "text", "")
                        logger.debug(f"Create feature box content item type: {getattr(content_item, 'type', None)}, length: {len(text_content)} chars")
                        result["content"].append({
                            "type": getattr(content_item, "type", None),
                            "text": text_content,
                            "annotations": getattr(content_item, "annotations", None)
                        })
                
                logger.debug(f"Final create_feature_box result content items: {len(result['content'])}")
                return result
        except Exception as e:
            logger.error(f"Error in create_feature_box: {e}", exc_info=True)
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"Error creating feature box: {str(e)}",
                    "annotations": None
                }],
                "isError": True
            }

    async def product_create(self, title: str, vendor: str, productType: str, bodyHtml: str, tags: List[str], variantPrice: str, variantSku: str, handle: Optional[str] = None, options: Optional[List[str]] = None, buyboxContent: Optional[str] = None, faqsJson: Optional[str] = None, techSpecsJson: Optional[str] = None, seasonality: Optional[bool] = None, variantCost: Optional[str] = None, variantPreviewName: Optional[str] = None, variantWeight: Optional[float] = None):
        """Create a new Shopify product."""
        try:
            logger.debug(f"Starting product_create for title: {title}")
            
            arguments = {
                "title": title,
                "vendor": vendor,
                "productType": productType,
                "bodyHtml": bodyHtml,
                "tags": tags,
                "variantPrice": variantPrice,
                "variantSku": variantSku,
            }
            if handle is not None:
                arguments["handle"] = handle
            if options is not None:
                arguments["options"] = options
            if buyboxContent is not None:
                arguments["buyboxContent"] = buyboxContent
            if faqsJson is not None:
                arguments["faqsJson"] = faqsJson
            if techSpecsJson is not None:
                arguments["techSpecsJson"] = techSpecsJson
            if seasonality is not None:
                arguments["seasonality"] = seasonality
            if variantCost is not None:
                arguments["variantCost"] = variantCost
            if variantPreviewName is not None:
                arguments["variantPreviewName"] = variantPreviewName
            if variantWeight is not None:
                arguments["variantWeight"] = variantWeight
            
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache, client_session_timeout_seconds=self.default_timeout) as server:
                logger.debug(f"MCPServerStdio context entered for product_create")
                raw_result = await server.call_tool("product_create", arguments)
                
                logger.debug(f"Raw product_create result type: {type(raw_result)}")
                
                # Process result with consistent structure
                if hasattr(raw_result, 'dict') and callable(raw_result.dict):
                    processed_result = raw_result.dict()
                elif hasattr(raw_result, '__dict__'):
                    processed_result = raw_result.__dict__
                else:
                    processed_result = raw_result
                
                logger.debug(f"Final product_create result structure: {type(processed_result)}")
                return processed_result
        except Exception as e:
            logger.error(f"Error in product_create: {e}", exc_info=True)
            return {
                "error": f"Failed to create product: {str(e)}"
            }
    
    async def product_tags_add(self, productId: str, tags: List[str]):
        """Add tags to a Shopify product."""
        logger.info(f"ShopifyFeaturesMCPServer: Calling product_tags_add for productId: {productId}")
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache, client_session_timeout_seconds=self.default_timeout) as server:
                logger.debug(f"ShopifyFeaturesMCPServer: MCPServerStdio context entered for product_tags_add.")
                result = await server.call_tool("product_tags_add", {"productId": productId, "tags": tags})
                logger.debug(f"ShopifyFeaturesMCPServer: product_tags_add MCP call raw result: {result}")
                if hasattr(result, 'dict') and callable(result.dict):
                    return result.dict()
                elif hasattr(result, '__dict__'):
                    return result.__dict__
                return result
        except Exception as e:
            logger.error(f"Error in ShopifyFeaturesMCPServer.product_tags_add: {e}", exc_info=True)
            return {
                "error": f"Failed to add tags to product {productId}: {str(e)}"
            }

    async def product_tags_remove(self, productId: str, tags: List[str]):
        """Remove tags from a Shopify product."""
        logger.info(f"ShopifyFeaturesMCPServer: Calling product_tags_remove for productId: {productId}")
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache, client_session_timeout_seconds=self.default_timeout) as server:
                logger.debug(f"ShopifyFeaturesMCPServer: MCPServerStdio context entered for product_tags_remove.")
                result = await server.call_tool("product_tags_remove", {"productId": productId, "tags": tags})
                logger.debug(f"ShopifyFeaturesMCPServer: product_tags_remove MCP call raw result: {result}")
                if hasattr(result, 'dict') and callable(result.dict):
                    return result.dict()
                elif hasattr(result, '__dict__'):
                    return result.__dict__
                return result
        except Exception as e:
            logger.error(f"Error in ShopifyFeaturesMCPServer.product_tags_remove: {e}", exc_info=True)
            return {
                "error": f"Failed to remove tags from product {productId}: {str(e)}"
            }

    async def product_update(self, variantId: str, title: Optional[str] = None, vendor: Optional[str] = None, productType: Optional[str] = None, description: Optional[str] = None, status: Optional[str] = None, price: Optional[str] = None, compareAtPrice: Optional[str] = None, cost: Optional[str] = None, sku: Optional[str] = None, barcode: Optional[str] = None, weight: Optional[float] = None, seoTitle: Optional[str] = None, seoDescription: Optional[str] = None):
        """Update a Shopify product variant."""
        logger.info(f"ShopifyFeaturesMCPServer: Calling product_update for variantId: {variantId}")
        
        arguments = {"variantId": variantId}
        if title is not None: arguments["title"] = title
        if vendor is not None: arguments["vendor"] = vendor
        if productType is not None: arguments["productType"] = productType
        if description is not None: arguments["description"] = description
        if status is not None: arguments["status"] = status
        if price is not None: arguments["price"] = price
        if compareAtPrice is not None: arguments["compareAtPrice"] = compareAtPrice
        if cost is not None: arguments["cost"] = cost
        if sku is not None: arguments["sku"] = sku
        if barcode is not None: arguments["barcode"] = barcode
        if weight is not None: arguments["weight"] = weight
        if seoTitle is not None: arguments["seoTitle"] = seoTitle
        if seoDescription is not None: arguments["seoDescription"] = seoDescription
        
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache, client_session_timeout_seconds=self.default_timeout) as server:
                logger.debug(f"ShopifyFeaturesMCPServer: MCPServerStdio context entered for product_update.")
                result = await server.call_tool("product_update", arguments)
                logger.debug(f"ShopifyFeaturesMCPServer: product_update MCP call raw result: {result}")
                if hasattr(result, 'dict') and callable(result.dict):
                    return result.dict()
                elif hasattr(result, '__dict__'):
                    return result.__dict__
                return result
        except Exception as e:
            logger.error(f"Error in ShopifyFeaturesMCPServer.product_update: {e}", exc_info=True)
            return {
                "error": f"Failed to update product variant {variantId}: {str(e)}"
            }

# Create a singleton instance for Shopify Features MCP
shopify_features_mcp_server = ShopifyFeaturesMCPServer()

class PerplexityMCPServer:
    """
    A class to handle communication with a local Perplexity MCP server instance.
    This spawns an npx process running server-perplexity-ask using MCP.
    """
    def __init__(self):
        # Ensure XDG_CONFIG_HOME is set
        if "XDG_CONFIG_HOME" not in os.environ:
            os.environ["XDG_CONFIG_HOME"] = os.path.expanduser("~/.config")
        
        # Create a copy of the current environment and add Perplexity API key
        env_vars = os.environ.copy()
        env_vars["PERPLEXITY_API_KEY"] = os.environ.get("PERPLEXITY_API_KEY", "")
        
        self.params = {
            "command": "npx",
            "args": ["-y", "server-perplexity-ask"],
            "env": env_vars
        }
        self.cache = True

    async def perplexity_ask(self, messages):
        """Ask Perplexity a question using the MCP server."""
        logger.debug("Attempting to start Perplexity MCP server...")
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                logger.debug("Perplexity MCP server context entered. Calling tool...")
                try:
                    raw_result = await server.call_tool(
                        "perplexity_ask", {"messages": messages}
                    )
                    logger.debug(f"Perplexity MCP raw_result: {str(raw_result)[:200]}...")
                    
                    result = {
                        "meta": getattr(raw_result, "meta", None),
                        "content": [],
                        "isError": getattr(raw_result, "isError", False)
                    }
                    
                    if hasattr(raw_result, "content"):
                        for content_item in raw_result.content:
                            result["content"].append({
                                "type": getattr(content_item, "type", None),
                                "text": getattr(content_item, "text", None),
                                "annotations": getattr(content_item, "annotations", None)
                            })
                    return result
                except asyncio.TimeoutError as e:
                    logger.error(f"asyncio.TimeoutError during Perplexity call_tool: {e}", exc_info=True)
                    return {
                        "meta": None,
                        "content": [{"type": "text", "text": f"Timeout error connecting to Perplexity MCP server: {str(e)}\n\nPlease try again later.", "annotations": None}],
                        "isError": True
                    }
                except Exception as e:
                    logger.error(f"Exception during Perplexity call_tool: {e}", exc_info=True)
                    return {
                        "meta": None,
                        "content": [{"type": "text", "text": f"Error connecting to Perplexity MCP server: {str(e)}\n\nPlease try again later.", "annotations": None}],
                        "isError": True
                    }
        except Exception as e:
            logger.error(f"Exception during Perplexity MCPServerStdio setup: {e}", exc_info=True)
            return {
                "meta": None,
                "content": [{"type": "text", "text": f"Error setting up Perplexity MCP server: {str(e)}\n\nPlease try again later.", "annotations": None}],
                "isError": True
            }

perplexity_mcp_server = PerplexityMCPServer()

# memory_mcp_server is already an instance imported from simple_memory

# --- FetchMCPServer ---
try:
    # This part requires mcp.client and mcp_server_fetch to be available
    from mcp.client.stdio import StdioServerParameters, stdio_client
    
    class FetchMCPServer:
        """
        A class to handle web content fetching using the mcp-server-fetch Python package (if available),
        with a fallback to direct httpx calls.
        """
        def __init__(self):
            self.params = {
                "command": "python",
                "args": ["-m", "mcp_server_fetch"],
                "env": os.environ.copy()
            }
            self.mcp_available = True # Assume available initially
            logger.info("FetchMCPServer initialized with MCP support.")

        async def _run_mcp_server(self, tool_name, args):
            """Helper method to run a tool on the MCP fetch server"""
            logger.debug(f"FetchMCPServer: Attempting to run MCP tool '{tool_name}' with args: {args}")
            process = None
            try:
                process = subprocess.Popen(
                    [self.params["command"]] + self.params["args"],
                    env=self.params["env"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False # Important for binary communication
                )
                
                mcp_stdio_params = StdioServerParameters(
                    command=None, 
                    args=[],
                    process=process
                )
                
                client = stdio_client(mcp_stdio_params)
                session = MCPClientSession(client) # Use the aliased MCPClientSession
                
                async with session as s:
                    result = await s.call_tool(
                        name=tool_name,
                        arguments=args
                    )
                    
                content = ""
                if hasattr(result, "content") and result.content:
                    for content_item in result.content:
                        if hasattr(content_item, "text"):
                            content += content_item.text
                                
                return {
                    "success": True,
                    "content": content,
                    "meta": result.meta if hasattr(result, "meta") else None
                }
            except FileNotFoundError: # e.g. 'python' or 'mcp_server_fetch' not found
                logger.warning("FetchMCPServer: MCP server command not found. Disabling MCP for fetch.", exc_info=True)
                self.mcp_available = False
                return {"success": False, "error": "MCP server command not found"}
            except Exception as e:
                logger.error(f"[FETCH_MCP] Error running MCP server for tool '{tool_name}': {e}", exc_info=True)
                # Potentially disable MCP if it's a persistent issue, or just return error
                return {"success": False, "error": str(e)}
            finally:
                if process and process.poll() is None: # Ensure process is cleaned up if it was started
                    process.terminate()
                    process.wait(timeout=5) # Wait a bit for termination
                    if process.poll() is None: # If still running, force kill
                        process.kill()
        
        async def fetch_and_extract_text(self, url, selector=None):
            logger.info(f"[FETCH_MCP] Fetching text from URL: {url}, selector: {selector}")
            if self.mcp_available:
                try:
                    args = {"url": url}
                    if selector:
                        args["selector"] = selector
                    result = await self._run_mcp_server("extractText", args)
                    
                    if result["success"]:
                        meta = result.get("meta", {})
                        status = meta.get("status", 200) if meta else 200
                        logger.info(f"[FETCH_MCP] Successfully fetched text via MCP. Status: {status}")
                        return {"success": True, "url": url, "text": result.get("content", ""), "status": status}
                    else:
                        logger.warning(f"[FETCH_MCP] MCP fetch_and_extract_text failed: {result.get('error')}. Falling back.")
                        # Fall through to simplified if MCP fails but was thought to be available
                except Exception as e: # Broad exception if _run_mcp_server itself fails catastrophically
                    logger.error(f"[FETCH_MCP] Critical error in MCP fetch_and_extract_text: {e}. Falling back.", exc_info=True)
            
            # Fallback or if MCP not available
            logger.info(f"[FETCH_MCP] Using simplified fallback for fetch_and_extract_text: {url}")
            return await self._fetch_and_extract_text_simplified(url, selector)

        async def _fetch_and_extract_text_simplified(self, url, selector=None):
            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    response.raise_for_status() # Raise HTTPStatusError for bad responses (4xx or 5xx)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    if selector:
                        elements = soup.select(selector)
                        text = "\n\n".join([elem.get_text(strip=True) for elem in elements])
                    else:
                        for script_or_style in soup(["script", "style"]):
                            script_or_style.extract()
                        text = soup.get_text(separator="\n")
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                    
                    return {"success": True, "url": url, "text": text, "status": response.status_code}
            except Exception as e:
                logger.error(f"[FETCH_MCP_SIMPLIFIED] Error extracting text: {e}", exc_info=True)
                return {"success": False, "url": url, "error": str(e), "text": "", "status": 0}

        async def fetch_json(self, url, options=None):
            logger.info(f"[FETCH_MCP] Fetching JSON from URL: {url}")
            if options is None: options = {}
            
            if self.mcp_available:
                try:
                    args = {"url": url, **options} # Pass options through
                    result = await self._run_mcp_server("fetchJson", args)

                    if result["success"]:
                        meta = result.get("meta", {})
                        status = meta.get("status", 200) if meta else 200
                        headers = meta.get("headers", {}) if meta else {}
                        try:
                            json_data = json.loads(result.get("content", "null"))
                        except json.JSONDecodeError:
                            logger.warning(f"[FETCH_MCP] MCP fetchJson returned non-JSON content: {result.get('content')[:100]}")
                            json_data = None # Or raise error
                        logger.info(f"[FETCH_MCP] Successfully fetched JSON via MCP. Status: {status}")
                        return {"success": True, "url": url, "json": json_data, "status": status, "headers": headers}
                    else:
                        logger.warning(f"[FETCH_MCP] MCP fetch_json failed: {result.get('error')}. Falling back.")
                except Exception as e:
                    logger.error(f"[FETCH_MCP] Critical error in MCP fetch_json: {e}. Falling back.", exc_info=True)

            logger.info(f"[FETCH_MCP] Using simplified fallback for fetch_json: {url}")
            return await self._fetch_json_simplified(url, options)

        async def _fetch_json_simplified(self, url, options=None):
            if options is None: options = {}
            try:
                headers = options.get("headers", {})
                if "Accept" not in headers and "accept" not in headers: headers["Accept"] = "application/json"
                timeout = options.get("timeout", 15.0)
                
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    json_data = response.json()
                    return {"success": True, "url": url, "json": json_data, "status": response.status_code, "headers": dict(response.headers)}
            except Exception as e:
                logger.error(f"[FETCH_MCP_SIMPLIFIED] Error fetching JSON: {e}", exc_info=True)
                return {"success": False, "url": url, "error": str(e), "json": None, "status": 0}

except ImportError:
    logger.warning("mcp.client.stdio or mcp.client.session not found. FetchMCPServer will use simplified, direct HTTP calls only.")
    class FetchMCPServer:
        """
        Simplified FetchMCPServer using direct httpx calls as MCP components are not available.
        """
        def __init__(self):
            self.mcp_available = False
            logger.info("FetchMCPServer initialized in simplified (direct HTTP) mode.")

        async def fetch_and_extract_text(self, url, selector=None):
            logger.info(f"[FETCH_MCP_SIMPLIFIED_ONLY] Fetching text from URL: {url}, selector: {selector}")
            return await self._fetch_and_extract_text_simplified(url, selector)

        async def _fetch_and_extract_text_simplified(self, url, selector=None):
            try:
                async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                    response = await client.get(url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    if selector:
                        elements = soup.select(selector)
                        text = "\n\n".join([elem.get_text(strip=True) for elem in elements])
                    else:
                        for script_or_style in soup(["script", "style"]): script_or_style.extract()
                        text = soup.get_text(separator="\n")
                        lines = (line.strip() for line in text.splitlines())
                        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                        text = '\n'.join(chunk for chunk in chunks if chunk)
                    return {"success": True, "url": url, "text": text, "status": response.status_code}
            except Exception as e:
                logger.error(f"[FETCH_MCP_SIMPLIFIED_ONLY] Error extracting text: {e}", exc_info=True)
                return {"success": False, "url": url, "error": str(e), "text": "", "status": 0}

        async def fetch_json(self, url, options=None):
            logger.info(f"[FETCH_MCP_SIMPLIFIED_ONLY] Fetching JSON from URL: {url}")
            return await self._fetch_json_simplified(url, options)

        async def _fetch_json_simplified(self, url, options=None):
            if options is None: options = {}
            try:
                headers = options.get("headers", {})
                if "Accept" not in headers and "accept" not in headers: headers["Accept"] = "application/json"
                timeout = options.get("timeout", 15.0)
                
                async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    json_data = response.json()
                    return {"success": True, "url": url, "json": json_data, "status": response.status_code, "headers": dict(response.headers)}
            except Exception as e:
                logger.error(f"[FETCH_MCP_SIMPLIFIED_ONLY] Error fetching JSON: {e}", exc_info=True)
                return {"success": False, "url": url, "error": str(e), "json": None, "status": 0}

# Create an instance of FetchMCPServer
fetch_mcp_server = FetchMCPServer()

# --- FilesystemMCPServer ---
class FilesystemMCPServer:
    """
    A class to handle filesystem operations using direct Python file operations.
    This does not use MCP client/server; it's a local utility structured like one.
    """
    def __init__(self):
        self.base_dir = os.path.join(PROJECT_ROOT, "storage")
        self.templates_dir = os.path.join(self.base_dir, "templates")
        self.exports_dir = os.path.join(self.base_dir, "exports")
        self.users_dir = os.path.join(self.base_dir, "users")
        
        for dir_path in [self.base_dir, self.templates_dir, self.exports_dir, self.users_dir]:
            os.makedirs(dir_path, exist_ok=True)
        logger.info(f"FilesystemMCPServer initialized. Base directory: {self.base_dir}")
    
    def _resolve_path(self, path_str, user_id=None):
        """Resolves a user-provided path to a safe, absolute path within allowed storage."""
        # Prevent directory traversal attacks and normalize the path
        # Disallow '..' in paths to prevent escaping the base directory
        if ".." in path_str.split(os.path.sep):
            logger.warning(f"Path traversal attempt detected: {path_str}")
            return None

        base = self.base_dir
        if path_str.startswith("templates/"):
            base = self.templates_dir
            path_str = path_str[len("templates/"):]
        elif path_str.startswith("exports/"):
            base = self.exports_dir
            path_str = path_str[len("exports/"):]
        elif path_str.startswith("users/"):
            # users/[user_id]/file.txt or users/file_not_in_user_id_folder.txt
            if user_id and path_str.startswith(f"users/{user_id}/"):
                 base = os.path.join(self.users_dir, str(user_id))
                 path_str = path_str[len(f"users/{user_id}/"):]
                 os.makedirs(base, exist_ok=True) # Ensure user's specific dir exists
            elif user_id: # Path is just for this user, relative to their dir
                 base = os.path.join(self.users_dir, str(user_id))
                 os.makedirs(base, exist_ok=True)
            else: # Path is users/somefile.txt, not specific to a user via user_id param
                 base = self.users_dir # Resolved to general users folder
                 path_str = path_str[len("users/"):]

        elif user_id: # Path is relative to a specific user's directory
            base = os.path.join(self.users_dir, str(user_id))
            os.makedirs(base, exist_ok=True) # Ensure user's specific dir exists
        
        # Create absolute path and normalize it (e.g., collapses redundant separators)
        abs_path = os.path.normpath(os.path.join(base, path_str))
        
        # Security check: Ensure the resolved path is still within one of the allowed base directories
        allowed_bases = [
            os.path.normpath(self.base_dir),
            os.path.normpath(self.templates_dir),
            os.path.normpath(self.exports_dir),
            os.path.normpath(self.users_dir) # This covers subdirectories like users_dir/user_id too
        ]
        
        # Check if abs_path starts with any of the allowed_bases
        is_safe = any(abs_path.startswith(allowed_base) for allowed_base in allowed_bases)

        if not is_safe:
            # If user_id was provided, it could be that the path was intended for their specific folder
            if user_id:
                user_specific_base = os.path.normpath(os.path.join(self.users_dir, str(user_id)))
                if abs_path.startswith(user_specific_base):
                    is_safe = True
            
            if not is_safe:
                logger.warning(f"Resolved path '{abs_path}' is outside allowed directories.")
                return None
        
        return abs_path

    async def read_file(self, path, user_id=None, encoding="utf-8"):
        logger.info(f"[FS_MCP] Reading file: {path}, user: {user_id}")
        abs_path = self._resolve_path(path, user_id)
        if not abs_path:
            return {"success": False, "path": path, "error": "Invalid or disallowed file path."}
        
        if not os.path.exists(abs_path) or not os.path.isfile(abs_path):
            return {"success": False, "path": path, "error": "File does not exist or is not a file.", "exists": False}
        
        try:
            with open(abs_path, "r", encoding=encoding) as f:
                content = f.read()
            return {"success": True, "path": path, "content": content, "exists": True}
        except Exception as e:
            logger.error(f"[FS_MCP] Error reading file '{abs_path}': {e}", exc_info=True)
            return {"success": False, "path": path, "error": str(e)}

    async def write_file(self, path, content, user_id=None, encoding="utf-8"):
        logger.info(f"[FS_MCP] Writing file: {path}, user: {user_id}, length: {len(content)}")
        abs_path = self._resolve_path(path, user_id)
        if not abs_path:
            return {"success": False, "path": path, "error": "Invalid or disallowed file path."}
        
        try:
            os.makedirs(os.path.dirname(abs_path), exist_ok=True) # Ensure parent directory exists
            with open(abs_path, "w", encoding=encoding) as f:
                f.write(content)
            return {"success": True, "path": path, "message": f"File written successfully to {path}"}
        except Exception as e:
            logger.error(f"[FS_MCP] Error writing file '{abs_path}': {e}", exc_info=True)
            return {"success": False, "path": path, "error": str(e)}

    async def list_directory(self, path=".", user_id=None): # Default path to current context base
        logger.info(f"[FS_MCP] Listing directory: {path}, user: {user_id}")
        abs_path = self._resolve_path(path, user_id)
        if not abs_path:
            return {"success": False, "path": path, "error": "Invalid or disallowed directory path."}

        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return {"success": False, "path": path, "error": "Directory does not exist or is not a directory."}
        
        try:
            items = os.listdir(abs_path)
            files = [item for item in items if os.path.isfile(os.path.join(abs_path, item))]
            directories = [item for item in items if os.path.isdir(os.path.join(abs_path, item))]
            return {"success": True, "path": path, "files": files, "directories": directories}
        except Exception as e:
            logger.error(f"[FS_MCP] Error listing directory '{abs_path}': {e}", exc_info=True)
            return {"success": False, "path": path, "error": str(e)}

    async def delete_file(self, path, user_id=None):
        logger.info(f"[FS_MCP] Deleting file: {path}, user: {user_id}")
        abs_path = self._resolve_path(path, user_id)
        if not abs_path:
            return {"success": False, "path": path, "error": "Invalid or disallowed file path."}

        if not os.path.exists(abs_path) or not os.path.isfile(abs_path): # Check it's a file
            return {"success": False, "path": path, "error": "File does not exist or is not a file."}
        
        try:
            os.remove(abs_path)
            return {"success": True, "path": path, "message": f"File deleted successfully: {path}"}
        except Exception as e:
            logger.error(f"[FS_MCP] Error deleting file '{abs_path}': {e}", exc_info=True)
            return {"success": False, "path": path, "error": str(e)}

    async def check_file_exists(self, path, user_id=None):
        logger.debug(f"[FS_MCP] Checking existence of file: {path}, user: {user_id}")
        abs_path = self._resolve_path(path, user_id)
        if not abs_path: # Invalid path means it effectively doesn't exist in a usable way
            return {"success": True, "path": path, "exists": False, "error": "Invalid or disallowed file path."} 
            # Success true because the check itself succeeded, even if result is 'does not exist due to invalid path'
        
        try:
            exists = os.path.exists(abs_path) and os.path.isfile(abs_path)
            return {"success": True, "path": path, "exists": exists}
        except Exception as e: # Should not happen for os.path.exists unless perms issues on parent dir
            logger.error(f"[FS_MCP] Error checking file existence for '{abs_path}': {e}", exc_info=True)
            return {"success": False, "path": path, "exists": False, "error": str(e)}

filesystem_mcp_server = FilesystemMCPServer()


# All server instances are now created:
# shopify_mcp_server
# perplexity_mcp_server  
# memory_mcp_server (imported instance)
# fetch_mcp_server
# filesystem_mcp_server
