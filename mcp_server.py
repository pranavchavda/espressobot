"""
Module for handling MCP server connections for Shopify Dev MCP and Perplexity Ask
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

# Import agents package for MCP server communication
from agents.mcp.server import MCPServerStdio
from mcp.client.session import ClientSession as MCPClientSession

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
    and documentation search capabilities.
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
            print(f"[DEBUG] Starting introspect_admin_schema with query: {query}")
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                print(f"[DEBUG] MCPServerStdio context entered for schema introspection")
                raw_result = await server.call_tool(
                    "introspect_admin_schema", {"query": query, "filter": filter_types}
                )
                
                # Log the raw response for debugging
                print(f"[DEBUG] Raw introspect_admin_schema result type: {type(raw_result)}")
                print(f"[DEBUG] Raw introspect_admin_schema attributes: {dir(raw_result)[:200]}")
                
                # Convert CallToolResult to dictionary for proper JSON serialization
                result = {
                    "meta": getattr(raw_result, "meta", None),
                    "content": [],
                    "isError": getattr(raw_result, "isError", False)
                }
                
                # Extract content items
                if hasattr(raw_result, "content"):
                    for content_item in raw_result.content:
                        # Get full text content
                        text_content = getattr(content_item, "text", "")
                        print(f"[DEBUG] Schema content item type: {getattr(content_item, 'type', None)}")
                        print(f"[DEBUG] Schema content text length: {len(text_content)} chars")
                        
                        # Preserve the complete text content
                        result["content"].append({
                            "type": getattr(content_item, "type", None),
                            "text": text_content,
                            "annotations": getattr(content_item, "annotations", None)
                        })
                
                # Log the final result for debugging
                print(f"[DEBUG] Final introspect_admin_schema result content items: {len(result['content'])}")
                
                return result
        except Exception as e:
            print(f"Error in introspect_admin_schema: {e}")
            # Fallback response
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"## Matching GraphQL Types for '{query}':\nError connecting to Shopify MCP server: {str(e)}\n\nPlease check the Shopify Admin API documentation for accurate schema information.",
                    "annotations": None
                }],
                "isError": False
            }
    
    async def search_dev_docs(self, prompt):
        """Search Shopify developer documentation using the MCP server"""
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                raw_result = await server.call_tool(
                    "search_dev_docs", {"prompt": prompt}
                )
                
                # Log the raw response for debugging
                print(f"[DEBUG] Raw search_dev_docs result type: {type(raw_result)}")
                print(f"[DEBUG] Raw search_dev_docs attributes: {dir(raw_result)[:200]}")
                
                # Convert CallToolResult to dictionary for proper JSON serialization
                result = {
                    "meta": getattr(raw_result, "meta", None),
                    "content": [],
                    "isError": getattr(raw_result, "isError", False)
                }
                
                # Extract content items
                if hasattr(raw_result, "content"):
                    for content_item in raw_result.content:
                        # Get full text content
                        text_content = getattr(content_item, "text", "")
                        print(f"[DEBUG] Content item type: {getattr(content_item, 'type', None)}")
                        print(f"[DEBUG] Content text length: {len(text_content)} chars")
                        
                        # Preserve the complete text content
                        result["content"].append({
                            "type": getattr(content_item, "type", None),
                            "text": text_content,
                            "annotations": getattr(content_item, "annotations", None)
                        })
                
                # Log the final result for debugging
                print(f"[DEBUG] Final result content items: {len(result['content'])}")
                
                return result
        except Exception as e:
            print(f"Error in search_dev_docs: {e}")
            # Fallback response
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"## Search Results for '{prompt}':\nError connecting to Shopify MCP server: {str(e)}\n\nPlease check the Shopify developer documentation for accurate information.",
                    "annotations": None
                }],
                "isError": False
            }
    
    def stop(self):
        """Stop the MCP server process (no-op; context manager handles teardown)"""
        pass
    
    def _get_mock_docs_response(self, prompt):
        """Get a mock documentation response when the MCP server fails"""
        
        # Basic mock response with common Shopify documentation
        mock_content = f"""## Search Results for '{prompt}':

### Shopify Admin API

The Shopify Admin API lets you build apps that extend Shopify's admin functionality. You can use the Admin API to create apps that integrate with merchants' stores and help them run their businesses.

