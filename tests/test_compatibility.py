"""
Integration test for the compatibility layer with the optimized services.
Tests that the compatibility layer maintains the same API as the original MCP servers.
"""
import os
import sys
import json
import unittest
import asyncio
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.compatibility import (
    memory_server,
    fetch_mcp_server,
    shopify_mcp_server,
    thinking_mcp_server,
    filesystem_mcp_server
)

class TestCompatibilityLayer(unittest.TestCase):
    """Test cases for the compatibility layer."""
    
    def test_memory_server_adapter(self):
        """Test that the memory server adapter maintains the same API."""
        # Verify that the adapter has the same methods as the original MCP server
        self.assertTrue(hasattr(memory_server, 'store_memory'))
        self.assertTrue(hasattr(memory_server, 'retrieve_memory'))
        self.assertTrue(hasattr(memory_server, 'delete_memory'))
        self.assertTrue(hasattr(memory_server, 'list_memories'))
        
        # Mock the underlying service
        with patch('services.memory_service.memory_service.store_memory') as mock_store:
            mock_store.return_value = {"success": True, "user_id": "1", "key": "test_key"}
            
            # Run the async test
            result = asyncio.run(self._test_memory_adapter_async())
            
            # Verify result
            self.assertTrue(result["success"])
            self.assertEqual(result["user_id"], "1")
            self.assertEqual(result["key"], "test_key")
            
            # Verify the service method was called with the correct arguments
            mock_store.assert_called_once_with("1", "test_key", "test_value")
    
    async def _test_memory_adapter_async(self):
        """Async implementation of test_memory_adapter."""
        return await memory_server.store_memory("1", "test_key", "test_value")
    
    def test_fetch_server_adapter(self):
        """Test that the fetch server adapter maintains the same API."""
        # Verify that the adapter has the same methods as the original MCP server
        self.assertTrue(hasattr(fetch_mcp_server, 'fetch_url'))
        self.assertTrue(hasattr(fetch_mcp_server, 'fetch_and_extract_text'))
        self.assertTrue(hasattr(fetch_mcp_server, 'fetch_json'))
        
        # Mock the underlying service
        with patch('services.fetch_service.fetch_service.fetch_url') as mock_fetch:
            mock_fetch.return_value = {
                "success": True,
                "url": "https://example.com",
                "content": "<html>Test</html>"
            }
            
            # Run the async test
            result = asyncio.run(self._test_fetch_adapter_async())
            
            # Verify result
            self.assertTrue(result["success"])
            self.assertEqual(result["url"], "https://example.com")
            self.assertEqual(result["content"], "<html>Test</html>")
            
            # Verify the service method was called with the correct arguments
            mock_fetch.assert_called_once_with("https://example.com", {"headers": {"User-Agent": "Test"}})
    
    async def _test_fetch_adapter_async(self):
        """Async implementation of test_fetch_adapter."""
        return await fetch_mcp_server.fetch_url("https://example.com", {"headers": {"User-Agent": "Test"}})
    
    def test_shopify_server_adapter(self):
        """Test that the shopify server adapter maintains the same API."""
        # Verify that the adapter has the same methods as the original MCP server
        self.assertTrue(hasattr(shopify_mcp_server, 'query_admin_api'))
        self.assertTrue(hasattr(shopify_mcp_server, 'get_products'))
        self.assertTrue(hasattr(shopify_mcp_server, 'get_orders'))
        self.assertTrue(hasattr(shopify_mcp_server, 'search_products'))
        
        # Mock the underlying service
        with patch('services.shopify_service.shopify_service.query_admin_api') as mock_query:
            mock_query.return_value = {
                "success": True,
                "data": {"products": {"edges": []}}
            }
            
            # Run the async test
            result = asyncio.run(self._test_shopify_adapter_async())
            
            # Verify result
            self.assertTrue(result["success"])
            self.assertEqual(result["data"], {"products": {"edges": []}})
            
            # Verify the service method was called with the correct arguments
            mock_query.assert_called_once_with("query { products { edges { node { id } } } }", {"limit": 10})
    
    async def _test_shopify_adapter_async(self):
        """Async implementation of test_shopify_adapter."""
        return await shopify_mcp_server.query_admin_api("query { products { edges { node { id } } } }", {"limit": 10})
    
    def test_thinking_server_adapter(self):
        """Test that the thinking server adapter maintains the same API."""
        # Verify that the adapter has the same methods as the original MCP server
        self.assertTrue(hasattr(thinking_mcp_server, 'think'))
        self.assertTrue(hasattr(thinking_mcp_server, 'solve_problem'))
        self.assertTrue(hasattr(thinking_mcp_server, 'plan_code'))
        
        # Mock the underlying service
        with patch('services.thinking_service.thinking_service.think') as mock_think:
            mock_think.return_value = {
                "success": True,
                "steps": ["Step 1", "Step 2"],
                "conclusion": "Conclusion"
            }
            
            # Run the async test
            result = asyncio.run(self._test_thinking_adapter_async())
            
            # Verify result
            self.assertTrue(result["success"])
            self.assertEqual(result["steps"], ["Step 1", "Step 2"])
            self.assertEqual(result["conclusion"], "Conclusion")
            
            # Verify the service method was called with the correct arguments
            mock_think.assert_called_once_with("How to solve this problem?", "general", 5)
    
    async def _test_thinking_adapter_async(self):
        """Async implementation of test_thinking_adapter."""
        return await thinking_mcp_server.think("How to solve this problem?", "general", 5)
    
    def test_filesystem_server_adapter(self):
        """Test that the filesystem server adapter maintains the same API."""
        # Verify that the adapter has the same methods as the original MCP server
        self.assertTrue(hasattr(filesystem_mcp_server, 'read_file'))
        self.assertTrue(hasattr(filesystem_mcp_server, 'write_file'))
        self.assertTrue(hasattr(filesystem_mcp_server, 'list_directory'))
        self.assertTrue(hasattr(filesystem_mcp_server, 'delete_file'))
        self.assertTrue(hasattr(filesystem_mcp_server, 'check_file_exists'))
        
        # Mock the underlying service
        with patch('services.filesystem_service.filesystem_service.read_file') as mock_read:
            mock_read.return_value = {
                "success": True,
                "path": "test.txt",
                "content": "Test content"
            }
            
            # Run the async test
            result = asyncio.run(self._test_filesystem_adapter_async())
            
            # Verify result
            self.assertTrue(result["success"])
            self.assertEqual(result["path"], "test.txt")
            self.assertEqual(result["content"], "Test content")
            
            # Verify the service method was called with the correct arguments
            mock_read.assert_called_once_with("test.txt", "1")
    
    async def _test_filesystem_adapter_async(self):
        """Async implementation of test_filesystem_adapter."""
        return await filesystem_mcp_server.read_file("test.txt", "1")

if __name__ == '__main__':
    unittest.main()
