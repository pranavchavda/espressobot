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
import asyncio
import json
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import timedelta

# MCP Core and related imports
from agents.mcp.server import MCPServerStdio
from mcp.client.session import ClientSession as MCPClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
# Note: mcp.client.stdio is imported within FetchMCPServer and SequentialThinkingMCPServer where needed

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

def _patch_mcp_client_timeout(default_seconds: int = 30) -> None:
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
_patch_mcp_client_timeout(default_seconds=30)  # Increase timeout to 30 seconds

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
                if "Accept" not in headers and "accept" not in headers: # Ensure we ask for JSON
                    headers["Accept"] = "application/json"
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
            # Duplicated from above for standalone use if import fails
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
            # Duplicated from above
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

fetch_mcp_server = FetchMCPServer()


# --- SequentialThinkingMCPServer ---
try:
    from mcp.client.stdio import StdioServerParameters, stdio_client # Already imported if FetchMCPServer's try block succeeded

    class SequentialThinkingMCPServer:
        """
        A class to handle structured, step-by-step thinking using the
        @modelcontextprotocol/server-sequential-thinking MCP server.
        """
        def __init__(self):
            # Ensure XDG_CONFIG_HOME is set (important for npx/npm global tools)
            if "XDG_CONFIG_HOME" not in os.environ:
                os.environ["XDG_CONFIG_HOME"] = os.path.expanduser("~/.config")

            # Default initializations
            self.mcp_tool_name = "sequential_thinking" # Default tool name, can be overridden by config
            self.mcp_thinking_available = False # Assume not available until config validates it

            # Default params for npx, can be overridden by mcp_config.json
            self.params = {
                "command": "npx", 
                "args": ["-y", "@modelcontextprotocol/server-sequential-thinking@latest"], # Default to latest if not in config
                "env": os.environ.copy()
            }
            # self.cache = True # MCPServerStdio has this, set if needed after super().__init__ or directly

            config_path = "thinking.json"
            server_key = "sequential-thinking" # Key for this server in mcp_config.json
            # expected_tool_name is self.mcp_tool_name, initialized above

            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    if server_key in config.get("mcpServers", {}):
                        server_config = config["mcpServers"][server_key]
                        # Override default params if specified in config
                        if server_config.get("command"):
                            self.params["command"] = server_config.get("command")
                        if server_config.get("args") is not None: # Allow empty list from config
                            self.params["args"] = server_config.get("args")
                        loaded_env = server_config.get("env")
                        if isinstance(loaded_env, dict) and loaded_env: # Only use if it's a non-empty dict
                            self.params["env"] = loaded_env
                        # If loaded_env is {} or None, self.params["env"] (which defaults to os.environ.copy()) is preserved.
                        
                        # Tool name might also be configurable in mcp_config.json
                        # For now, using the default/expected one. Update self.mcp_tool_name if needed from server_config.
                        # self.mcp_tool_name = server_config.get("toolName", self.mcp_tool_name)

                        if self.params.get("command") and self.mcp_tool_name:
                            self.mcp_thinking_available = True
                            logger.info(f"Primary SequentialThinkingMCPServer initialized to use MCP server '{server_key}' with tool '{self.mcp_tool_name}'. Params: {self.params}")
                        else:
                            logger.warning(f"Primary SequentialThinkingMCPServer: Config for '{server_key}' missing command or resulting mcp_tool_name is empty. Will use default npx if possible, or fallback to direct OpenAI.")
                            # Attempt to use default npx params if they are valid
                            if self.params.get("command") and self.mcp_tool_name and self.params.get("command") == "npx": 
                                self.mcp_thinking_available = True 
                                logger.info(f"Primary SequentialThinkingMCPServer: Using default npx for '{server_key}' as config was incomplete.")
                            else:
                                self.mcp_thinking_available = False # Ensure it's false if config is bad and default npx also invalid

                    else:
                        logger.warning(f"Primary SequentialThinkingMCPServer: Entry for '{server_key}' not found in {config_path}. Will use default npx if possible, or fallback to direct OpenAI.")
                        if self.params.get("command") and self.mcp_tool_name and self.params.get("command") == "npx":
                                self.mcp_thinking_available = True 
                                logger.info(f"Primary SequentialThinkingMCPServer: Using default npx due to missing config key for '{server_key}'.")
                else:
                    logger.warning(f"Primary SequentialThinkingMCPServer: MCP config file {config_path} not found. Will use default npx if possible, or fallback to direct OpenAI.")
                    if self.params.get("command") and self.mcp_tool_name and self.params.get("command") == "npx": 
                                self.mcp_thinking_available = True 
                                logger.info(f"Primary SequentialThinkingMCPServer: Using default npx due to missing config file.")

            except Exception as e:
                logger.error(f"Primary SequentialThinkingMCPServer: Error loading MCP config from {config_path}: {e}. Will use default npx if possible, or fallback to direct OpenAI.", exc_info=True)
                if self.params.get("command") and self.mcp_tool_name and self.params.get("command") == "npx":
                                self.mcp_thinking_available = True
                                logger.info(f"Primary SequentialThinkingMCPServer: Using default npx after error loading config.")
            
            if not self.mcp_thinking_available:
                logger.info("Primary SequentialThinkingMCPServer: MCP not configured or enabled. Fallback to direct OpenAI will be used if think() is called.")
            # If this class inherits from MCPServerStdio, its __init__ would typically be called here, e.g.:
            # super().__init__(params=self.params, cache=True) # Assuming self.cache is defined or default is True
            
        async def _run_mcp_server(self, tool_name, args):
            """Helper method to run a tool on the Sequential Thinking MCP server"""
            logger.debug(f"SequentialThinkingMCPServer: Attempting MCP tool '{tool_name}' with args: {args}")
            process = None
            try:
                process = subprocess.Popen(
                    [self.params["command"]] + self.params["args"],
                    env=self.params["env"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False
                )
                mcp_stdio_params = StdioServerParameters(
                    command=self.params["command"],
                    args=self.params["args"],
                    process=process
                )
                async with stdio_client(mcp_stdio_params) as (current_read_stream, current_write_stream):
                    session = MCPClientSession(
                        read_stream=current_read_stream,
                        write_stream=current_write_stream
                    )
                    
                    async with session as s:
                        result = await s.call_tool(name=tool_name, arguments=args)
                    
                content = []
                if hasattr(result, "content") and result.content:
                    for item in result.content:
                        if hasattr(item, "text"): content.append(item.text)
                
                steps, conclusion = [], ""
                if hasattr(result, "meta") and isinstance(result.meta, dict):
                    steps = result.meta.get("steps", [])
                    conclusion = result.meta.get("conclusion", "")
                elif content: # Fallback parsing if meta is not structured as expected
                    combined_content = "\n".join(content)
                    # (Simplified parsing, could be enhanced)
                    step_matches = re.findall(r"Step (\d+):(.*?)(?=Step \d+:|$)", combined_content + "\n", re.DOTALL)
                    steps = [{"number": int(num), "content": c.strip()} for num, c in step_matches]
                    if "\n\nConclusion:" in combined_content:
                        conclusion = combined_content.split("\n\nConclusion:", 1)[1].strip()

                return {"success": True, "steps": steps, "conclusion": conclusion, "thinking_type": args.get("thinking_type", "general"), "raw_content": content}
            except FileNotFoundError:
                logger.warning("SequentialThinkingMCPServer: MCP server command not found. MCP thinking disabled.", exc_info=True)
                self.mcp_thinking_available = False
                return {"success": False, "error": "MCP server command not found"}
            except Exception as e:
                logger.error(f"[THINKING_MCP] Error running MCP server for tool '{tool_name}': {e}", exc_info=True)
                return {"success": False, "error": str(e)}
            finally:
                if process and process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill()

        async def _think_direct(self, prompt, thinking_type="general", max_steps=5):
            # Direct OpenAI call for thinking process, used if MCP server is unavailable or an MCP call fails.
            # In a real scenario, you might structure this to avoid duplication.
            logger.debug(f"[THINKING_MCP_DIRECT_FALLBACK] Using direct OpenAI for: {prompt[:50]}...")
            try:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.error("[THINKING_MCP_DIRECT_FALLBACK] OPENAI_API_KEY not set.")
                    return {"success": False, "steps": [], "conclusion": "OPENAI_API_KEY not configured.", "thinking_type": thinking_type, "error": "API key missing"}

                client = openai.AsyncOpenAI(api_key=api_key)
                system_messages = {
                    "general": f"You are a thinking assistant. Break down this problem or question into clear, step-by-step reasoning. Provide exactly {max_steps-2}-{max_steps} steps... Each step should start with 'Step X:'. End with 'Conclusion:'.",
                    "problem-solving": f"You are a problem-solving assistant... Provide {max_steps-1}-{max_steps+1} steps... Each step 'Step X:'. End with 'Conclusion:'.",
                    "coding": f"You are a coding assistant... Provide {max_steps-1}-{max_steps+2} steps... Each step 'Step X:'. End with 'Conclusion:'."
                } # Truncated for brevity, use full prompts from above
                system_message = system_messages.get(thinking_type, system_messages["general"])
                
                response = await client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-4.1"),
                    messages=[ {"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
                )
                thinking_text = response.choices[0].message.content
                
                steps_text, conclusion = thinking_text, "No explicit conclusion."
                if "\nConclusion:" in thinking_text:
                    parts = thinking_text.split("\nConclusion:", 1); steps_text, conclusion = parts[0], parts[1].strip()
                elif "\n\nConclusion:" in thinking_text:
                     parts = thinking_text.split("\n\nConclusion:", 1); steps_text, conclusion = parts[0], parts[1].strip()   
                
                parsed_steps = []
                step_pattern = re.compile(r"Step\s*(\d+)[:.]\s*(.*?)(?=Step\s*\d+[:.]|$)", re.DOTALL | re.IGNORECASE)
                matches = step_pattern.findall(steps_text + "\n")
                for num, content in matches: parsed_steps.append({"number": int(num), "content": content.strip()})

                # Simplified parsing logic for fallback - ensure it's robust or identical to above
                if not parsed_steps and steps_text: # Fallback parsing
                    lines = steps_text.split('\n')
                    current_step_num = 0; current_step_content = []
                    for line in lines:
                        match = re.match(r"Step\s*(\d+)[:.]?\s*(.*)", line, re.IGNORECASE)
                        if match:
                            if current_step_num > 0: parsed_steps.append({"number": current_step_num, "content": "\n".join(current_step_content).strip()})
                            current_step_num = int(match.group(1)); current_step_content = [match.group(2).strip()]
                        elif current_step_num > 0: current_step_content.append(line.strip())
                    if current_step_num > 0: parsed_steps.append({"number": current_step_num, "content": "\n".join(current_step_content).strip()})
                
                return {"success": True, "steps": parsed_steps, "conclusion": conclusion, "thinking_type": thinking_type}
            except Exception as e:
                logger.error(f"[THINKING_MCP_DIRECT_FALLBACK] Error: {e}", exc_info=True)
                return {"success": False, "steps": [], "conclusion": f"Error: {str(e)}", "thinking_type": thinking_type, "error": str(e)}

        async def think(self, prompt, thinking_type="general", max_steps=5):
            if self.mcp_thinking_available:
                logger.debug(f"[THINKING_MCP] Attempting to use MCP server for: {prompt[:50]}...")
                all_steps_content = []
                current_thought_number = 1
                # The initial 'thought' for the MCP server is the user's prompt.
                # For now, we'll resend the original prompt as 'thought' for simplicity, as the server should track state by thoughtNumber.

                for i_step in range(max_steps): # Loop up to max_steps as a safeguard
                    mcp_args = {
                        "thought": prompt, # Using the original prompt as the 'thought' context for each step
                        "nextThoughtNeeded": True, # We always expect the server to tell us if it's done
                        "thoughtNumber": current_thought_number,
                        "totalThoughts": max_steps, # Informing the server of the desired length
                        "thinking_type": thinking_type
                        # Optional fields like isRevision, revisesThought are omitted
                    }

                    log_args_display = {key: (val[:50] + '...' if key == 'thought' and isinstance(val, str) and len(val) > 50 else val) 
                                        for key, val in mcp_args.items()}
                    logger.debug(f"[THINKING_MCP] Calling MCP step {current_thought_number} with args: {log_args_display}")
                    
                    mcp_call_result = await self._run_mcp_server(tool_name=self.mcp_tool_name, args=mcp_args)

                    if not mcp_call_result.get("success"):
                        logger.warning(f"[THINKING_MCP] MCP client-level error at step {current_thought_number}: {mcp_call_result.get('error', 'Unknown error')}. Falling back.")
                        return await self._think_direct(prompt, thinking_type, max_steps)

                    try:
                        mcp_response_str_list = mcp_call_result.get("raw_content", [])
                        if not isinstance(mcp_response_str_list, list):
                             mcp_response_str_list = [str(mcp_response_str_list)]
                        
                        mcp_response_str = "".join(mcp_response_str_list).strip()

                        if not mcp_response_str:
                            logger.warning(f"[THINKING_MCP] MCP server returned empty content at step {current_thought_number}.")
                            if current_thought_number == 1:
                                return await self._think_direct(prompt, thinking_type, max_steps)
                            else:
                                logger.info(f"[THINKING_MCP] Treating empty content as end of process.")
                                final_conclusion = mcp_server_output.get("conclusion") if 'mcp_server_output' in locals() else "MCP process ended with empty step."
                                break 

                        mcp_server_output = json.loads(mcp_response_str)
                    except json.JSONDecodeError as je:
                        logger.warning(f"[THINKING_MCP] Failed to parse JSON from MCP server at step {current_thought_number}: '{mcp_response_str}'. Error: {je}. Falling back.")
                        return await self._think_direct(prompt, thinking_type, max_steps)
                    except Exception as e:
                        logger.error(f"[THINKING_MCP] Unexpected error processing MCP server output at step {current_thought_number}: {e}. Content: '{mcp_response_str}'. Falling back.", exc_info=True)
                        return await self._think_direct(prompt, thinking_type, max_steps)
                    
                    current_step_thought = mcp_server_output.get("currentThought")
                    
                    has_error_indicator = "error" in mcp_server_output or \
                                          any(err_kw in mcp_response_str.lower() for err_kw in ["unknown tool", "traceback", "exception", "failed"])

                    if current_step_thought is None and has_error_indicator:
                         logger.warning(f"[THINKING_MCP] MCP server response at step {current_thought_number} suggests an error: {mcp_response_str}. Falling back.")
                         return await self._think_direct(prompt, thinking_type, max_steps)
                    
                    if current_step_thought is not None:
                        all_steps_content.append({
                            "number": mcp_server_output.get("thoughtNumber", current_thought_number), 
                            "content": current_step_thought
                        })
                    
                    final_conclusion = mcp_server_output.get("conclusion")

                    if not mcp_server_output.get("nextThoughtNeeded", False):
                        logger.info(f"[THINKING_MCP] MCP thinking completed after {current_thought_number} steps as indicated by server.")
                        return {
                            "success": True,
                            "steps": all_steps_content,
                            "conclusion": final_conclusion if final_conclusion else "MCP process completed.",
                            "thinking_type": "mcp_sequential"
                        }
                    
                    current_thought_number += 1
                    if i_step == max_steps -1 and mcp_server_output.get("nextThoughtNeeded", False):
                        logger.warning(f"[THINKING_MCP] Reached max_steps ({max_steps}) but MCP server indicates more thoughts are available.")

                conclusion_after_loop = "MCP process reached max steps or ended."
                if 'mcp_server_output' in locals() and mcp_server_output and mcp_server_output.get("conclusion"):
                    conclusion_after_loop = mcp_server_output.get("conclusion")
                elif not all_steps_content and current_thought_number > 1 :
                     conclusion_after_loop = "MCP process ended after first step with no further content."

                logger.info(f"[THINKING_MCP] MCP thinking loop finished. Collected {len(all_steps_content)} steps.")
                return {
                    "success": True,
                    "steps": all_steps_content,
                    "conclusion": conclusion_after_loop,
                    "thinking_type": "mcp_sequential_incomplete" if len(all_steps_content) < max_steps and current_thought_number > len(all_steps_content) else "mcp_sequential"
                }
            else: # self.mcp_thinking_available is False
                logger.debug(f"[THINKING_MCP] MCP not available/configured. Using direct OpenAI for: {prompt[:50]}...")
                return await self._think_direct(prompt, thinking_type, max_steps)

        
        async def solve_problem(self, problem, max_steps=5):
            return await self.think(problem, thinking_type="problem-solving", max_steps=max_steps)
        
        async def plan_code(self, coding_task, max_steps=7): # Usually needs more steps
            return await self.think(coding_task, thinking_type="coding", max_steps=max_steps)

except ImportError:
    logger.warning("mcp.client.stdio or mcp.client.session not found for SequentialThinking. Server will use direct OpenAI calls only.")
    class SequentialThinkingMCPServer: # Fallback class if MCP client components are missing
        def __init__(self):
            self.params = {}
            self.mcp_tool_name = ""
            self.mcp_thinking_available = False
            config_path = "thinking.json"
            server_key = "sequential-thinking"
            expected_tool_name = "sequential_thinking" # From the MCP server's README

            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                    
                    if server_key in config.get("mcpServers", {}):
                        server_config = config["mcpServers"][server_key]
                        self.params["command"] = server_config.get("command")
                        self.params["args"] = server_config.get("args", [])
                        self.params["env"] = server_config.get("env", os.environ.copy())
                        self.mcp_tool_name = expected_tool_name

                        if self.params["command"] and self.mcp_tool_name:
                            self.mcp_thinking_available = True
                            logger.info(f"SequentialThinkingMCPServer initialized to use MCP server '{server_key}' with tool '{self.mcp_tool_name}'.")
                        else:
                            logger.warning(f"SequentialThinkingMCPServer: Missing command or tool_name for '{server_key}' in {config_path}. Falling back to direct OpenAI.")
                    else:
                        logger.warning(f"SequentialThinkingMCPServer: Entry for '{server_key}' not found in {config_path}. Falling back to direct OpenAI.")
                else:
                    logger.warning(f"SequentialThinkingMCPServer: MCP config file {config_path} not found. Falling back to direct OpenAI.")
            except Exception as e:
                logger.error(f"SequentialThinkingMCPServer: Error loading MCP config from {config_path}: {e}. Falling back to direct OpenAI.", exc_info=True)
            
            if not self.mcp_thinking_available:
                logger.info("SequentialThinkingMCPServer initialized in simplified (direct OpenAI) mode as fallback.")
                # Re-define _think_direct, think, solve_problem, plan_code as above if needed,
                # or simply make the main class's _think_direct the only path.
                # For brevity, assuming the _think_direct from the try block is sufficient as the fallback.
                # The methods will be identical to the _think_direct and its wrappers in the try block.
                
        async def _think_direct(self, prompt, thinking_type="general", max_steps=5):
            # This is a duplication of the _think_direct method from the 'try' block.
            # In a real scenario, you might structure this to avoid duplication.
            logger.debug(f"[THINKING_MCP_DIRECT_FALLBACK] Using direct OpenAI for: {prompt[:50]}...")
            try:
                api_key = os.environ.get("OPENAI_API_KEY")
                if not api_key:
                    logger.error("[THINKING_MCP_DIRECT_FALLBACK] OPENAI_API_KEY not set.")
                    return {"success": False, "steps": [], "conclusion": "OPENAI_API_KEY not configured.", "thinking_type": thinking_type, "error": "API key missing"}

                client = openai.AsyncOpenAI(api_key=api_key)
                system_messages = {
                    "general": f"You are a thinking assistant. Break down this problem or question into clear, step-by-step reasoning. Provide exactly {max_steps-2}-{max_steps} steps... Each step should start with 'Step X:'. End with 'Conclusion:'.",
                    "problem-solving": f"You are a problem-solving assistant... Provide {max_steps-1}-{max_steps+1} steps... Each step 'Step X:'. End with 'Conclusion:'.",
                    "coding": f"You are a coding assistant... Provide {max_steps-1}-{max_steps+2} steps... Each step 'Step X:'. End with 'Conclusion:'."
                } # Truncated for brevity, use full prompts from above
                system_message = system_messages.get(thinking_type, system_messages["general"])
                
                response = await client.chat.completions.create(
                    model=os.environ.get("OPENAI_MODEL", "gpt-4.1"),
                    messages=[ {"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
                )
                thinking_text = response.choices[0].message.content
                
                steps_text, conclusion = thinking_text, "No explicit conclusion."
                if "\nConclusion:" in thinking_text:
                    parts = thinking_text.split("\nConclusion:", 1); steps_text, conclusion = parts[0], parts[1].strip()
                elif "\n\nConclusion:" in thinking_text:
                     parts = thinking_text.split("\n\nConclusion:", 1); steps_text, conclusion = parts[0], parts[1].strip()   
                
                parsed_steps = []
                step_pattern = re.compile(r"Step\s*(\d+)[:.]\s*(.*?)(?=Step\s*\d+[:.]|$)", re.DOTALL | re.IGNORECASE)
                matches = step_pattern.findall(steps_text + "\n")
                for num, content in matches: parsed_steps.append({"number": int(num), "content": content.strip()})

                # Simplified parsing logic for fallback - ensure it's robust or identical to above
                if not parsed_steps and steps_text: # Fallback parsing
                    lines = steps_text.split('\n')
                    current_step_num = 0; current_step_content = []
                    for line in lines:
                        match = re.match(r"Step\s*(\d+)[:.]?\s*(.*)", line, re.IGNORECASE)
                        if match:
                            if current_step_num > 0: parsed_steps.append({"number": current_step_num, "content": "\n".join(current_step_content).strip()})
                            current_step_num = int(match.group(1)); current_step_content = [match.group(2).strip()]
                        elif current_step_num > 0: current_step_content.append(line.strip())
                    if current_step_num > 0: parsed_steps.append({"number": current_step_num, "content": "\n".join(current_step_content).strip()})
                
                return {"success": True, "steps": parsed_steps, "conclusion": conclusion, "thinking_type": thinking_type}
            except Exception as e:
                logger.error(f"[THINKING_MCP_DIRECT_FALLBACK] Error: {e}", exc_info=True)
                return {"success": False, "steps": [], "conclusion": f"Error: {str(e)}", "thinking_type": thinking_type, "error": str(e)}

        async def think(self, prompt, thinking_type="general", max_steps=5):
            if self.mcp_thinking_available:
                logger.debug(f"[THINKING_MCP] Attempting to use MCP server for: {prompt[:50]}...")
                mcp_args = {
                    "thought": prompt,
                    "nextThoughtNeeded": True,  # For the initial call, we always need the first thought
                    "thoughtNumber": 1,
                    "totalThoughts": max_steps, # Corresponds to the agent's request for complexity
                    "thinking_type": thinking_type # Pass along for richer context if the MCP server uses it
                    # Optional fields like isRevision, revisesThought, etc., are omitted for initial call
                }
                result = await self._run_mcp_server(tool_name=self.mcp_tool_name, args=mcp_args)
                
                if result.get("success"):
                    # The result from _run_mcp_server should already be in the desired format.
                    # We need to ensure its 'raw_content' doesn't indicate an internal MCP server error.
                    raw_content_str = "".join(result.get("raw_content", []))
                    if "Unknown tool" in raw_content_str or "error" in raw_content_str.lower(): # Check for errors from MCP server itself
                        logger.warning(f"[THINKING_MCP] MCP server reported an issue: {raw_content_str}. Falling back to direct OpenAI.")
                        return await self._think_direct(prompt, thinking_type, max_steps)
                    logger.info(f"[THINKING_MCP] Successfully completed thinking via MCP. Conclusion: {result.get('conclusion', 'N/A')[:100]}...")
                else:
                    logger.warning(f"[THINKING_MCP] MCP thinking failed at client level: {result.get('error', 'Unknown error')}. Falling back to direct OpenAI.")
                    return await self._think_direct(prompt, thinking_type, max_steps)
                return result
            else:
                logger.debug(f"[THINKING_MCP] MCP not available/configured. Using direct OpenAI for: {prompt[:50]}...")
                return await self._think_direct(prompt, thinking_type, max_steps)
        
        async def solve_problem(self, problem, max_steps=5):
            return await self.think(problem, thinking_type="problem-solving", max_steps=max_steps)
        
        async def plan_code(self, coding_task, max_steps=7): # Usually needs more steps
            return await self.think(coding_task, thinking_type="coding", max_steps=max_steps)

thinking_mcp_server = SequentialThinkingMCPServer()


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
# thinking_mcp_server
# filesystem_mcp_server
