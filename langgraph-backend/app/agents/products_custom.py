"""
Products Agent using custom agent mechanism (no LangGraph)
"""
from typing import List, Dict, Any
from langchain_core.tools import BaseTool
from pathlib import Path
import logging
import os

from .base_agent import BaseAgent
from app.config.agent_model_manager import agent_model_manager

logger = logging.getLogger(__name__)

# Import MCP tools
from langchain_mcp_adapters.client import MultiServerMCPClient

class ProductsAgentCustom(BaseAgent):
    """Products agent using custom agent mechanism without LangGraph"""
    
    def __init__(self):
        super().__init__()
        self.name = "products"
        self.description = "Handles product searches, SKU lookups, and product information queries"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        
        # Initialize MCP client
        self.mcp_client = None
        self._initialize_mcp()
        self._initialize_tools()
        
        logger.info(f"{self.name} agent initialized with custom mechanism")
    
    def _initialize_mcp(self):
        """Initialize MCP client for tools"""
        try:
            self.mcp_client = MultiServerMCPClient({
                "products": {
                    "command": "python3",
                    "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-products-server.py"))],
                    "transport": "stdio",
                    "env": {
                        **os.environ,
                        "PYTHONPATH": "/home/pranav/espressobot/frontend/python-tools"
                    }
                }
            })
            logger.info("MCP client initialized for products")
        except Exception as e:
            logger.error(f"Failed to initialize MCP client: {e}")
    
    async def _get_tools_async(self) -> List[BaseTool]:
        """Get tools from MCP server asynchronously"""
        if self.mcp_client:
            try:
                tools = await self.mcp_client.get_tools()
                logger.info(f"Retrieved {len(tools)} tools from MCP server")
                return tools
            except Exception as e:
                logger.error(f"Failed to get tools from MCP: {e}")
        return []
    
    def _get_tools(self) -> List[BaseTool]:
        """Get tools synchronously (required by base class)"""
        # This will be populated by _initialize_tools
        return []
    
    def _initialize_tools(self):
        """Initialize tools asynchronously"""
        # We'll need to handle this differently since it's async
        # For now, we'll defer tool loading
        logger.info("Tool initialization deferred to first call")
    
    async def _ensure_tools_loaded(self):
        """Ensure tools are loaded from MCP"""
        if not self.tools:
            tools = await self._get_tools_async()
            # MCP tools might be BaseTool objects or need conversion
            self.tools = {}
            for tool in tools:
                if hasattr(tool, 'name'):
                    self.tools[tool.name] = tool
                elif isinstance(tool, dict) and 'name' in tool:
                    # Handle dict-based tools from MCP
                    self.tools[tool['name']] = tool
            logger.info(f"Loaded {len(self.tools)} tools from MCP")
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the products agent"""
        return """You are a Products specialist agent with expertise in product searches, inventory management, and product information.

You have access to powerful product search and management tools through the MCP server.

## Your Expertise:
- Product searches by title, SKU, vendor, or type
- Inventory and stock level queries
- Product details and specifications
- Price and variant information
- Product comparisons and recommendations
- Handling complex product queries

## Key Capabilities:
- **Search Products**: Find products using various filters and criteria
- **Get Product Details**: Retrieve complete product information including variants
- **Check Inventory**: Verify stock levels and availability
- **Product Recommendations**: Suggest products based on criteria

## Business Context:
- You're supporting iDrinkCoffee.com, a premium coffee equipment retailer
- Products include espresso machines, grinders, accessories, and coffee
- Focus on providing accurate, helpful product information
- Consider inventory levels when making recommendations

## Response Guidelines:
- Provide clear, structured product information
- Include relevant details like price, SKU, and availability
- When multiple products match, present them in a organized format
- Proactively offer related products or alternatives when appropriate
- Always execute searches immediately with sensible defaults rather than asking for parameters

IMPORTANT: When asked to search or find products, DO IT immediately. Don't ask for clarification unless absolutely necessary."""
    
    async def think_and_act(self, message: str, state: Dict[str, Any]) -> Any:
        """Override think_and_act to ensure tools are loaded"""
        await self._ensure_tools_loaded()
        
        # Check if this is a follow-up question
        if self.conversation_state.get("last_search"):
            # Add context about previous search
            message = f"Previous search: {self.conversation_state['last_search']}\n\nCurrent request: {message}"
        
        response = await super().think_and_act(message, state)
        
        # Track what we searched for
        if "search" in message.lower() or "find" in message.lower():
            self.conversation_state["last_search"] = message[:100]
        
        return response