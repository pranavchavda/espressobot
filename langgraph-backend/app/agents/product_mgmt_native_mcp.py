"""
Product Management Agent using native LangChain MCP support with MultiServerMCPClient
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

class ProductManagementAgentNativeMCP(ContextAwareMixin):
    """Product Management agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "product_management"
        self.description = "Creates and manages product listings, variants, and combos"
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
                # Initialize MultiServerMCPClient with product management server
                self.client = MultiServerMCPClient({
                    "product_management": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-product-management-server.py"))],
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
                
                logger.info(f"Connected to Product Management MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a Product Management specialist agent with expertise in creating and managing product listings.

You have access to product management tools through the MCP server. Use these tools to create products, 
manage variants, handle open box listings, and create combo products.

Available tools include:
- create_product: Create a new product with basic information
- create_full_product: Create a fully-configured product with metafields and tags
- update_full_product: Comprehensively update an existing product
- add_variants_to_product: Add multiple variants to an existing product
- create_open_box: Create an open box version of an existing product
- create_combo: Create combo products by combining two products
- duplicate_listing: Duplicate an existing product with modifications
- update_status: Change product status between active, draft, and archived
- update_variant_weight: Update the weight of a specific product variant
- manage_variant_links: Link related product variants (colors/styles)

## Your Expertise:
- Product creation and configuration
- Variant management and options
- Open box and combo product creation
- Product duplication and templates
- Status and visibility management
- Variant linking for related products

## Product Creation Best Practices:
- Start with create_full_product for complete setup
- Use proper product types and vendors
- Configure metafields for rich content
- Set appropriate tags for organization
- Products start as DRAFT by default

## Open Box Conventions:
- SKU Format: OB-{YYMM}-{Serial}-{OriginalSKU}
- Title Format: {Original Title} |{Serial}| - {Condition}
- Default 10% discount if not specified
- Inventory quantity set to 1, policy DENY
- Condition types: 14-day-return, 45-day-return, used-trade-in, etc.

## Combo Product Creation:
- Combines two products with special pricing
- Auto-generates combo images
- SKU Format: {prefix}-{serial}-{suffix}
- Typically 10-20% discount
- Tagged with 'combo' and monthly tag

## Variant Management:
- Add variants with different options (Size, Color, etc.)
- Each variant needs unique SKU
- Set individual prices and inventory
- Link related variants for navigation

## Status Management:
- ACTIVE: Visible and purchasable
- DRAFT: Hidden for preparation
- ARCHIVED: Preserved for records

Always provide clear, formatted responses with product information and confirm changes made."""
    
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
            logger.info(f"🚀 Running Product Management agent with context-aware prompt with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Product Management agent completed")
            
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
            logger.error(f"Error in ProductManagementAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in product management agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["create product", "new product", "add product", "variant", "variants",
                   "open box", "combo", "duplicate", "copy product", "product status",
                   "archive product", "draft product", "variant link", "product weight",
                   "create listing", "new listing", "product template"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)