"""
Integrations Agent using native LangChain MCP support with MultiServerMCPClient
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

class IntegrationsAgentNativeMCP:
    """Integrations agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "integrations"
        self.description = "Manages external integrations like SkuVault and Yotpo"
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
                # Initialize MultiServerMCPClient with integrations server
                self.client = MultiServerMCPClient({
                    "integrations": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-integrations-server.py"))],
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
                
                logger.info(f"Connected to Integrations MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are an Integrations specialist agent with expertise in external system connectivity.

You have access to integration tools through the MCP server. Use these tools to manage SkuVault inventory, 
Yotpo reviews, and other third-party system integrations.

Available tools include:
- upload_to_skuvault: Upload products from Shopify to SkuVault inventory management
- manage_skuvault_kits: Create, update, and manage product kits in SkuVault
- send_review_request: Send Yotpo review request emails to customers

## Your Expertise:
- SkuVault inventory synchronization
- Kit and bundle management
- Yotpo review campaigns
- API integration troubleshooting
- Data mapping between systems

## SkuVault Integration:
- Upload product data from Shopify
- Map SKU, title, vendor, price, cost, images
- Create and manage kits/bundles
- Kit format: "SKU1:QTY1,SKU2:QTY2"
- Kit SKUs use COMBO- or BUNDLE- prefix
- Dry run preview before upload

## SkuVault Kit Management:
- Actions: create, update, remove, get, list
- Components must exist in SkuVault
- Kit lines use Combine=3 for tracking
- Examples:
  - Machine + grinder combos
  - Coffee starter bundles
  - Seasonal packages

## Yotpo Review Integration:
- Send review request emails
- Product-specific review requests
- Spam filter (max 5 emails per 30 days)
- Best timing: 7-14 days after delivery
- Requires Yotpo Product ID (numeric)

## Integration Best Practices:
- Always use dry_run for testing
- Verify data mapping before sync
- Check API credentials in environment
- Monitor sync success/failure
- Document integration issues

Always provide clear, formatted responses with integration status and confirm successful operations."""
    
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
            logger.info(f"🚀 Running Integrations agent with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Integrations agent completed")
            
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
            logger.error(f"Error in IntegrationsAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in integrations agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["skuvault", "yotpo", "review", "reviews", "integration", 
                   "sync", "upload", "kit", "kits", "bundle", "combo",
                   "review request", "inventory sync", "external system"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)