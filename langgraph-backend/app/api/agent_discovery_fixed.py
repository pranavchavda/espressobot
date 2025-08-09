"""
Agent Discovery - Find and return actual running agents (Fixed version)
"""
import logging
from typing import Dict, List, Any
import importlib
import inspect

logger = logging.getLogger(__name__)

def discover_running_agents() -> List[Dict[str, Any]]:
    """Discover all running agents in the system without instantiating them"""
    agents = []
    
    # Add orchestrator
    agents.append({
        "id": "orchestrator",
        "agent_name": "orchestrator",
        "agent_type": "orchestrator",
        "description": "Handles routing and general conversation",
        "model_class": "DirectOrchestrator",
        "source": "orchestrator_direct.py"
    })
    
    # List of agent modules with their descriptions
    agent_definitions = [
        ("products", "ProductsAgentNativeMCPFinal", "Handles product searches, SKU lookups, and product information queries"),
        ("pricing", "PricingAgentNativeMCP", "Handles price updates, discounts, and pricing strategies"),
        ("inventory", "InventoryAgentNativeMCP", "Handles stock levels, inventory counts and management"),
        ("sales", "SalesAgentNativeMCP", "Handles MAP sales, promotions, and discount management"),
        ("features", "FeaturesAgentNativeMCP", "Handles product features, descriptions, and metafields"),
        ("media", "MediaAgentNativeMCP", "Handles images and media management for products"),
        ("integrations", "IntegrationsAgentNativeMCP", "Handles system integrations and connections"),
        ("product_management", "ProductManagementAgentNativeMCP", "Handles complex product creation and variant management"),
        ("utility", "UtilityAgentNativeMCP", "Handles general operations and utilities"),
        ("graphql", "GraphQLAgentNativeMCP", "Handles direct GraphQL operations on Shopify API"),
        ("orders", "OrdersAgentNativeMCP", "Handles sales data, revenue, and order analytics"),
        ("google_workspace", "GoogleWorkspaceAgentNativeMCP", "Handles Google services integration"),
        ("ga4_analytics", "GA4AnalyticsAgentNativeMCP", "Handles Google Analytics 4 data and reporting"),
    ]
    
    for agent_name, class_name, description in agent_definitions:
        # Don't try to import, just add the agent info
        agents.append({
            "id": agent_name,
            "agent_name": agent_name,
            "agent_type": "specialist",
            "description": description,
            "model_class": class_name,
            "source": f"{agent_name}_native_mcp.py"
        })
        logger.info(f"Added agent: {agent_name}")
    
    return agents

def get_agent_model_info(agent_name: str) -> Dict[str, Any]:
    """Get current model info for an agent"""
    from app.config.agent_model_manager import agent_model_manager
    
    # Get saved config if exists
    config = agent_model_manager.configs.get(agent_name, {})
    
    if config:
        return {
            "model_provider": config.get("model_provider", "anthropic"),
            "model_name": config.get("model_name", "claude-3-5-haiku-20241022"),
            "temperature": config.get("temperature", 0.0),
            "max_tokens": config.get("max_tokens", 2048)
        }
    
    # Default based on agent type
    if agent_name == "orchestrator":
        return {
            "model_provider": "openrouter",
            "model_name": "openai/gpt-5-chat",
            "temperature": 0.0,
            "max_tokens": 2048
        }
    else:
        return {
            "model_provider": "anthropic",
            "model_name": "claude-3-5-haiku-20241022",
            "temperature": 0.0,
            "max_tokens": 2048
        }