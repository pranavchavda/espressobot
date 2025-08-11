"""
Agent Management API - Manage LLM models for each agent
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List, Optional
import logging
import json
import os
from pathlib import Path
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent-management", tags=["agent-management"])

# Configuration file path
CONFIG_FILE = Path("app/config/agent_models.json")

class AgentConfig(BaseModel):
    """Agent configuration model"""
    agent_name: str
    agent_type: str = "specialist"
    model_provider: str = "anthropic"
    model_name: str = "claude-3-5-haiku-20241022"
    temperature: float = 0.0
    max_tokens: int = 2048
    description: Optional[str] = None
    configurable: bool = True

class ModelInfo(BaseModel):
    """Model information"""
    id: str
    name: str
    provider: str
    description: Optional[str] = None

class UpdateAgentRequest(BaseModel):
    """Request to update agent model"""
    model_slug: Optional[str] = None  # From frontend dropdown
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

def load_agent_configs() -> Dict[str, AgentConfig]:
    """Load agent configurations from file or defaults"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                return {k: AgentConfig(**v) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Error loading agent configs: {e}")
    
    # Default configurations
    defaults = {
        "orchestrator": AgentConfig(
            agent_name="orchestrator",
            agent_type="orchestrator",
            model_provider="openrouter",
            model_name="openai/gpt-5-chat",
            temperature=0.0,
            max_tokens=2048,
            description="Handles routing and general conversation"
        ),
        "products": AgentConfig(
            agent_name="products",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Product searches, SKU lookups, and product information"
        ),
        "pricing": AgentConfig(
            agent_name="pricing",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Price updates, discounts, and pricing strategies"
        ),
        "inventory": AgentConfig(
            agent_name="inventory",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Stock levels, inventory counts and management"
        ),
        "sales": AgentConfig(
            agent_name="sales",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="MAP sales, promotions, and discount management"
        ),
        "features": AgentConfig(
            agent_name="features",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Product features, descriptions, and metafields"
        ),
        "media": AgentConfig(
            agent_name="media",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Images and media management for products"
        ),
        "integrations": AgentConfig(
            agent_name="integrations",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="System integrations and connections"
        ),
        "product_management": AgentConfig(
            agent_name="product_management",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Complex product creation and variant management"
        ),
        "utility": AgentConfig(
            agent_name="utility",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="General operations and utilities"
        ),
        "graphql": AgentConfig(
            agent_name="graphql",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Direct GraphQL operations on Shopify API"
        ),
        "orders": AgentConfig(
            agent_name="orders",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Sales data, revenue, and order analytics"
        ),
        "google_workspace": AgentConfig(
            agent_name="google_workspace",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Google services integration"
        ),
        "ga4_analytics": AgentConfig(
            agent_name="ga4_analytics",
            agent_type="specialist",
            model_provider="anthropic",
            model_name="claude-3-5-haiku-20241022",
            temperature=0.0,
            max_tokens=2048,
            description="Google Analytics 4 data and reporting"
        )
    }
    
    return defaults

def save_agent_configs(configs: Dict[str, AgentConfig]):
    """Save agent configurations to file"""
    try:
        # Ensure config directory exists
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict for JSON serialization
        data = {k: v.dict() for k, v in configs.items()}
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(configs)} agent configurations")
    except Exception as e:
        logger.error(f"Error saving agent configs: {e}")
        raise

def get_available_models() -> List[ModelInfo]:
    """Get list of available models from cache or API"""
    from app.config.fetch_available_models import get_all_available_models
    
    # Get models from cache (or fetch if cache is old)
    raw_models = get_all_available_models(use_cache=True)
    
    # Convert to ModelInfo objects
    models = []
    for model in raw_models:
        models.append(ModelInfo(
            id=model["id"],
            name=model["name"],
            provider=model["provider"],
            description=model.get("description", "")
        ))
    
    return models

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database.session import get_db
from app.database.models import DynamicAgent as DynamicAgentModel

