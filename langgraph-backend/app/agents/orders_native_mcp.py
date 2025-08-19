"""
Orders Agent using native LangChain MCP support with MultiServerMCPClient
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

class OrdersAgentNativeMCP(ContextAwareMixin):
    """Orders agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "orders"
        self.description = "Handles order analytics and reporting"
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
                # Initialize MultiServerMCPClient with orders server
                self.client = MultiServerMCPClient({
                    "orders": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-orders-server.py"))],
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
                
                logger.info(f"Connected to Orders MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are an Orders specialist agent with expertise in order analytics and reporting.

You have access to order analytics tools through the MCP server. Use these tools to analyze orders, 
generate reports, and provide insights into sales performance.

Available tools include:
- analytics_order_summary: Get order analytics including count, revenue, and product performance
- analytics_daily_sales: Get today's or recent daily sales summary
- analytics_revenue_report: Generate detailed revenue reports with breakdowns

## Your Expertise:
- Order analytics and reporting
- Sales performance tracking
- Revenue analysis and trends
- Product performance metrics
- Customer behavior insights

## Analytics Capabilities:
- **Order Summary**: Count, revenue, AOV, top products
- **Daily Sales**: Hourly breakdown, velocity tracking
- **Revenue Reports**: Period comparisons, channel attribution
- **Performance Metrics**: Conversion rates, basket analysis

## Report Types:
- Daily performance summaries
- Weekly/monthly comparisons
- Product performance rankings
- Channel revenue attribution
- Customer segment analysis

## iDrinkCoffee Context:
- High-volume store (100-200+ orders daily)
- Multiple sales channels (POS vs Online)
- Focus on coffee equipment and supplies
- MAP pricing considerations
- Seasonal sales patterns

## Best Practices:
- Handle large datasets efficiently
- Provide actionable insights
- Compare periods for trends
- Include product breakdowns
- Track discount impact

## Date Handling:
- Support "today", "yesterday" keywords
- Handle date ranges properly
- Consider timezone (store timezone)
- Include comparison periods

Always provide clear, formatted reports with actionable insights and performance metrics."""
    
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
            logger.info(f"🚀 Running Orders agent with context-aware prompt with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Orders agent completed")
            
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
            logger.error(f"Error in OrdersAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in orders agent: {str(e)}",
                metadata={"agent": self.name, "intermediate": True, "error": True}
            ))
            return state
    
    async def process_async(self, message: str) -> Dict[str, Any]:
        """
        Process a message asynchronously for the async orchestrator
        """
        try:
            # Create a state dict with the message
            state = {
                "messages": [HumanMessage(content=message)]
            }
            
            # Call the agent
            result_state = await self(state)
            
            # Extract the response from the last AI message
            messages = result_state.get("messages", [])
            response_content = ""
            
            # Find the last AI message
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    response_content = msg.content
                    break
            
            return {
                "content": response_content,
                "agent": self.name,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in OrdersAgentNativeMCP.process_async: {e}")
            return {
                "content": f"Error in {self.name} agent: {str(e)}",
                "agent": self.name,
                "success": False,
                "error": str(e)
            }
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["order", "orders", "analytics", "report", "revenue", 
                   "sales performance", "daily sales", "aov", "average order",
                   "top products", "bestseller", "sales summary"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)