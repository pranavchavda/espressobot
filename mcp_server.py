"""
Module for handling MCP server connections for Shopify Dev MCP
"""
import os
import asyncio
from agents.mcp.server import MCPServerStdio
import httpx
from typing import Dict, Any, List, Optional
from datetime import timedelta
from mcp.client.session import ClientSession as MCPClientSession

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
_patch_mcp_client_timeout()

class ShopifyMCPServer:
    """
    A class to handle communication with a local Shopify Dev MCP server instance.
    This spawns an npx process running @shopify/dev-mcp to provide schema information
    and documentation search capabilities.
    """
    def __init__(self):
        # Params for local Shopify Dev MCP server
        self.params = {"command": "npx", "args": ["-y", "@shopify/dev-mcp@latest"]}
        self.cache = True
    
    async def introspect_admin_schema(self, query, filter_types=None):
        """Query the Shopify Admin API schema using the MCP server"""
        if filter_types is None:
            filter_types = ["all"]
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
            return await server.call_tool(
                "introspect_admin_schema", {"query": query, "filter": filter_types}
            )
    
    async def search_dev_docs(self, prompt):
        """Search Shopify developer documentation using the MCP server"""
        async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
            return await server.call_tool(
                "search_dev_docs", {"prompt": prompt}
            )
    
    def stop(self):
        """Stop the MCP server process (no-op; context manager handles teardown)"""
        pass

# Create a singleton instance
mcp_server = ShopifyMCPServer()

class PerplexityMCPServer:
    """
    A class to handle communication with a local Perplexity MCP server instance.
    This spawns an npx process running server-perplexity-ask.
    """
    def __init__(self):
        self.params = {
            "command": "npx",
            "args": ["-y", "server-perplexity-ask"],
            "env": {
                "PERPLEXITY_API_KEY": os.environ.get("PERPLEXITY_API_KEY", "")
            }
        }
        self.cache = True

    async def perplexity_ask(self, messages):
        """Ask Perplexity a question using the MCP server."""
        print("[MCP_SERVER_DEBUG] Attempting to start Perplexity MCP server...")
        try:
            async with MCPServerStdio(params=self.params, cache_tools_list=self.cache) as server:
                print("[MCP_SERVER_DEBUG] Perplexity MCP server context entered. Calling tool...")
                try:
                    tool_response = await server.call_tool(
                        "perplexity_ask", {"messages": messages}
                    )
                    print(f"[MCP_SERVER_DEBUG] Perplexity MCP tool_response: {str(tool_response)[:200]}...") # Log snippet
                    return tool_response
                except asyncio.TimeoutError as e:
                    print(f"[MCP_SERVER_DEBUG] asyncio.TimeoutError during Perplexity call_tool: {e}")
                    raise # Re-raise the timeout to be handled by the agent
                except Exception as e:
                    print(f"[MCP_SERVER_DEBUG] Exception during Perplexity call_tool: {e}")
                    return {"error": f"Exception in Perplexity MCP: {str(e)}"}
        except Exception as e:
            print(f"[MCP_SERVER_DEBUG] Exception during Perplexity MCPServerStdio setup: {e}")
            return {"error": f"Exception setting up Perplexity MCP: {str(e)}"}

perplexity_mcp_server = PerplexityMCPServer()
