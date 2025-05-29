"""
Compatibility layer for MCP servers to maintain API compatibility with the original implementation.

This module provides adapter classes that wrap the direct service implementations
to maintain the same API as the original MCP servers.
"""
from typing import Dict, Any, List, Optional

from services.base_service import BaseService
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
    
    async def add_memory(self, user_id: str, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new memory for a specific user."""
        return await self.service.add_memory(user_id, memory)
    
    async def get_memory(self, user_id: str, memory_id: str) -> Dict[str, Any]:
        """Get a specific memory for a user."""
        return await self.service.get_memory(user_id, memory_id)
    
    async def update_memory(self, user_id: str, memory_id: str, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Update a specific memory for a user."""
        return await self.service.update_memory(user_id, memory_id, memory)
    
    async def delete_memory(self, user_id: str, memory_id: str) -> Dict[str, Any]:
        """Delete a specific memory for a user."""
        return await self.service.delete_memory(user_id, memory_id)
    
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
    
    async def get_product(self, product_id: str) -> Dict[str, Any]:
        """Get a specific product by ID from the Shopify store."""
        return await self.service.get_product(product_id)
    
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
shopify_mcp_server = ShopifyServiceAdapter()  # For original code compatibility
shopify_features_mcp_server = ShopifyServiceAdapter()  # For original code compatibility
thinking_mcp_server = ThinkingServiceAdapter()
filesystem_mcp_server = FilesystemServiceAdapter()
