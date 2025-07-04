"""
Base class for MCP tools
"""

import os
import sys
import json
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

# Add parent directory to path to import existing tools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import ShopifyClient from parent base module
from base import ShopifyClient

class BaseMCPTool(ABC):
    """Base class for all MCP tools"""
    
    # Tool metadata
    name: str = ""
    description: str = ""
    context: str = ""  # Tool-specific context/instructions
    input_schema: Dict[str, Any] = {}
    
    def __init__(self):
        if not self.name:
            raise ValueError("Tool must have a name")
            
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given arguments"""
        raise NotImplementedError("Subclasses must implement execute()")
        
    async def test(self) -> Dict[str, Any]:
        """Test the tool functionality"""
        # Default test - subclasses should override
        return {"status": "not_implemented"}
        
    def validate_env(self) -> bool:
        """Validate required environment variables"""
        required_vars = ['SHOPIFY_SHOP_URL', 'SHOPIFY_ACCESS_TOKEN']
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
            
        return True