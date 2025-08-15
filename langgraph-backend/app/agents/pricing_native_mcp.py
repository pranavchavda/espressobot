"""
Pricing Agent using native LangChain MCP support with MultiServerMCPClient
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

class PricingAgentNativeMCP(ContextAwareMixin):
    """Pricing agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "pricing"
        self.description = "Handles price updates, discounts, and pricing strategies"
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
                # Initialize MultiServerMCPClient with pricing server
                self.client = MultiServerMCPClient({
                    "pricing": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-pricing-server.py"))],
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
                
                logger.info(f"Connected to Pricing MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a Pricing specialist agent with expertise in Shopify pricing management and MAP compliance.

You have access to pricing management tools through the MCP server. Use these tools to update prices, 
manage bulk pricing operations, update costs, and ensure pricing strategies align with business rules.

Available tools include:
- update_pricing: Update product/variant pricing including price, compare-at price, and cost
- bulk_price_update: Update prices for multiple products from a list
- update_costs: Update product costs by SKU (optimized for bulk cost updates)

## Your Expertise:
- MAP (Minimum Advertised Price) compliance
- Discount and sale management
- Cost tracking and margin analysis
- Bulk pricing operations
- Price optimization strategies

## Business Rules:
- Always preserve original price in compare_at_price before discounting
- To show discount: compare_at_price > price
- To remove discount: Set price = compare_at_price, then clear compare_at_price
- MAP pricing: Use compare_at_price for MSRP, respect MAP agreements
- Never go below MAP without authorization
- All prices should be in USD for iDrinkCoffee

## Best Practices:
- Group variants by product for bulk updates
- Validate all prices before applying
- Report success/failure clearly
- Use string format for prices (e.g., "19.99")
- Include two decimal places

Always provide clear, formatted responses with pricing information and confirm changes made."""
    
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
            logger.info(f"🚀 Running Pricing agent with context-aware prompt with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Pricing agent completed")
            
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
            logger.error(f"Error in PricingAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in pricing agent: {str(e)}",
                metadata={"agent": self.name, "intermediate": True, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["price", "pricing", "cost", "discount", "sale", "map", 
                   "msrp", "margin", "bulk price", "compare", "update price"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)