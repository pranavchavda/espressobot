"""
Simple Products Agent using MCP without LangGraph
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
import logging
import os
from pathlib import Path
import asyncio
import json

logger = logging.getLogger(__name__)

# Import the model manager
from app.config.agent_model_manager import agent_model_manager

class ProductsAgentNativeMCPSimple:
    """Simple products agent using MCP without LangGraph"""
    
    def __init__(self):
        self.name = "products"
        self.description = "Handles product searches, SKU lookups, and product information queries"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")
        self.client = None
        self.tools = {}
        self.system_prompt = self._get_system_prompt()
        
    async def _ensure_mcp_connected(self):
        """Ensure MCP client and tools are initialized"""
        if not self.tools:
            try:
                # Initialize MultiServerMCPClient with products server
                self.client = MultiServerMCPClient({
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
                
                # Get tools from client
                tools = await self.client.get_tools()
                
                # Store tools by name for easy access
                for tool in tools:
                    self.tools[tool.name] = tool
                
                logger.info(f"Connected to Products MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a Products specialist agent with deep expertise in Shopify product management.

You have access to product management tools through the MCP server. Use these tools to search for products, 
get product details, create new products, and manage product status.

When asked to search for products, ALWAYS use the search_products tool immediately.
When asked for product details, use the get_product tool.

## Available Tools:
- search_products: Search for products with filters
- get_product: Get detailed product information
- create_product: Create new products
- update_status: Change product status
- update_variant_weight: Update product weight

Always provide clear, formatted responses with relevant product information."""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state and return updated state"""
        try:
            await self._ensure_mcp_connected()
            
            messages = state.get("messages", [])
            
            if not messages:
                return state
            
            # Get last user message
            last_message = messages[-1]
            if not isinstance(last_message, HumanMessage):
                return state
            
            user_query = last_message.content
            logger.info(f"🚀 Processing query: {user_query[:100]}...")
            
            # Simple tool selection based on keywords
            response = None
            
            if "search" in user_query.lower() or "find" in user_query.lower():
                # Use search_products tool
                if "search_products" in self.tools:
                    logger.info("Using search_products tool...")
                    try:
                        # Extract the actual product name from the query
                        # Look for quoted strings first
                        import re
                        quoted = re.findall(r"'([^']+)'|\"([^\"]+)\"", user_query)
                        if quoted:
                            search_query = quoted[0][0] or quoted[0][1]
                        else:
                            # Simple extraction - remove common task words
                            search_query = user_query
                            for word in ["search for", "find", "search", "the product", "product", "and return", 
                                       "matching items", "including", "variants", "model numbers", "exhaustive",
                                       "catalog", "close", "fuzzy", "partial", "matches", "common"]:
                                search_query = search_query.replace(word, " ")
                            # Clean up extra spaces and get the main term
                            search_query = " ".join(search_query.split()).strip()
                            
                        logger.info(f"Extracted search query: {search_query}")
                        tool = self.tools["search_products"]
                        
                        # Call the tool with proper parameters
                        # MCP tools require a config parameter
                        result = await tool._arun(query=search_query, config={})
                        
                        # Format the response
                        if isinstance(result, str):
                            response = f"Product search results:\n{result}"
                        else:
                            response = f"Product search results:\n{json.dumps(result, indent=2)}"
                        
                        logger.info(f"✅ Search completed, got {len(str(result))} chars")
                        
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        response = f"I encountered an error while searching: {str(e)}"
                else:
                    response = "The search_products tool is not available."
                    
            elif "get" in user_query.lower() and ("product" in user_query.lower() or "sku" in user_query.lower()):
                # Use get_product tool
                if "get_product" in self.tools:
                    logger.info("Using get_product tool...")
                    response = "Please provide a specific SKU or product ID to look up."
                else:
                    response = "The get_product tool is not available."
            else:
                # General query - use model to decide
                prompt = f"{self.system_prompt}\n\nUser query: {user_query}\n\nHow would you respond?"
                model_response = await self.model.ainvoke(prompt)
                response = model_response.content if hasattr(model_response, 'content') else str(model_response)
            
            # Add response to state
            if response:
                state["messages"].append(AIMessage(
                    content=response,
                    metadata={"agent": self.name}
                ))
            else:
                state["messages"].append(AIMessage(
                    content="I couldn't process your request. Please try again.",
                    metadata={"agent": self.name}
                ))
            
            state["last_agent"] = self.name
            logger.info(f"✅ Products agent completed")
            return state
            
        except Exception as e:
            logger.error(f"Error in ProductsAgentNativeMCPSimple: {e}")
            state["messages"].append(AIMessage(
                content=f"I encountered an error: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state