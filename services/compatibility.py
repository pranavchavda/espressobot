"""
Compatibility layer for MCP server integration.
Provides adapters to maintain compatibility with existing MCP server code.
"""
import asyncio
from typing import Any, Dict, Optional, List, Callable, Awaitable

from services.memory_service import memory_service
from services.fetch_service import fetch_service
from services.shopify_service import shopify_service
from services.thinking_service import thinking_service
from services.filesystem_service import filesystem_service

class MemoryServiceAdapter:
    """
    Adapter for memory service to maintain compatibility with MCPMemoryServer.
    """
    def __init__(self):
        self.service = memory_service
    
    async def store_memory(self, user_id: str, key: str, value: Any) -> Dict[str, Any]:
        """Store a memory for a specific user."""
        return await self.service.store_memory(user_id, key, value)
    
    async def retrieve_memory(self, user_id: str, key: str) -> Dict[str, Any]:
        """Retrieve a memory for a specific user."""
        return await self.service.retrieve_memory(user_id, key)
    
    async def delete_memory(self, user_id: str, key: str) -> Dict[str, Any]:
        """Delete a memory for a specific user."""
        return await self.service.delete_memory(user_id, key)
    
    async def list_memories(self, user_id: str) -> Dict[str, Any]:
        """List all memories for a specific user."""
        return await self.service.list_memories(user_id)
    
    # Add any other methods from the original MCPMemoryServer as needed

class FetchServiceAdapter:
    """
    Adapter for fetch service to maintain compatibility with FetchMCPServer.
    """
    def __init__(self):
        self.service = fetch_service
    
    async def fetch_url(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch raw content from a URL with metadata."""
        return await self.service.fetch_url(url, options)
    
    async def fetch_and_extract_text(self, url: str, selector: Optional[str] = None) -> Dict[str, Any]:
        """Fetch a webpage and extract text content."""
        return await self.service.fetch_and_extract_text(url, selector)
    
    async def fetch_json(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch and parse JSON from a URL."""
        return await self.service.fetch_json(url, options)
    
    # Add any other methods from the original FetchMCPServer as needed

class ShopifyServiceAdapter:
    """
    Adapter for shopify service to maintain compatibility with ShopifyMCPServer.
    """
    def __init__(self):
        self.service = shopify_service
    
    async def query_admin_api(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query against the Shopify Admin API."""
        return await self.service.query_admin_api(query, variables)
    
    async def get_products(self, limit: int = 10, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get products from the Shopify store."""
        return await self.service.get_products(limit, cursor)
    
    async def get_orders(self, limit: int = 10, cursor: Optional[str] = None) -> Dict[str, Any]:
        """Get orders from the Shopify store."""
        return await self.service.get_orders(limit, cursor)
    
    async def search_products(self, query_text: str, limit: int = 10) -> Dict[str, Any]:
        """Search for products in the Shopify store."""
        return await self.service.search_products(query_text, limit)
    
    # Add any other methods from the original ShopifyMCPServer as needed

class ThinkingServiceAdapter:
    """
    Adapter for thinking service to maintain compatibility with SequentialThinkingMCPServer.
    """
    def __init__(self):
        self.service = thinking_service
    
    async def think(self, prompt: str, thinking_type: str = "general", max_steps: Optional[int] = None) -> Dict[str, Any]:
        """Perform step-by-step thinking on a prompt."""
        return await self.service.think(prompt, thinking_type, max_steps)
    
    async def solve_problem(self, problem: str, max_steps: Optional[int] = None) -> Dict[str, Any]:
        """Perform problem-solving thinking."""
        return await self.service.solve_problem(problem, max_steps)
    
    async def plan_code(self, coding_task: str, max_steps: Optional[int] = None) -> Dict[str, Any]:
        """Perform code planning thinking."""
        return await self.service.plan_code(coding_task, max_steps)
    
    # Add any other methods from the original SequentialThinkingMCPServer as needed

class FilesystemServiceAdapter:
    """
    Adapter for filesystem service to maintain compatibility with FileSystemMCPServer.
    """
    def __init__(self):
        self.service = filesystem_service
    
    async def read_file(self, path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Read a file from the controlled storage."""
        return await self.service.read_file(path, user_id)
    
    async def write_file(self, path: str, content: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Write content to a file in the controlled storage."""
        return await self.service.write_file(path, content, user_id)
    
    async def list_directory(self, path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """List contents of a directory in the controlled storage."""
        return await self.service.list_directory(path, user_id)
    
    async def delete_file(self, path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Delete a file from the controlled storage."""
        return await self.service.delete_file(path, user_id)
    
    async def check_file_exists(self, path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Check if a file exists in the controlled storage."""
        return await self.service.check_file_exists(path, user_id)
    
    # Add any other methods from the original FileSystemMCPServer as needed

# Create adapter instances
memory_server = MemoryServiceAdapter()
fetch_mcp_server = FetchServiceAdapter()
shopify_mcp_server = ShopifyServiceAdapter()
thinking_mcp_server = ThinkingServiceAdapter()
filesystem_mcp_server = FilesystemServiceAdapter()
