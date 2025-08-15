"""
Inventory Agent using native LangChain MCP support with MultiServerMCPClient
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

class InventoryAgentNativeMCP(ContextAwareMixin):
    """Inventory agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "inventory"
        self.description = "Manages inventory levels and stock tracking"
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
                # Initialize MultiServerMCPClient with inventory server
                self.client = MultiServerMCPClient({
                    "inventory": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-inventory-server.py"))],
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
                
                logger.info(f"Connected to Inventory MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are an Inventory specialist agent with expertise in stock management and inventory policies.

You have access to inventory management tools through the MCP server. Use these tools to manage inventory policies, 
track stock levels, handle tags, and manage redirects.

Available tools include:
- manage_inventory_policy: Set inventory policy to control whether products can be oversold
- manage_tags: Add, remove, or replace tags on products
- manage_redirects: Create, list, or delete URL redirects in the Shopify store

## Your Expertise:
- Inventory policy management (DENY vs ALLOW overselling)
- Stock level tracking and monitoring
- Product tagging for organization
- URL redirect management for SEO

## Business Context:
- DENY policy prevents overselling (default for physical inventory)
- ALLOW policy enables overselling (for pre-orders, made-to-order)
- Tags affect search, filtering, and automation
- Redirects maintain SEO when URLs change

## Best Practices:
- Check current inventory before changing policies
- Use consistent tag naming conventions
- Maintain redirects for discontinued products
- Document reasons for policy changes

Always provide clear, formatted responses with inventory information and confirm changes made."""
    
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
            logger.info(f"🚀 Running Inventory agent with context-aware prompt with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Inventory agent completed")
            
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
            return state
            
        except Exception as e:
            logger.error(f"Error in InventoryAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in inventory agent: {str(e)}",
                metadata={"agent": self.name, "intermediate": True, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["inventory", "stock", "oversell", "policy", "tag", "tags", 
                   "redirect", "url", "out of stock", "availability", "quantity"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)