"""
A2A-enabled Products Agent that can request help from other agents
"""
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage, HumanMessage
from app.agents.a2a_base import A2AAgent
from app.agents.products_native_mcp_final import ProductsAgentNativeMCPFinal
import logging
import re

logger = logging.getLogger(__name__)

class ProductsA2AAgent(A2AAgent):
    """Products agent with A2A communication capabilities"""
    
    def __init__(self):
        super().__init__(
            name="products",
            description="Handles product searches with ability to request pricing and inventory data"
        )
        # Use existing products agent as base
        self.base_agent = ProductsAgentNativeMCPFinal()
    
    async def execute(self, state: Dict[str, Any], is_a2a_request: bool) -> Dict[str, Any]:
        """Execute products logic with A2A awareness"""
        
        # Run base agent logic
        result = await self.base_agent(state)
        
        # If not an A2A request, check if we need additional data
        if not is_a2a_request:
            messages = state.get("messages", [])
            if messages:
                last_message = messages[-1]
                if isinstance(last_message, HumanMessage):
                    content = last_message.content.lower()
                    
                    # Check if user wants pricing info
                    if any(word in content for word in ["price", "cost", "pricing", "how much"]):
                        # Extract SKUs from our response
                        skus = self._extract_skus(result)
                        if skus:
                            result["needs_assistance"] = True
                            result["help_from_agent"] = "pricing"
                            result["help_needed"] = f"Get current pricing for SKUs: {', '.join(skus)}"
                            result["help_context"] = {"skus": skus}
                            logger.info(f"Products agent needs pricing data for {len(skus)} SKUs")
                    
                    # Check if user wants inventory info
                    elif any(word in content for word in ["stock", "inventory", "available", "in stock"]):
                        skus = self._extract_skus(result)
                        if skus:
                            result["needs_assistance"] = True
                            result["help_from_agent"] = "inventory"
                            result["help_needed"] = f"Check inventory levels for SKUs: {', '.join(skus)}"
                            result["help_context"] = {"skus": skus}
                            logger.info(f"Products agent needs inventory data for {len(skus)} SKUs")
                    
                    # Check if user wants both
                    elif ("price" in content or "cost" in content) and ("stock" in content or "available" in content):
                        skus = self._extract_skus(result)
                        if skus:
                            # Will request pricing first, then inventory
                            result["needs_assistance"] = True
                            result["help_from_agent"] = "pricing"
                            result["help_needed"] = f"Get pricing and then inventory for SKUs: {', '.join(skus)}"
                            result["help_context"] = {
                                "skus": skus,
                                "next_agent": "inventory"  # Signal chain of requests
                            }
        
        return result
    
    def _extract_skus(self, result: Dict[str, Any]) -> List[str]:
        """Extract SKUs from agent response"""
        skus = []
        
        # Look for SKUs in the response
        messages = result.get("messages", [])
        for msg in messages:
            if hasattr(msg, 'content'):
                # Simple SKU pattern matching (customize based on your SKU format)
                sku_pattern = r'\b[A-Z]{2,}-\d{3,}\b|\b\d{5,}\b'
                found_skus = re.findall(sku_pattern, msg.content)
                skus.extend(found_skus)
        
        # Also check if agent stored SKUs in metadata
        if "product_skus" in result:
            skus.extend(result["product_skus"])
        
        return list(set(skus))  # Remove duplicates
    
    def can_help_with(self, request: str) -> bool:
        """Check if products agent can help with a request"""
        keywords = ["product", "sku", "item", "listing", "search", "find"]
        return any(keyword in request.lower() for keyword in keywords)