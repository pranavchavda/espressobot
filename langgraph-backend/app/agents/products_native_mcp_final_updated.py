"""
Products Agent using native LangChain MCP support with MultiServerMCPClient
Updated to use dynamic model configuration
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import logging
import os
from pathlib import Path
import asyncio

# Import the model manager
from app.config.agent_model_manager import agent_model_manager

logger = logging.getLogger(__name__)

class ProductsAgentNativeMCPFinal:
    """Products agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "products"
        self.description = "Handles product searches, SKU lookups, and product information queries"
        
        # Use dynamic model configuration
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"Products agent initialized with model: {type(self.model).__name__}")
        
        self.client = None
        self.tools = None
        self.agent = None
        self.system_prompt = self._get_system_prompt()
    
    def refresh_model(self):
        """Refresh the model configuration (call this when config changes)"""
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"Products agent model refreshed: {type(self.model).__name__}")
        # Reset agent to use new model
        self.agent = None
        
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
                
                if not self.tools:
                    logger.warning("No tools available from MCP server")
                    self.tools = []
                else:
                    logger.info(f"Products agent initialized with {len(self.tools)} tools")
                
                # Create agent with the current model
                self.agent = create_react_agent(
                    self.model,
                    self.tools,
                    messages_modifier=self.system_prompt,
                    max_iterations=5
                )
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self):
        """Get the system prompt for the products agent"""
        return """You are a products specialist agent for iDrinkCoffee.com's EspressoBot.

Your responsibilities:
- Search for products by name, SKU, or attributes
- Provide detailed product information
- Handle product lookups and queries
- Work with collections and product organization

Available tools provide access to Shopify product data.

Be concise and accurate in your responses."""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process a products-related request"""
        try:
            # Ensure MCP is connected
            await self._ensure_mcp_connected()
            
            messages = state.get("messages", [])
            if not messages:
                state["messages"] = [AIMessage(
                    content="No messages provided",
                    metadata={"agent": self.name, "error": "No input"}
                )]
                return state
            
            # Get the last human message
            last_message = messages[-1]
            user_input = last_message.content if hasattr(last_message, 'content') else str(last_message)
            
            logger.info(f"Products agent processing: {user_input[:100]}...")
            
            # Prepare input for agent
            agent_input = {
                "messages": [HumanMessage(content=user_input)]
            }
            
            # Run the agent
            try:
                result = await asyncio.wait_for(
                    self.agent.ainvoke(agent_input),
                    timeout=30.0
                )
                
                # Extract the response
                if "messages" in result and result["messages"]:
                    final_message = result["messages"][-1]
                    response_content = final_message.content if hasattr(final_message, 'content') else str(final_message)
                else:
                    response_content = "I completed the product operation successfully."
                
                # Add response to state
                state["messages"].append(AIMessage(
                    content=response_content,
                    metadata={"agent": self.name}
                ))
                
            except asyncio.TimeoutError:
                logger.error("Products agent timed out")
                state["messages"].append(AIMessage(
                    content="The product search timed out. Please try again with a more specific query.",
                    metadata={"agent": self.name, "error": "timeout"}
                ))
            except Exception as e:
                logger.error(f"Error in products agent: {e}")
                state["messages"].append(AIMessage(
                    content=f"I encountered an error while searching for products: {str(e)}",
                    metadata={"agent": self.name, "error": str(e)}
                ))
            
            return state
            
        except Exception as e:
            logger.error(f"Error in products agent: {e}")
            state["messages"] = state.get("messages", []) + [
                AIMessage(
                    content=f"Error in products agent: {str(e)}",
                    metadata={"agent": self.name, "error": str(e)}
                )
            ]
            return state
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except:
                pass