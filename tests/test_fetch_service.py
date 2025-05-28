"""
Unit tests for the optimized fetch service implementation.
"""
import os
import sys
import json
import unittest
import asyncio
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.fetch_service import FetchService, FetchServiceError

class TestFetchService(unittest.TestCase):
    """Test cases for the FetchService class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test instance
        self.fetch_service = FetchService()
    
    def test_fetch_url(self):
        """Test fetching a URL."""
        # Mock httpx.AsyncClient
        with patch('httpx.AsyncClient') as mock_client:
            # Set up the mock response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html><body>Test content</body></html>"
            mock_response.headers = {"content-type": "text/html"}
            mock_response.url = "https://example.com"
            mock_response.raise_for_status = MagicMock()
            
            # Set up the mock client
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value = mock_client_instance
            
            # Run the async test
            result = asyncio.run(self._test_fetch_url_async())
            
            # Verify result
            self.assertTrue(result["success"])
            self.assertEqual(result["url"], "https://example.com")
            self.assertEqual(result["status"], 200)
            self.assertEqual(result["content"], "<html><body>Test content</body></html>")
            self.assertEqual(result["content_type"], "text/html")
    
    async def _test_fetch_url_async(self):
        """Async implementation of test_fetch_url."""
        return await self.fetch_service.fetch_url("https://example.com")
    
    def test_fetch_and_extract_text(self):
        """Test fetching and extracting text from a URL."""
        # Mock fetch_url method
        with patch.object(self.fetch_service, 'fetch_url') as mock_fetch_url:
            # Set up the mock response
            mock_fetch_url.return_value = {
                "success": True,
                "url": "https://example.com",
                "status": 200,
                "content": "<html><body><div class='content'>Test content</div></body></html>",
                "content_type": "text/html"
            }
            
            # Run the async test
            result = asyncio.run(self._test_fetch_and_extract_text_async())
            
            # Verify result
            self.assertTrue(result["success"])
            self.assertEqual(result["url"], "https://example.com")
            self.assertIn("Test content", result["text"])
            self.assertEqual(result["selector_used"], ".content")
    
    async def _test_fetch_and_extract_text_async(self):
        """Async implementation of test_fetch_and_extract_text."""
        return await self.fetch_service.fetch_and_extract_text("https://example.com", ".content")
    
    def test_fetch_json(self):
        """Test fetching and parsing JSON from a URL."""
        # Mock fetch_url method
        with patch.object(self.fetch_service, 'fetch_url') as mock_fetch_url:
            # Set up the mock response
            mock_fetch_url.return_value = {
                "success": True,
                "url": "https://example.com/api.json",
                "status": 200,
                "content": '{"key": "value", "array": [1, 2, 3]}',
                "content_type": "application/json"
            }
            
            # Run the async test
            result = asyncio.run(self._test_fetch_json_async())
            
            # Verify result
            self.assertTrue(result["success"])
            self.assertEqual(result["url"], "https://example.com/api.json")
            self.assertEqual(result["data"]["key"], "value")
            self.assertEqual(result["data"]["array"], [1, 2, 3])
    
    async def _test_fetch_json_async(self):
        """Async implementation of test_fetch_json."""
        return await self.fetch_service.fetch_json("https://example.com/api.json")
    
    def test_fetch_url_error(self):
        """Test error handling when fetching a URL."""
        # Mock httpx.AsyncClient to raise an exception
        with patch('httpx.AsyncClient') as mock_client:
            # Set up the mock client to raise an exception
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.side_effect = Exception("Connection error")
            mock_client.return_value = mock_client_instance
            
            # Run the async test
            with self.assertRaises(FetchServiceError):
                asyncio.run(self._test_fetch_url_error_async())
    
    async def _test_fetch_url_error_async(self):
        """Async implementation of test_fetch_url_error."""
        return await self.fetch_service.fetch_url("https://example.com")
    
    def test_fetch_json_invalid(self):
        """Test handling invalid JSON."""
        # Mock fetch_url method
        with patch.object(self.fetch_service, 'fetch_url') as mock_fetch_url:
            # Set up the mock response with invalid JSON
            mock_fetch_url.return_value = {
                "success": True,
                "url": "https://example.com/api.json",
                "status": 200,
                "content": 'This is not valid JSON',
                "content_type": "application/json"
            }
            
            # Run the async test
            result = asyncio.run(self._test_fetch_json_invalid_async())
            
            # Verify result
            self.assertFalse(result["success"])
            self.assertIn("not valid JSON", result["error"])
    
    async def _test_fetch_json_invalid_async(self):
        """Async implementation of test_fetch_json_invalid."""
        return await self.fetch_service.fetch_json("https://example.com/api.json")

if __name__ == '__main__':
    unittest.main()
