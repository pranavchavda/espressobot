"""
Sales Agent using native LangChain MCP support with MultiServerMCPClient
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import logging
import os
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class SalesAgentNativeMCP:
    """Sales agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "sales"
        self.description = "Manages sales campaigns, MAP pricing, and promotions"
        self.model = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0.0,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.client = None
        self.tools = None
        self.agent = None
        self.system_prompt = self._get_system_prompt()
        
    async def _ensure_mcp_connected(self):
        """Ensure MCP client and agent are initialized"""
        if not self.agent:
            try:
                # Initialize MultiServerMCPClient with sales server
                self.client = MultiServerMCPClient({
                    "sales": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-sales-server.py"))],
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
                    state_modifier=self.system_prompt
                )
                
                logger.info(f"Connected to Sales MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a Sales specialist agent with expertise in MAP compliance and promotional campaigns.

You have access to sales management tools through the MCP server. Use these tools to manage MAP sales, 
apply promotional pricing, and coordinate sales campaigns.

Available tools include:
- manage_miele_sales: Manage Miele MAP (Minimum Advertised Price) sales
- manage_map_sales: Apply or revert Breville MAP sales
- analytics_daily_sales: Get today's or recent daily sales summary
- analytics_order_summary: Get order analytics including revenue and product performance
- analytics_revenue_report: Generate detailed revenue reports with breakdowns

## Your Expertise:
- MAP (Minimum Advertised Price) compliance for Miele and Breville
- Sales campaign management and scheduling
- Revenue analytics and reporting
- Promotional pricing strategies
- Sales performance tracking

## Business Context:
- MAP sales must follow manufacturer-approved pricing windows
- Miele products: CM5310, CM6160, CM6360, CM7750
- Breville has enhanced 2025 sales calendar
- Sales typically run 7-14 days
- Compare-at price shows original MSRP during sales
- Tags track sales (miele-sale, sale-YYYY-MM)

## MAP Sale Process:
1. Check current/upcoming sales windows
2. Apply sale prices with proper tags
3. Set compare-at price to show discount
4. Monitor sales performance
5. Revert prices after sale ends

## Analytics Focus:
- Daily sales monitoring
- Product performance during promotions
- Revenue impact of sales campaigns
- Customer response to MAP pricing

Always provide clear, formatted responses with sales information and confirm changes made."""
    
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
            
            # Use the agent to process the request with full conversation history
            agent_state = {"messages": messages}
            
            # Run the agent
            logger.info(f"🚀 Running Sales agent with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Sales agent completed")
            
            # Extract the response
            if result.get("messages"):
                # Get the last AI message from the agent's response
                agent_messages = result["messages"]
                for msg in reversed(agent_messages):
                    if hasattr(msg, 'content') and msg.content:
                        state["messages"].append(AIMessage(
                            content=msg.content,
                            metadata={"agent": self.name}
                        ))
                        break
            else:
                state["messages"].append(AIMessage(
                    content="I processed your request but couldn't generate a response.",
                    metadata={"agent": self.name}
                ))
            
            state["last_agent"] = self.name
            return state
            
        except Exception as e:
            logger.error(f"Error in SalesAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in sales agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["sale", "sales", "map", "miele", "breville", "promotion", 
                   "campaign", "revenue", "analytics", "daily sales", "order summary",
                   "discount campaign", "map pricing", "sales report"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)