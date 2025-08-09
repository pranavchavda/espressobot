"""
Media Agent using native LangChain MCP support with MultiServerMCPClient
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

class MediaAgentNativeMCP(ContextAwareMixin):
    """Media agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "media"
        self.description = "Manages product images and media assets"
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
                # Initialize MultiServerMCPClient with media server
                self.client = MultiServerMCPClient({
                    "media": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-media-server.py"))],
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
                
                logger.info(f"Connected to Media MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a Media specialist agent with expertise in product image and media management.

You have access to media management tools through the MCP server. Use these tools to manage product images, 
handle uploads, organize media assets, and optimize visual content.

Available tools include:
- add_product_images: Comprehensive image management - add from URLs or local files, list, delete, or reorder

## Your Expertise:
- Product image management
- Image upload and staging
- Media asset organization
- Alt text optimization for SEO
- Image ordering and featured images

## Image Management Actions:
- **add**: Add images from URLs or local files
- **list**: View all current product images
- **delete**: Remove specific images by position
- **reorder**: Change the order of product images
- **clear**: Remove all images

## Business Context:
- First image becomes the featured/main image
- Local files are uploaded to Shopify's staging area
- Images are processed asynchronously by Shopify
- Alt text improves accessibility and SEO
- Product identifier can be SKU, handle, or product ID

## Image Best Practices:
- High-quality product photography
- Multiple angles for complex products
- Lifestyle images for context
- Proper alt text for accessibility
- Consistent image dimensions
- Optimized file sizes

## Upload Process:
1. Local files are staged to Shopify
2. URLs must be publicly accessible
3. Processing may take a few seconds
4. Changes appear in storefront after processing

Always provide clear, formatted responses with image information and confirm changes made."""
    
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
            logger.info(f"🚀 Running Media agent with context-aware prompt with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Media agent completed")
            
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
            logger.error(f"Error in MediaAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in media agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["image", "images", "photo", "picture", "media", "upload", 
                   "gallery", "thumbnail", "alt text", "product image", "visual",
                   "reorder images", "delete image", "add image"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)