**Key Resources:**
- [Admin API Overview](https://shopify.dev/api/admin) - Learn about the Admin API and how to use it
- [GraphQL Admin API](https://shopify.dev/api/admin-graphql) - Use GraphQL to query and modify data in a Shopify store
- [REST Admin API](https://shopify.dev/api/admin-rest) - Use REST to interact with Shopify resources

### Common GraphQL Patterns

**Querying Products:**
```graphql
query {{
  products(first: 10) {{
    edges {{
      node {{
        id
        title
        handle
        variants(first: 5) {{
          edges {{
            node {{
              id
              title
              sku
              price
            }}
          }}
        }}
      }}
    }}
  }}
}}
```

**Creating a Product:**
```graphql
mutation {{
  productCreate(input: {{
    title: "New Product",
    productType: "Accessories",
    vendor: "My Store",
    status: DRAFT
  }}) {{
    product {{
      id
      title
    }}
    userErrors {{
      field
      message
    }}
  }}
}}
```

For more specific information, please refer to the [official Shopify documentation](https://shopify.dev/docs).
"""
        
        return {
            "meta": None,
            "content": [{
                "type": "text",
                "text": mock_content,
                "annotations": None
            }],
            "isError": False
        }
    
    def stop(self):
        """Stop the MCP server process (no-op)"""
        pass

# Create a singleton instance
mcp_server = ShopifyMCPServer()

class PerplexityMCPServer:
    """
    A class to handle communication with a local Perplexity MCP server instance.
    This spawns an npx process running server-perplexity-ask.
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
        print("[MCP_SERVER_DEBUG] Attempting to start Perplexity MCP server...")
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                print("[MCP_SERVER_DEBUG] Perplexity MCP server context entered. Calling tool...")
                try:
                    raw_result = await server.call_tool(
                        "perplexity_ask", {"messages": messages}
                    )
                    print(f"[MCP_SERVER_DEBUG] Perplexity MCP raw_result: {str(raw_result)[:200]}...") # Log snippet
                    
                    # Convert CallToolResult to dictionary for proper JSON serialization
                    result = {
                        "meta": getattr(raw_result, "meta", None),
                        "content": [],
                        "isError": getattr(raw_result, "isError", False)
                    }
                    
                    # Extract content items
                    if hasattr(raw_result, "content"):
                        for content_item in raw_result.content:
                            result["content"].append({
                                "type": getattr(content_item, "type", None),
                                "text": getattr(content_item, "text", None),
                                "annotations": getattr(content_item, "annotations", None)
                            })
                    
                    return result
                except asyncio.TimeoutError as e:
                    print(f"[MCP_SERVER_DEBUG] asyncio.TimeoutError during Perplexity call_tool: {e}")
                    # Fallback response
                    return {
                        "meta": None,
                        "content": [{
                            "type": "text",
                            "text": f"Timeout error connecting to Perplexity API: {str(e)}\n\nPlease try again later.",
                            "annotations": None
                        }],
                        "isError": False
                    }
                except Exception as e:
                    print(f"[MCP_SERVER_DEBUG] Exception during Perplexity call_tool: {e}")
                    return {
                        "meta": None,
                        "content": [{
                            "type": "text",
                            "text": f"Error connecting to Perplexity API: {str(e)}\n\nPlease try again later.",
                            "annotations": None
                        }],
                        "isError": False
                    }
        except Exception as e:
            print(f"[MCP_SERVER_DEBUG] Exception during Perplexity MCPServerStdio setup: {e}")
            return {
                "meta": None,
                "content": [{
                    "type": "text",
                    "text": f"Error setting up Perplexity MCP server: {str(e)}\n\nPlease try again later.",
                    "annotations": None
                }],
                "isError": False
            }

perplexity_mcp_server = PerplexityMCPServer()

class MemoryMCPServer:
    """
    A class to handle user-specific memory storage using the MCP memory server.
    This provides persistent memory capabilities for the Shopify agent, with each
    user having their own isolated memory space.
    """
    def __init__(self):
        # Ensure XDG_CONFIG_HOME is set
        if "XDG_CONFIG_HOME" not in os.environ:
            os.environ["XDG_CONFIG_HOME"] = os.path.expanduser("~/.config")
        
        # Create a copy of the current environment
        env_vars = os.environ.copy()
        
        self.params = {
            "command": "npx",
            "args": ["-y", "server-memory"],
            "env": env_vars
        }
        self.cache = True
    
    async def store_memory(self, user_id, key, value):
        """
        Store a memory for a specific user.
        
        Args:
            user_id: The user's ID to namespace the memory
            key: The memory key
            value: The value to store
            
        Returns:
            Dictionary with storage status
        """
        # Use user_id as part of the memory key for isolation
        memory_key = f"user_{user_id}:{key}"
        print(f"[MEMORY_MCP] Storing memory for user {user_id}: {key}")
        
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                raw_result = await server.call_tool(
                    "store", {"key": memory_key, "value": value}
                )
                
                # Convert result to dictionary for proper JSON serialization
                result = {
                    "success": True,
                    "key": memory_key,
                    "message": f"Memory stored successfully for user {user_id}"
                }
                
                return result
        except Exception as e:
            print(f"[MEMORY_MCP] Error storing memory: {e}")
            return {
                "success": False,
                "key": memory_key,
                "message": f"Error storing memory: {str(e)}"
            }
    
    async def retrieve_memory(self, user_id, key):
        """
        Retrieve a memory for a specific user.
        
        Args:
            user_id: The user's ID to namespace the memory
            key: The memory key to retrieve
            
        Returns:
            Dictionary with the retrieved memory or error
        """
        memory_key = f"user_{user_id}:{key}"
        print(f"[MEMORY_MCP] Retrieving memory for user {user_id}: {key}")
        
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                raw_result = await server.call_tool(
                    "retrieve", {"key": memory_key}
                )
                
                # Extract the value from the result
                if hasattr(raw_result, "content") and raw_result.content:
                    memory_value = raw_result.content[0].text if raw_result.content[0].text else None
                    
                    return {
                        "success": True,
                        "key": memory_key,
                        "value": memory_value
                    }
                else:
                    return {
                        "success": False,
                        "key": memory_key,
                        "message": "Memory not found",
                        "value": None
                    }
        except Exception as e:
            print(f"[MEMORY_MCP] Error retrieving memory: {e}")
            return {
                "success": False,
                "key": memory_key,
                "message": f"Error retrieving memory: {str(e)}",
                "value": None
            }
    
    async def list_memories(self, user_id):
        """
        List all memories for a specific user.
        
        Args:
            user_id: The user's ID to namespace the memories
            
        Returns:
            Dictionary with the list of memory keys for the user
        """
        user_prefix = f"user_{user_id}:"
        print(f"[MEMORY_MCP] Listing memories for user {user_id}")
        
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                raw_result = await server.call_tool("list", {})
                
                # Extract relevant user memories
                all_keys = []
                if hasattr(raw_result, "content") and raw_result.content:
                    try:
                        content_text = raw_result.content[0].text
                        all_keys = json.loads(content_text) if content_text else []
                    except json.JSONDecodeError:
                        # If not valid JSON, try parsing as a string list
                        content_text = raw_result.content[0].text
                        all_keys = content_text.split('\n') if content_text else []
                
                # Filter keys to only include those for this user
                user_keys = [key for key in all_keys if key.startswith(user_prefix)]
                
                # Strip the user prefix for clarity
                clean_keys = [key.replace(user_prefix, '') for key in user_keys]
                
                return {
                    "success": True,
                    "keys": clean_keys,
                    "count": len(clean_keys)
                }
        except Exception as e:
            print(f"[MEMORY_MCP] Error listing memories: {e}")
            return {
                "success": False,
                "keys": [],
                "message": f"Error listing memories: {str(e)}",
                "count": 0
            }
    
    async def delete_memory(self, user_id, key):
        """
        Delete a specific memory for a user.
        
        Args:
            user_id: The user's ID to namespace the memory
            key: The memory key to delete
            
        Returns:
            Dictionary with deletion status
        """
        memory_key = f"user_{user_id}:{key}"
        print(f"[MEMORY_MCP] Deleting memory for user {user_id}: {key}")
        
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                raw_result = await server.call_tool(
                    "delete", {"key": memory_key}
                )
                
                return {
                    "success": True,
                    "key": memory_key,
                    "message": f"Memory deleted successfully for user {user_id}"
                }
        except Exception as e:
            print(f"[MEMORY_MCP] Error deleting memory: {e}")
            return {
                "success": False,
                "key": memory_key,
                "message": f"Error deleting memory: {str(e)}"
            }

# Create a singleton instance
memory_mcp_server = MemoryMCPServer()

class FetchMCPServer:
    """
    A class to handle web content fetching using the MCP fetch server.
    This provides more robust web content retrieval than simple curl commands.
    """
    def __init__(self):
        # Ensure XDG_CONFIG_HOME is set
        if "XDG_CONFIG_HOME" not in os.environ:
            os.environ["XDG_CONFIG_HOME"] = os.path.expanduser("~/.config")
        
        # Create a copy of the current environment
        env_vars = os.environ.copy()
        
        self.params = {
            "command": "npx",
            "args": ["-y", "server-fetch"],
            "env": env_vars
        }
        self.cache = True
    
    async def fetch_url(self, url, options=None):
        """
        Fetch content from a URL using the MCP fetch server.
        
        Args:
            url: The URL to fetch
            options: Optional dict of fetch options (e.g., headers, timeout)
            
        Returns:
            Dictionary with the fetched content and metadata
        """
        if options is None:
            options = {}
            
        print(f"[FETCH_MCP] Fetching URL: {url}")
        
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                raw_result = await server.call_tool(
                    "fetch", {"url": url, **options}
                )
                
                # Extract the content from the result
                result = {
                    "success": True,
                    "url": url,
                    "content": "",
                    "status": 200,
                    "headers": {},
                    "content_type": ""
                }
                
                if hasattr(raw_result, "content") and raw_result.content:
                    # Extract text content
                    content_text = ""
                    for content_item in raw_result.content:
                        if hasattr(content_item, "text") and content_item.text:
                            content_text += content_item.text
                    
                    result["content"] = content_text
                    
                    # Try to extract metadata if available
                    if hasattr(raw_result, "meta") and raw_result.meta:
                        meta = raw_result.meta
                        if hasattr(meta, "status"):
                            result["status"] = meta.status
                        if hasattr(meta, "headers"):
                            result["headers"] = meta.headers
                        if hasattr(meta, "content_type"):
                            result["content_type"] = meta.content_type
                
                return result
        except Exception as e:
            print(f"[FETCH_MCP] Error fetching URL: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "content": "",
                "status": 0
            }
    
    async def fetch_and_extract_text(self, url, selector=None):
        """
        Fetch a URL and extract text content, optionally filtered by a CSS selector.
        
        Args:
            url: The URL to fetch
            selector: Optional CSS selector to filter content
            
        Returns:
            Dictionary with the extracted text content
        """
        print(f"[FETCH_MCP] Fetching and extracting text from URL: {url}")
        
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                tool_args = {"url": url}
                if selector:
                    tool_args["selector"] = selector
                    
                raw_result = await server.call_tool("extractText", tool_args)
                
                # Extract the text content from the result
                result = {
                    "success": True,
                    "url": url,
                    "text": "",
                    "status": 200
                }
                
                if hasattr(raw_result, "content") and raw_result.content:
                    # Combine all text content
                    content_text = ""
                    for content_item in raw_result.content:
                        if hasattr(content_item, "text") and content_item.text:
                            content_text += content_item.text
                    
                    result["text"] = content_text
                    
                    # Try to extract metadata if available
                    if hasattr(raw_result, "meta") and raw_result.meta:
                        meta = raw_result.meta
                        if hasattr(meta, "status"):
                            result["status"] = meta.status
                
                return result
        except Exception as e:
            print(f"[FETCH_MCP] Error extracting text from URL: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "text": "",
                "status": 0
            }
    
    async def fetch_json(self, url, options=None):
        """
        Fetch and parse JSON content from a URL.
        
        Args:
            url: The URL to fetch
            options: Optional dict of fetch options (e.g., headers, timeout)
            
        Returns:
            Dictionary with the parsed JSON content
        """
        if options is None:
            options = {}
            
        print(f"[FETCH_MCP] Fetching JSON from URL: {url}")
        
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                raw_result = await server.call_tool(
                    "fetchJson", {"url": url, **options}
                )
                
                # Extract the JSON content from the result
                result = {
                    "success": True,
                    "url": url,
                    "json": None,
                    "status": 200,
                    "headers": {}
                }
                
                if hasattr(raw_result, "content") and raw_result.content:
                    # Try to parse JSON content
                    try:
                        if raw_result.content[0].text:
                            result["json"] = json.loads(raw_result.content[0].text)
                    except (json.JSONDecodeError, IndexError) as json_err:
                        print(f"[FETCH_MCP] JSON parsing error: {json_err}")
                        result["success"] = False
                        result["error"] = f"JSON parsing error: {str(json_err)}"
                    
                    # Try to extract metadata if available
                    if hasattr(raw_result, "meta") and raw_result.meta:
                        meta = raw_result.meta
                        if hasattr(meta, "status"):
                            result["status"] = meta.status
                        if hasattr(meta, "headers"):
                            result["headers"] = meta.headers
                
                return result
        except Exception as e:
            print(f"[FETCH_MCP] Error fetching JSON: {e}")
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "json": None,
                "status": 0
            }

# Create a singleton instance
fetch_mcp_server = FetchMCPServer()

class SequentialThinkingMCPServer:
    """
    A class to handle structured, step-by-step thinking using the MCP sequential thinking server.
    This enhances the current <THINKING> tags with a more formal reasoning process.
    """
    def __init__(self):
        # Ensure XDG_CONFIG_HOME is set
        if "XDG_CONFIG_HOME" not in os.environ:
            os.environ["XDG_CONFIG_HOME"] = os.path.expanduser("~/.config")
        
        # Create a copy of the current environment
        env_vars = os.environ.copy()
        
        self.params = {
            "command": "npx",
            "args": ["-y", "server-sequential-thinking"],
            "env": env_vars
        }
        self.cache = True
    
    async def think(self, prompt, thinking_type="general", max_steps=5):
        """
        Perform structured step-by-step thinking on a prompt.
        
        Args:
            prompt: The prompt to think about
            thinking_type: Type of thinking (general, problem-solving, coding)
            max_steps: Maximum number of thinking steps
            
        Returns:
            Dictionary with the thinking steps and final conclusion
        """
        print(f"[THINKING_MCP] Starting sequential thinking process: {prompt[:50]}...")
        
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                raw_result = await server.call_tool(
                    "think", {
                        "prompt": prompt,
                        "type": thinking_type,
                        "max_steps": max_steps
                    }
                )
                
                # Convert result to a structured format
                result = {
                    "success": True,
                    "steps": [],
                    "conclusion": "",
                    "thinking_type": thinking_type
                }
                
                if hasattr(raw_result, "content") and raw_result.content:
                    # Try to parse thinking steps and conclusion
                    try:
                        thinking_text = raw_result.content[0].text
                        thinking_parts = thinking_text.split("\n\nConclusion: ")
                        
                        if len(thinking_parts) > 1:
                            # Extract steps and conclusion
                            steps_text = thinking_parts[0]
                            conclusion = thinking_parts[1].strip()
                            
                            # Parse steps
                            steps = []
                            step_lines = steps_text.split("\n")
                            current_step = ""
                            step_number = 0
                            
                            for line in step_lines:
                                if line.startswith("Step ") and ":" in line:
                                    # Save previous step if it exists
                                    if current_step and step_number > 0:
                                        steps.append({
                                            "number": step_number,
                                            "content": current_step.strip()
                                        })
                                    
                                    # Start new step
                                    step_parts = line.split(":", 1)
                                    try:
                                        step_number = int(step_parts[0].replace("Step ", "").strip())
                                    except ValueError:
                                        step_number = len(steps) + 1
                                        
                                    current_step = step_parts[1].strip() if len(step_parts) > 1 else ""
                                else:
                                    # Continue current step
                                    current_step += "\n" + line
                            
                            # Add the last step
                            if current_step and step_number > 0:
                                steps.append({
                                    "number": step_number,
                                    "content": current_step.strip()
                                })
                            
                            result["steps"] = steps
                            result["conclusion"] = conclusion
                        else:
                            # No clear conclusion format, use the whole text
                            result["conclusion"] = thinking_text.strip()
                    except Exception as e:
                        print(f"[THINKING_MCP] Error parsing thinking result: {e}")
                        result["steps"] = []
                        result["conclusion"] = raw_result.content[0].text
                
                return result
        except Exception as e:
            print(f"[THINKING_MCP] Error in sequential thinking: {e}")
            return {
                "success": False,
                "steps": [],
                "conclusion": f"Error in sequential thinking: {str(e)}",
                "thinking_type": thinking_type,
                "error": str(e)
            }
    
    async def solve_problem(self, problem, max_steps=5):
        """
        Apply problem-solving thinking to a specific problem.
        
        Args:
            problem: The problem to solve
            max_steps: Maximum number of thinking steps
            
        Returns:
            Dictionary with problem-solving steps and solution
        """
        return await self.think(problem, thinking_type="problem-solving", max_steps=max_steps)
    
    async def plan_code(self, coding_task, max_steps=5):
        """
        Plan coding implementation with step-by-step thinking.
        
        Args:
            coding_task: The coding task to plan
            max_steps: Maximum number of thinking steps
            
        Returns:
            Dictionary with coding plan steps and final implementation plan
        """
        return await self.think(coding_task, thinking_type="coding", max_steps=max_steps)

# Create a singleton instance
thinking_mcp_server = SequentialThinkingMCPServer()
