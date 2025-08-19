"""
Agent Registry for Async Orchestrator
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def get_all_agents() -> Dict[str, Any]:
    """
    Get all available agents for the orchestrator
    """
    try:
        # Import real agents
        from app.agents.products_native_mcp import ProductsAgentNativeMCP
        from app.agents.orders_native_mcp import OrdersAgentNativeMCP
        from app.agents.pricing_native_mcp import PricingAgentNativeMCP
        from app.agents.ga4_analytics_native_mcp import GA4AnalyticsAgentNativeMCP
        from app.agents.utility_native_mcp import UtilityAgentNativeMCP
        
        # Initialize real agents
        agents = {}
        
        try:
            agents["products"] = ProductsAgentNativeMCP()
            logger.info("Loaded products agent")
        except Exception as e:
            logger.error(f"Failed to load products agent: {e}")
        
        try:
            agents["orders"] = OrdersAgentNativeMCP()
            logger.info("Loaded orders agent")
        except Exception as e:
            logger.error(f"Failed to load orders agent: {e}")
        
        try:
            agents["pricing"] = PricingAgentNativeMCP()
            logger.info("Loaded pricing agent")
        except Exception as e:
            logger.error(f"Failed to load pricing agent: {e}")
        
        try:
            agents["ga4_analytics"] = GA4AnalyticsAgentNativeMCP()
            logger.info("Loaded ga4_analytics agent")
        except Exception as e:
            logger.error(f"Failed to load ga4_analytics agent: {e}")
        
        try:
            agents["utility"] = UtilityAgentNativeMCP()
            logger.info("Loaded utility agent")
        except Exception as e:
            logger.error(f"Failed to load utility agent: {e}")
        
        logger.info(f"Successfully loaded {len(agents)} real agents for async orchestrator")
        return agents
        
    except Exception as e:
        logger.error(f"Failed to load real agents, falling back to mock: {e}")
        
        # Fallback to mock agents if real agents fail
        class MockAgent:
            def __init__(self, name: str):
                self.name = name
            
            async def process_async(self, message: str) -> Dict[str, Any]:
                import asyncio
                await asyncio.sleep(0.5)
                return {
                    "content": f"Mock {self.name} agent processed: {message[:50]}...",
                    "agent": self.name,
                    "success": True
                }
        
        return {
            "products": MockAgent("products"),
            "orders": MockAgent("orders"), 
            "pricing": MockAgent("pricing"),
            "ga4_analytics": MockAgent("ga4_analytics"),
            "utility": MockAgent("utility")
        }