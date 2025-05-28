"""
Fetch service implementation for web content retrieval.
Replaces the FetchMCPServer with a direct implementation.
"""
import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
import logging
import httpx
from bs4 import BeautifulSoup

from services.base_service import BaseService, ServiceError
from services.config import service_config

class FetchServiceError(ServiceError):
    """Exception raised for fetch service errors."""
    pass

class FetchService(BaseService):
    """
    Direct implementation of fetch service functionality.
    Provides web content retrieval without MCP overhead.
    """
    def __init__(self):
        """Initialize the fetch service."""
        super().__init__("fetch")
        
        # Default headers
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Default timeout in seconds
        self.default_timeout = service_config.get("fetch", "timeout", 30)
    
    async def fetch_url(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch raw content from a URL with metadata.
        
        Args:
            url: URL to fetch
            options: Optional fetch options (headers, timeout, etc.)
            
        Returns:
            Response content and metadata
        """
        try:
            # Prepare request options
            options = options or {}
            headers = {**self.default_headers, **(options.get("headers", {}))}
            timeout = options.get("timeout", self.default_timeout)
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    headers=headers,
                    timeout=timeout,
                    follow_redirects=True
                )
                
                # Raise for HTTP errors
                response.raise_for_status()
                
                return {
                    "success": True,
                    "url": str(response.url),
                    "status": response.status_code,
                    "headers": dict(response.headers),
                    "content": response.text,
                    "content_type": response.headers.get("content-type", "")
                }
        except Exception as e:
            raise FetchServiceError(f"Failed to fetch URL {url}: {str(e)}")
    
    async def fetch_and_extract_text(self, url: str, selector: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch a webpage and extract text content, with optional CSS selector filtering.
        
        Args:
            url: URL to fetch
            selector: Optional CSS selector to filter content
            
        Returns:
            Extracted text content and metadata
        """
        try:
            # Fetch raw content
            result = await self.fetch_url(url)
            
            # Parse HTML
            soup = BeautifulSoup(result["content"], "html.parser")
            
            # Remove script and style elements
            for script_or_style in soup(["script", "style"]):
                script_or_style.decompose()
            
            # Extract text based on selector
            if selector:
                elements = soup.select(selector)
                if not elements:
                    return {
                        "success": False,
                        "error": f"No elements found matching selector '{selector}'"
                    }
                
                # Extract text from selected elements
                text = "\n\n".join([elem.get_text(strip=True) for elem in elements])
            else:
                # Extract all text
                text = soup.get_text(separator="\n\n", strip=True)
            
            return {
                "success": True,
                "url": result["url"],
                "text": text,
                "title": soup.title.string if soup.title else "",
                "selector_used": selector
            }
        except Exception as e:
            raise FetchServiceError(f"Failed to extract text from {url}: {str(e)}")
    
    async def fetch_json(self, url: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch and parse JSON from a URL.
        
        Args:
            url: URL to fetch
            options: Optional fetch options (headers, timeout, etc.)
            
        Returns:
            Parsed JSON data and metadata
        """
        try:
            # Prepare request options
            options = options or {}
            headers = {
                **self.default_headers,
                "Accept": "application/json",
                **(options.get("headers", {}))
            }
            
            # Update options with JSON-specific headers
            json_options = {**options, "headers": headers}
            
            # Fetch raw content
            result = await self.fetch_url(url, json_options)
            
            # Parse JSON
            try:
                json_data = json.loads(result["content"])
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Response is not valid JSON"
                }
            
            return {
                "success": True,
                "url": result["url"],
                "data": json_data
            }
        except Exception as e:
            raise FetchServiceError(f"Failed to fetch JSON from {url}: {str(e)}")

# Create a singleton instance
fetch_service = FetchService()
