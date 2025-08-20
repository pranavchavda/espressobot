"""
API endpoints for managing dynamic agents
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from app.database.session import get_db
from app.database.models import DynamicAgent, AgentTemplate, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dynamic-agents", tags=["dynamic-agents"])


# Pydantic models for requests/responses
class CreateAgentRequest(BaseModel):
    name: str
    display_name: str
    description: str
    agent_type: str = "specialist"
    system_prompt: str
    model_provider: str = "openrouter"
    model_name: str = "gpt-5-nano"
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    tools: List[Dict[str, Any]] = []
    mcp_servers: List[str] = []
    capabilities: List[str] = []
    routing_keywords: List[str] = []
    example_queries: List[str] = []


# Infer provider from a model name/slug
def _infer_provider(model_name: Optional[str]) -> Optional[str]:
    if not model_name:
        return None
    lower = model_name.lower()
    if lower.startswith("openai/"):
        return "openai"
    if lower.startswith("anthropic/"):
        return "anthropic"
    if lower.startswith("perplexity/"):
        return "perplexity"
    # Heuristic: presence of a slash indicates OpenRouter or other router
    if "/" in lower:
        return "openrouter"
    # If it's a short name, leave as-is and let defaults apply
    return None


class UpdateAgentRequest(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    max_completion_tokens: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    mcp_servers: Optional[List[str]] = None
    capabilities: Optional[List[str]] = None
    routing_keywords: Optional[List[str]] = None
    example_queries: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TestAgentRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


@router.get("/")
async def list_agents(
    db: AsyncSession = Depends(get_db),
    include_inactive: bool = False
):
    """List all dynamic agents"""
    query = select(DynamicAgent)
    if not include_inactive:
        query = query.where(DynamicAgent.is_active == True)
    
    result = await db.execute(query)
    agents = result.scalars().all()
    
    return [
        {
            "id": agent.id,
            "name": agent.name,
            "display_name": agent.display_name,
            "description": agent.description,
            "is_active": agent.is_active,
            "is_tested": agent.is_tested,
            "usage_count": agent.usage_count,
            "success_rate": agent.success_rate,
            "created_at": agent.created_at.isoformat() if agent.created_at else None
        }
        for agent in agents
    ]


@router.get("/{agent_name}")
async def get_agent(
    agent_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific agent"""
    result = await db.execute(
        select(DynamicAgent).where(DynamicAgent.name == agent_name)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    return {
        "id": agent.id,
        "name": agent.name,
        "display_name": agent.display_name,
        "description": agent.description,
        "agent_type": agent.agent_type,
        "system_prompt": agent.system_prompt,
        "model_provider": agent.model_provider,
        "model_name": agent.model_name,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "max_completion_tokens": agent.max_completion_tokens if hasattr(agent, 'max_completion_tokens') else None,
        "tools": agent.tools,
        "mcp_servers": agent.mcp_servers,
        "capabilities": agent.capabilities,
        "routing_keywords": agent.routing_keywords,
        "example_queries": agent.example_queries,
        "is_active": agent.is_active,
        "is_tested": agent.is_tested,
        "usage_count": agent.usage_count,
        "success_rate": agent.success_rate,
        "last_error": agent.last_error,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None
    }


@router.post("/")
async def create_agent(
    request: CreateAgentRequest,
    db: AsyncSession = Depends(get_db),
    # current_user: User = Depends(get_current_user)  # Add auth when ready
):
    """Create a new dynamic agent"""
    
    # Check if agent name already exists
    existing = await db.execute(
        select(DynamicAgent).where(DynamicAgent.name == request.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Agent {request.name} already exists")
    
    # Infer provider from model_name if a slug is used or if unset
    inferred = _infer_provider(request.model_name)
    model_provider = inferred or request.model_provider or "openrouter"

    # Create new agent
    agent = DynamicAgent(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        agent_type=request.agent_type,
        system_prompt=request.system_prompt,
        model_provider=model_provider,
        model_name=request.model_name,
        temperature={"value": request.temperature} if request.temperature is not None else None,
        max_tokens=request.max_tokens,
        tools=request.tools,
        mcp_servers=request.mcp_servers,
        capabilities=request.capabilities,
        routing_keywords=request.routing_keywords,
        example_queries=request.example_queries,
        # created_by=current_user.id  # Add when auth is ready
    )
    
    # Handle max_completion_tokens for OpenAI models
    if request.max_completion_tokens is not None:
        agent.max_completion_tokens = request.max_completion_tokens
    
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    
    logger.info(f"Created new dynamic agent: {agent.name}")
    
    return {
        "id": agent.id,
        "name": agent.name,
        "message": f"Agent {agent.name} created successfully"
    }


@router.put("/{agent_name}")
async def update_agent(
    agent_name: str,
    request: UpdateAgentRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Update an existing dynamic agent"""
    
    # Get existing agent
    result = await db.execute(
        select(DynamicAgent).where(DynamicAgent.name == agent_name)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    # If model_name changes or is provided, infer provider unless explicitly set
    incoming_model_name = update_data.get("model_name")
    incoming_provider = update_data.get("model_provider")
    if incoming_model_name and not incoming_provider:
        inf = _infer_provider(incoming_model_name)
        if inf:
            update_data["model_provider"] = inf
    elif incoming_model_name and incoming_provider:
        # If both provided but mismatch with slug prefix, align to slug
        inf = _infer_provider(incoming_model_name)
        if inf and inf != incoming_provider:
            update_data["model_provider"] = inf

    for field, value in update_data.items():
        if field == "temperature" and value is not None:
            setattr(agent, field, {"value": value})
        elif field == "temperature" and value is None:
            setattr(agent, field, None)
        else:
            setattr(agent, field, value)
    
    agent.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(agent)
    
    # TODO: Trigger orchestrator reload in background
    # background_tasks.add_task(reload_agent_in_orchestrator, agent_name)
    
    logger.info(f"Updated dynamic agent: {agent.name}")
    
    return {
        "id": agent.id,
        "name": agent.name,
        "message": f"Agent {agent.name} updated successfully"
    }


@router.delete("/{agent_name}")
async def delete_agent(
    agent_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a dynamic agent (soft delete by deactivating)"""
    
    result = await db.execute(
        select(DynamicAgent).where(DynamicAgent.name == agent_name)
    )
    agent = result.scalar_one_or_none()
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    
    # Soft delete by deactivating
    agent.is_active = False
    agent.updated_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info(f"Deactivated dynamic agent: {agent.name}")
    
    return {
        "name": agent.name,
        "message": f"Agent {agent.name} deactivated successfully"
    }


@router.post("/{agent_name}/test")
async def test_agent(
    agent_name: str,
    request: TestAgentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test a dynamic agent with a sample query"""
    
    from app.agents.dynamic_agent import DynamicAgentFactory
    
    # Create agent instance
    agent = await DynamicAgentFactory.create_from_database(db, agent_name)
    
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found or inactive")
    
    try:
        # Test if agent can handle the query
        can_handle = agent.can_handle(request.query)
        
        # Run a test query (simplified - would need full orchestrator context in production)
        if can_handle:
            # Here you would actually run the agent
            # For now, just return capability check
            response = {
                "can_handle": can_handle,
                "agent_name": agent.name,
                "matched_keywords": [
                    kw for kw in agent.routing_keywords 
                    if kw.lower() in request.query.lower()
                ],
                "message": "Agent can handle this query"
            }
            
            # Update test status
            await db.execute(
                update(DynamicAgent)
                .where(DynamicAgent.name == agent_name)
                .values(is_tested=True)
            )
            await db.commit()
        else:
            response = {
                "can_handle": can_handle,
                "agent_name": agent.name,
                "message": "Agent cannot handle this query"
            }
        
        return response
        
    except Exception as e:
        logger.error(f"Error testing agent {agent_name}: {e}")
        
        # Update error in database
        await db.execute(
            update(DynamicAgent)
            .where(DynamicAgent.name == agent_name)
            .values(last_error=str(e))
        )
        await db.commit()
        
        raise HTTPException(status_code=500, detail=f"Error testing agent: {str(e)}")


@router.get("/templates/")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = None
):
    """List available agent templates"""
    query = select(AgentTemplate)
    if category:
        query = query.where(AgentTemplate.category == category)
    query = query.where(AgentTemplate.is_public == True)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return [
        {
            "id": template.id,
            "name": template.name,
            "category": template.category,
            "description": template.description,
            "usage_count": template.usage_count,
            "rating": template.rating,
            "is_featured": template.is_featured
        }
        for template in templates
    ]


@router.post("/from-template/{template_name}")
async def create_from_template(
    template_name: str,
    new_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Create a new agent from a template"""
    
    # Get template
    result = await db.execute(
        select(AgentTemplate).where(AgentTemplate.name == template_name)
    )
    template = result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_name} not found")
    
    # Check if new name already exists
    existing = await db.execute(
        select(DynamicAgent).where(DynamicAgent.name == new_name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Agent {new_name} already exists")
    
    # Create agent from template
    config = template.config
    # Infer provider from template model_name if needed
    tmpl_model_name = config.get('model_name')
    tmpl_provider = config.get('model_provider')
    inferred = _infer_provider(tmpl_model_name)
    if inferred and tmpl_provider != inferred:
        tmpl_provider = inferred
    if not tmpl_provider:
        tmpl_provider = "openrouter"
    agent = DynamicAgent(
        name=new_name,
        display_name=config.get('display_name', new_name),
        description=config.get('description', ''),
        system_prompt=config.get('system_prompt', ''),
        model_provider=tmpl_provider,
        model_name=tmpl_model_name or 'gpt-5-nano',
        temperature=config.get('temperature', {"value": 0.0}),
        max_tokens=config.get('max_tokens', 2048),
        tools=config.get('tools', []),
        mcp_servers=config.get('mcp_servers', []),
        capabilities=config.get('capabilities', []),
        routing_keywords=config.get('routing_keywords', []),
        example_queries=config.get('example_queries', [])
    )
    
    db.add(agent)
    
    # Update template usage count
    template.usage_count += 1
    
    await db.commit()
    await db.refresh(agent)
    
    logger.info(f"Created agent {new_name} from template {template_name}")
    
    return {
        "id": agent.id,
        "name": agent.name,
        "message": f"Agent {agent.name} created from template successfully"
    }