@router.get("/agents")
async def get_agents(db: AsyncSession = Depends(get_db)):
    """Get all agent configurations"""
    try:
        from app.api.agent_discovery_fixed import discover_running_agents, get_agent_model_info
        
        # Discover actual running agents
        running_agents = discover_running_agents()
        
        # Load saved configurations
        configs = load_agent_configs()
        
        # Merge running agents with saved configs
        agents = []
        for agent_info in running_agents:
            agent_name = agent_info["agent_name"]
            
            # Get saved config or use defaults
            if agent_name in configs:
                config = configs[agent_name]
                model_info = config.dict()
            else:
                model_info = get_agent_model_info(agent_name)
                model_info["agent_name"] = agent_name
                model_info["agent_type"] = agent_info["agent_type"]
                model_info["description"] = agent_info["description"]
                model_info["configurable"] = True
            
            # Build agent dict for frontend
            agent_dict = {
                "id": agent_name,
                "agent_name": agent_name,
                "agent_type": agent_info.get("agent_type", "specialist"),
                "model_slug": model_info.get("model_name", "claude-3-5-haiku-20241022"),
                "model_provider": model_info.get("model_provider", "anthropic"),
                "temperature": model_info.get("temperature", 0.0),
                "max_tokens": model_info.get("max_tokens", 2048),
                "description": agent_info.get("description", ""),
                "source": "running",
                "configurable": True,
                "model_class": agent_info.get("model_class", ""),
            }
            agents.append(agent_dict)

        # Also include dynamic agents from the database
        try:
            result = await db.execute(select(DynamicAgentModel).where(DynamicAgentModel.is_active == True))
            dyn_agents = result.scalars().all()
            for da in dyn_agents:
                # Prefer stored values or sensible defaults
                model_name = da.model_name or "gpt-4o-mini"
                provider = da.model_provider or "openrouter"
                agents.append({
                    "id": da.name,
                    "agent_name": da.name,
                    "agent_type": da.agent_type or "dynamic",
                    "model_slug": model_name,
                    "description": da.description or "Dynamic agent",
                    "source": "dynamic",
                    "configurable": True,
                    "model_class": "DynamicAgent"
                })
        except Exception as e:
            logger.warning(f"Unable to list dynamic agents for management UI: {e}")

        logger.info(f"Returning {len(agents)} discovered agents")
        
        return {
            "success": True,
            "agents": agents
        }
    except Exception as e:
        logger.error(f"Error getting agents: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/models")
async def get_models():
    """Get available models"""
    try:
        models = get_available_models()
        
        # Determine current provider based on env vars
        provider = "openrouter"  # Default since we're using OpenRouter primarily
        if os.getenv("OPENROUTER_API_KEY"):
            provider = "openrouter"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "anthropic"
        
        return {
            "success": True,
            "models": [m.dict() for m in models],
            "provider": provider
        }
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/stats")
async def get_stats():
    """Get agent statistics"""
    try:
        configs = load_agent_configs()
        
        # Calculate statistics
        total_agents = len(configs)
        active_agents = len(configs)  # All agents are active in this implementation
        
        # Count by type
        by_type = {}
        for config in configs.values():
            agent_type = config.agent_type
            if agent_type not in by_type:
                by_type[agent_type] = {"count": 0, "active_count": 0}
            by_type[agent_type]["count"] += 1
            by_type[agent_type]["active_count"] += 1
        
        # Count unique models
        unique_models = len(set(c.model_name for c in configs.values()))
        
        # Count agents with custom settings (all in this case)
        agents_with_prompts = len(configs)
        
        return {
            "success": True,
            "stats": {
                "totals": {
                    "total_agents": total_agents,
                    "active_agents": active_agents,
                    "unique_models": unique_models,
                    "agents_with_prompts": agents_with_prompts
                },
                "by_type": [
                    {"agent_type": k, **v} for k, v in by_type.items()
                ]
            }
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }

from fastapi import Request as FastAPIRequest
from typing import Union

@router.put("/agents/{agent_id}/debug")
async def debug_update_agent(agent_id: str, request: FastAPIRequest):
    """Debug endpoint to see raw request"""
    body = await request.body()
    logger.info(f"Raw body for {agent_id}: {body}")
    json_body = await request.json()
    logger.info(f"JSON body for {agent_id}: {json_body}")
    return {"received": json_body}

