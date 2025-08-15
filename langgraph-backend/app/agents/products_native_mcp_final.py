"""
Products Agent using native LangChain MCP support with MultiServerMCPClient
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import logging
import os
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

# Import the model manager
from app.config.agent_model_manager import agent_model_manager

# Import context mixin for A2A context handling
from app.agents.base_context_mixin import ContextAwareMixin

class ProductsAgentNativeMCPFinal(ContextAwareMixin):
    """Products agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "products"
        self.description = "Handles product searches, SKU lookups, and product information queries"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")
        self.client = None
        self.tools = None
        self.agent = None
        self.system_prompt = self._get_system_prompt()
        
    async def _ensure_mcp_connected(self):
        """Ensure MCP client and agent are initialized"""
        if not self.agent:
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
                self.tools = await self.client.get_tools()
                
                # Create react agent with tools
                self.agent = create_react_agent(
                    self.model,
                    self.tools,
                    prompt=self.system_prompt
                )
                
                logger.info(f"Connected to Products MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a Products specialist agent with deep expertise in Shopify product management.

You have access to product management tools through the MCP server. Use these tools to search for products, 
get product details, create new products, and manage product status.

Available tools include:
- search_products: Search for products with filters (query, vendor, product_type, status, limit)
- get_product: Get detailed product information by SKU, handle, or ID
- create_product: Create new products with basic information
- update_status: Change product status (ACTIVE, DRAFT, ARCHIVED)
- update_variant_weight: Update product variant weight by SKU

## Your Expertise:
- Product lifecycle management
- SKU and inventory tracking
- Product search and filtering
- Understanding product attributes

## Business Context:
- Products are the core of iDrinkCoffee.com's catalog
- SKUs must be unique across all products
- Product status affects visibility
- Verify product exists before suggesting updates

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
            
            # Use context-aware messages from the mixin
            context_aware_messages = self.build_context_aware_messages(state, self.system_prompt)
            
            # Use the agent to process the request with context
            agent_state = {"messages": context_aware_messages}
            
            # Run the agent
            logger.info(f"🚀 Running Products agent with context-aware prompt")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Products agent completed invoke")
            
            # Extract the response
            if result.get("messages"):
                # Get the last AI message from the agent's response
                agent_messages = result["messages"]
                for msg in reversed(agent_messages):
                    if hasattr(msg, 'content') and msg.content:
                        state["messages"].append(AIMessage(
                            content=msg.content,
                            metadata={"agent": self.name, "intermediate": True}
                        ))
                        break
            else:
                state["messages"].append(AIMessage(
                    content="I processed your request but couldn't generate a response.",
                    metadata={"agent": self.name, "intermediate": True}
                ))
            
            state["last_agent"] = self.name
            logger.info(f"✅ Products agent returning state")
            return state
            
        except Exception as e:
            logger.error(f"Error in ProductsAgentNativeMCPFinal: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in products agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["product", "sku", "find", "search", "item", "listing", 
                   "coffee", "machine", "grinder", "espresso", "breville",
                   "miele", "sanremo", "eureka", "accessories"]
        
        message_content = last_message.content.lower()
        return any(keyword in message_content for keyword in keywords)
    
    async def cleanup(self):
        """Clean up MCP connection"""
        if self.client:
            # MultiServerMCPClient should handle cleanup
            pass