"""
Features Agent using native LangChain MCP support with MultiServerMCPClient
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

class FeaturesAgentNativeMCP(ContextAwareMixin):
    """Features agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "features"
        self.description = "Manages product features, specifications, and metafields"
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
                # Initialize MultiServerMCPClient with features server
                self.client = MultiServerMCPClient({
                    "features": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-features-server.py"))],
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
                
                logger.info(f"Connected to Features MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a Features specialist agent with expertise in product content management and metafields.

You have access to feature management tools through the MCP server. Use these tools to manage product features, 
specifications, metafields, and rich content.

Available tools include:
- manage_features_metaobjects: Manage product features using Shopify metaobjects
- update_metafields: Atomically set one or more metafields on products

## Your Expertise:
- Product feature management with metaobjects
- Metafield configuration and updates
- Technical specifications management
- Rich content formatting
- SEO-optimized product descriptions

## Metafield Structure:
- Features stored as metaobject references
- Common namespaces: faq, specs, content, new
- Supports JSON and single_line_text_field types
- Features can include text and images

## Feature Box Management:
- Title: **Bold title** format
- Description: Supporting text
- Image: Optional product feature image
- Status: ACTIVE (published) or DRAFT (hidden)
- Actions: list, add, update, remove, reorder, clear

## Common Metafields:
- content.features_box: Product feature metaobjects
- specs.techjson: Technical specifications JSON
- faq.content: Frequently asked questions
- new.varLinks: Variant linking references

## Best Practices:
- Use metaobjects for rich, editable content
- Keep features concise and benefit-focused
- Include images for visual features
- Set proper status (ACTIVE/DRAFT)
- Maintain consistent formatting

Always provide clear, formatted responses with feature information and confirm changes made."""
    
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
            logger.info(f"🚀 Running Features agent with context-aware prompt with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Features agent completed")
            
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
            logger.error(f"Error in FeaturesAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in features agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["feature", "features", "specification", "spec", "specs", 
                   "metafield", "metaobject", "faq", "technical", "description",
                   "content", "features box", "product detail"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)