"""
Agent Discovery - Find and return actual running agents
"""
import logging
from typing import Dict, List, Any
import importlib
import inspect

logger = logging.getLogger(__name__)

def discover_running_agents() -> List[Dict[str, Any]]:
    """Discover all running agents in the system"""
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
    
    # List of agent modules and their classes
    agent_modules = [
        ("app.agents.products_native_mcp_final", "ProductsAgentNativeMCPFinal", "products"),
        ("app.agents.pricing_native_mcp", "PricingAgentNativeMCP", "pricing"),
        ("app.agents.inventory_native_mcp", "InventoryAgentNativeMCP", "inventory"),
        ("app.agents.sales_native_mcp", "SalesAgentNativeMCP", "sales"),
        ("app.agents.features_native_mcp", "FeaturesAgentNativeMCP", "features"),
        ("app.agents.media_native_mcp", "MediaAgentNativeMCP", "media"),
        ("app.agents.integrations_native_mcp", "IntegrationsAgentNativeMCP", "integrations"),
        ("app.agents.product_mgmt_native_mcp", "ProductManagementAgentNativeMCP", "product_management"),
        ("app.agents.utility_native_mcp", "UtilityAgentNativeMCP", "utility"),
        ("app.agents.graphql_native_mcp", "GraphQLAgentNativeMCP", "graphql"),
        ("app.agents.orders_native_mcp", "OrdersAgentNativeMCP", "orders"),
        ("app.agents.google_workspace_native_mcp", "GoogleWorkspaceAgentNativeMCP", "google_workspace"),
        ("app.agents.ga4_analytics_native_mcp", "GA4AnalyticsAgentNativeMCP", "ga4_analytics"),
    ]
    
    for module_name, class_name, agent_name in agent_modules:
        try:
            # Try to import the module
            module = importlib.import_module(module_name)
            agent_class = getattr(module, class_name, None)
            
            if agent_class:
                # Try to instantiate to get description
                try:
                    temp_agent = agent_class()
                    description = getattr(temp_agent, 'description', f"{agent_name} agent")
                    # Clean up if it has a cleanup method
                    if hasattr(temp_agent, 'cleanup'):
                        try:
                            import asyncio
                            asyncio.run(temp_agent.cleanup())
                        except:
                            pass
                except Exception as e:
                    logger.debug(f"Could not instantiate {class_name} for description: {e}")
                    description = f"{agent_name} specialist agent"
                
                agents.append({
                    "id": agent_name,
                    "agent_name": agent_name,
                    "agent_type": "specialist",
                    "description": description,
                    "model_class": class_name,
                    "source": f"{module_name.split('.')[-1]}.py"
                })
                logger.info(f"Discovered agent: {agent_name}")
        except ImportError as e:
            logger.warning(f"Could not import {module_name}: {e}")
        except Exception as e:
            logger.error(f"Error discovering agent {agent_name}: {e}")
    
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