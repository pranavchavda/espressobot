"""
Base service class for all direct service implementations.
Provides common functionality and error handling for all services.
"""
from typing import Any, Dict, Optional, Union, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ServiceError(Exception):
    """Base exception class for service errors."""
    pass

class BaseService:
    """
    Base class for all direct service implementations.
    Provides common functionality and standardized error handling.
    """
    def __init__(self, name: str):
        """
        Initialize the base service.
        
        Args:
            name: Service name for logging and identification
        """
        self.name = name
        self.logger = logging.getLogger(f"service.{name}")
    
    def format_response(self, data: Any, is_error: bool = False) -> Dict[str, Any]:
        """
        Format a response in a standardized way compatible with MCP format.
        
        Args:
            data: Response data
            is_error: Whether this is an error response
            
        Returns:
            Formatted response dictionary
        """
        if is_error:
            return {
                "content": [{"type": "text", "text": str(data)}],
                "isError": True
            }
        
        # If already in the expected format, return as-is
        if isinstance(data, dict) and "content" in data:
            return data
            
        # Format as text content
        return {
            "content": [{"type": "text", "text": str(data)}],
            "isError": False
        }
    
    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """
        Handle an exception and return a standardized error response.
        
        Args:
            error: Exception to handle
            
        Returns:
            Formatted error response
        """
        error_message = f"{self.name} service error: {str(error)}"
        self.logger.error(error_message)
        return self.format_response(error_message, is_error=True)
    
    async def execute(self, func, *args, **kwargs) -> Dict[str, Any]:
        """
        Execute a function with standardized error handling.
        
        Args:
            func: Function to execute
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Formatted response
        """
        try:
            result = await func(*args, **kwargs)
            return self.format_response(result)
        except Exception as e:
            return self.handle_error(e)