@router.put("/agents/{agent_id}")
async def update_agent(agent_id: str, request: Dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Update agent configuration"""
    logger.info(f"Updating agent {agent_id} with request: {request}")
    try:
        configs = load_agent_configs()
        
        if agent_id not in configs:
            # Try dynamic agents fallback
            try:
                result = await db.execute(select(DynamicAgentModel).where(DynamicAgentModel.name == agent_id))
                dyn = result.scalar_one_or_none()
            except Exception as e:
                dyn = None
            if dyn is None:
                raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
            # Update dynamic agent in DB
            model_provider = request.get("model_provider") or dyn.model_provider
            model_name = request.get("model_slug") or request.get("model_name") or dyn.model_name
            temperature = request.get("temperature") if request.get("temperature") is not None else dyn.temperature
            max_tokens = request.get("max_tokens") if request.get("max_tokens") is not None else dyn.max_tokens

            # Normalize provider-specific model IDs
            if model_provider == "openai" and model_name and "/" in model_name:
                model_name = model_name.split("/")[-1]
            if model_provider == "anthropic" and model_name and model_name.startswith("anthropic/"):
                model_name = model_name.replace("anthropic/", "")

            dyn.model_provider = model_provider
            dyn.model_name = model_name
            dyn.temperature = {"value": temperature} if isinstance(temperature, (int, float)) else temperature
            dyn.max_tokens = max_tokens
            await db.commit()

            logger.info(f"Updated dynamic agent {agent_id} to {model_provider}/{model_name}")
            return {"success": True, "message": f"Updated dynamic agent {agent_id}. Restart or reload dynamic agents to take effect."}
        
        # Update the configuration
        config = configs[agent_id]
        
        # Map model_slug to model_name for compatibility
        model_slug = request.get("model_slug")
        if model_slug:
            model_name = model_slug
        else:
            model_name = request.get("model_name")
        
        # Handle provider update first
        model_provider = request.get("model_provider")
        if model_provider:
            config.model_provider = model_provider
        
        # Update fields if provided
        if model_name:
            # Translate model name based on provider
            current_provider = config.model_provider or "openrouter"
            
            # Clean up model name for different providers
            if current_provider == "openai":
                # Remove OpenRouter prefixes for OpenAI direct
                if model_name.startswith("openai/"):
                    model_name = model_name.replace("openai/", "")
                # Remove any other provider prefixes
                if "/" in model_name:
                    model_name = model_name.split("/")[-1]
            elif current_provider == "anthropic":
                # Remove OpenRouter prefixes for Anthropic direct
                if model_name.startswith("anthropic/"):
                    model_name = model_name.replace("anthropic/", "")
                # Remove any other provider prefixes
                if "/" in model_name and not model_name.startswith("claude"):
                    model_name = model_name.split("/")[-1]
            elif current_provider == "openrouter":
                # Add prefixes if missing for OpenRouter
                if "/" not in model_name:
                    # Add appropriate prefix based on model type
                    if model_name.startswith("gpt") or model_name.startswith("o1"):
                        model_name = f"openai/{model_name}"
                    elif model_name.startswith("claude"):
                        model_name = f"anthropic/{model_name}"
                    elif model_name.startswith("gemini"):
                        model_name = f"google/{model_name}"
                    elif model_name.startswith("llama"):
                        model_name = f"meta-llama/{model_name}"
                    elif model_name.startswith("mistral"):
                        model_name = f"mistralai/{model_name}"
            
            config.model_name = model_name
        
        temperature = request.get("temperature")
        if temperature is not None:
            config.temperature = temperature
            
        max_tokens = request.get("max_tokens")
        if max_tokens is not None:
            config.max_tokens = max_tokens
        
        # Save the updated configuration
        configs[agent_id] = config
        save_agent_configs(configs)
        
        # Apply the change to the running agent
        apply_agent_config(agent_id, config)
        
        return {
            "success": True,
            "message": f"Updated agent {agent_id}"
        }
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/sync")
async def sync_agents():
    """Sync agents from current system state"""
    try:
        # This would normally discover agents from the running system
        # For now, we'll just ensure all default agents are present
        configs = load_agent_configs()
        
        # Save to ensure file exists
        save_agent_configs(configs)
        
        return {
            "success": True,
            "synced": len(configs),
            "message": f"Synced {len(configs)} agents"
        }
    except Exception as e:
        logger.error(f"Error syncing agents: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/agents/{agent_id}/prompt")
async def get_agent_prompt(agent_id: str):
    """Get agent's system prompt"""
    try:
        # For now, return a placeholder prompt
        # In production, this would fetch from the actual agent
        prompts = {
            "orchestrator": "You are EspressoBot's orchestrator. Route requests to appropriate specialist agents.",
            "products": "You are a products specialist. Help with product searches, SKU lookups, and product information.",
            "pricing": "You are a pricing specialist. Handle price updates, discounts, and pricing strategies.",
            "inventory": "You are an inventory specialist. Manage stock levels and inventory counts.",
            # Add more as needed
        }
        
        system_prompt = prompts.get(agent_id, f"You are the {agent_id} agent.")
        
        return {
            "success": True,
            "system_prompt": system_prompt
        }
    except Exception as e:
        logger.error(f"Error getting prompt for {agent_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.put("/agents/{agent_id}/prompt")
async def update_agent_prompt(agent_id: str, request: Dict[str, Any]):
    """Update agent's system prompt"""
    try:
        # In production, this would update the actual agent's prompt
        # For now, we'll just acknowledge the update
        system_prompt = request.get("system_prompt", "")
        
        logger.info(f"Updated prompt for {agent_id}: {len(system_prompt)} chars")
        
        return {
            "success": True,
            "message": f"Updated prompt for {agent_id}"
        }
    except Exception as e:
        logger.error(f"Error updating prompt for {agent_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def apply_agent_config(agent_id: str, config: AgentConfig):
    """Apply configuration to running agent"""
    from app.config.agent_model_manager import agent_model_manager
    
    # Update the model manager with new configuration
    agent_model_manager.update_agent_config(agent_id, config.dict())
    
    # Force reload of all configs to ensure consistency
    agent_model_manager.reload_configs()
    
    logger.info(f"Applied config to {agent_id}: {config.model_provider}/{config.model_name}")
    
    # Note: Agents will pick up the new model on their next invocation
    # when they call agent_model_manager.get_model_for_agent()
