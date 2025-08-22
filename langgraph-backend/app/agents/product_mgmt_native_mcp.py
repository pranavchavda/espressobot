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
        self.name = "product_mgmt"
        self.description = "Creates and manages product listings, variants, and combos"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")

        self.client = None
        self.tools = {}  # Dictionary like products agent
        self.system_prompt = self._get_system_prompt()
        
    async def _ensure_mcp_connected(self):
        """Ensure MCP client and tools are initialized"""
        if not self.tools:
            try:
                # Initialize MultiServerMCPClient with product management server
                self.client = MultiServerMCPClient({
                    "product_management": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-product-management-server.py"))],
                        "transport": "stdio",
                        "env": {
                            **os.environ,
                            "PYTHONPATH": "/home/pranav/espressobot/frontend/python-tools",
                            "SHOPIFY_SHOP_URL": os.environ.get("SHOPIFY_SHOP_URL", ""),
                            "SHOPIFY_ACCESS_TOKEN": os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
                        }
                    }
                })
                
                # Get tools from client
                tools = await self.client.get_tools()
                
                # Store tools by name for easy access (like products agent)
                for tool in tools:
                    self.tools[tool.name] = tool
                
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
            
            user_query = last_message.content
            logger.info(f"🚀 Processing product management query: {user_query[:100]}...")
            
            # Simple tool selection based on keywords (like products_native_mcp_simple.py)
            response = None
            
            if "create" in user_query.lower() and ("product" in user_query.lower() or "new" in user_query.lower()):
                # Use create_full_product tool
                if "create_full_product" in self.tools:
                    logger.info("Using create_full_product tool...")
                    try:
                        # Get structured data from orchestrator context (preferred)
                        orchestrator_context = state.get("orchestrator_context", {})
                        previous_results = state.get("previous_results", {})
                        
                        # Try to get structured data from orchestrator first
                        title = orchestrator_context.get("title") or previous_results.get("title")
                        vendor = orchestrator_context.get("vendor") or previous_results.get("vendor")
                        product_type = orchestrator_context.get("product_type") or previous_results.get("product_type")
                        price = orchestrator_context.get("price") or previous_results.get("price")
                        sku = orchestrator_context.get("sku") or previous_results.get("sku")
                        
                        # Use LLM intelligence to extract parameters if not provided by orchestrator
                        if not all([title, vendor, product_type, price]):
                            extraction_prompt = f"""You are a product data extraction specialist. Extract the following information from this product creation request:

Task: {user_query}

Extract and return ONLY the following information in this exact JSON format:
{{
    "title": "exact product title/name",
    "vendor": "brand/manufacturer name", 
    "product_type": "category like 'Espresso Machines', 'Grinders', 'Fresh Coffee', etc.",
    "price": "price as decimal string like '699.99'",
    "sku": "product SKU if mentioned, or generate logical SKU based on product"
}}

Rules:
- If price not specified, use "0.00"
- If vendor not clear, extract from context or use "Unknown Vendor"
- Make SKU uppercase with hyphens if generating
- Be precise and concise"""

                            logger.info("Using LLM to extract product parameters...")
                            extraction_response = await self.model.ainvoke(extraction_prompt)
                            
                            try:
                                import json
                                # Try to parse JSON from response
                                content = extraction_response.content if hasattr(extraction_response, 'content') else str(extraction_response)
                                # Extract JSON from response (may have surrounding text)
                                json_start = content.find('{')
                                json_end = content.rfind('}') + 1
                                if json_start >= 0 and json_end > json_start:
                                    json_str = content[json_start:json_end]
                                    extracted_data = json.loads(json_str)
                                    
                                    # Use extracted data if not already provided
                                    title = title or extracted_data.get("title", "New Product")
                                    vendor = vendor or extracted_data.get("vendor", "Unknown Vendor")
                                    product_type = product_type or extracted_data.get("product_type", "General")
                                    price = price or extracted_data.get("price", "0.00")
                                    sku = sku or extracted_data.get("sku", f"AUTO-{title.replace(' ', '-').upper()}")
                                    
                                    logger.info(f"LLM extracted: title={title}, vendor={vendor}, type={product_type}, price={price}, sku={sku}")
                                else:
                                    logger.warning("Could not parse JSON from LLM response, using defaults")
                                    title = title or "New Product"
                                    vendor = vendor or "Unknown Vendor"
                                    product_type = product_type or "General"
                                    price = price or "0.00"
                                    sku = sku or f"AUTO-{title.replace(' ', '-').upper()}"
                                    
                            except Exception as e:
                                logger.error(f"Error parsing LLM extraction response: {e}")
                                # Fallback to defaults
                                title = title or "New Product"
                                vendor = vendor or "Unknown Vendor"
                                product_type = product_type or "General"
                                price = price or "0.00"
                                sku = sku or "AUTO-NEW-PRODUCT"
                        
                        tool = self.tools["create_full_product"]
                        
                        # Call the tool directly (like products agent does)
                        result = await tool._arun(
                            title=title,
                            vendor=vendor,
                            product_type=product_type,
                            price=price,
                            sku=sku,
                            config={}
                        )
                        
                        # Format the response
                        if isinstance(result, dict) and result.get("success"):
                            response = f"""✅ Successfully created product **{title}**!

**Product Details:**
- **Product ID**: `{result.get('product_id', 'N/A')}`
- **Variant ID**: `{result.get('variant_id', 'N/A')}`
- **SKU**: {sku}
- **Price**: ${price}
- **Vendor**: {vendor}
- **Type**: {product_type}

**Admin URL**: {result.get('admin_url', 'N/A')}

The product has been created and is ready for use. You can now update pricing, add images, or make other modifications using the product and variant IDs above."""
                        else:
                            response = f"❌ Failed to create product: {str(result)}"
                        
                        logger.info(f"✅ Product creation completed")
                        
                    except Exception as e:
                        logger.error(f"Tool execution failed: {e}")
                        import traceback
                        logger.error(f"Full traceback: {traceback.format_exc()}")
                        response = f"❌ I encountered an error while creating the product: {str(e)}"
                else:
                    response = "❌ The create_full_product tool is not available."
            else:
                # General query - provide guidance
                response = f"""I'm ready to help with product management! I can help you:

**Create Products**: "Create a new product called [name] by vendor [vendor], type [type], price $[price], SKU [sku]"
**Update Products**: Add variants, modify details, manage inventory
**Special Products**: Create combos, open box items, duplicates

What would you like me to help you with?"""
            
            # Add response to state
            if response:
                state["messages"].append(AIMessage(
                    content=response,
                    metadata={"agent": self.name}
                ))
            else:
                state["messages"].append(AIMessage(
                    content="I couldn't process your request. Please try again.",
                    metadata={"agent": self.name}
                ))
            
            state["last_agent"] = self.name
            logger.info(f"✅ Product Management agent completed")
            return state
            
        except Exception as e:
            logger.error(f"Error in ProductManagementAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in product management agent: {str(e)}",
                metadata={"agent": self.name, "intermediate": True, "error": True}
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