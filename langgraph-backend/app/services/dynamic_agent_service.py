"""
Dynamic Agent Service
Handles loading, testing, and management of dynamic agents
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.models import DynamicAgent, AgentTemplate

logger = logging.getLogger(__name__)


class DynamicAgentService:
    """Service for managing dynamic agents"""
    
    def __init__(self):
        self.loaded_agents: Dict[str, Any] = {}  # Cache of loaded agents
    
    async def load_agent(
        self,
        db: AsyncSession,
        agent_name: str
    ) -> Optional[DynamicAgent]:
        """Load a dynamic agent from database"""
        
        result = await db.execute(
            select(DynamicAgent).where(
                DynamicAgent.name == agent_name,
                DynamicAgent.is_active == True
            )
        )
        agent = result.scalar_one_or_none()
        
        if agent:
            logger.info(f"Loaded dynamic agent: {agent_name}")
        else:
            logger.warning(f"Dynamic agent not found: {agent_name}")
        
        return agent
    
    async def test_agent(
        self,
        db: AsyncSession,
        agent: DynamicAgent,
        test_query: str
    ) -> Dict[str, Any]:
        """Test if an agent can handle a query"""
        
        # Check routing keywords
        keywords_matched = []
        query_lower = test_query.lower()
        
        for keyword in (agent.routing_keywords or []):
            if keyword.lower() in query_lower:
                keywords_matched.append(keyword)
        
        # Check capabilities (could be more sophisticated)
        capabilities_matched = []
        for capability in (agent.capabilities or []):
            if any(word in query_lower for word in capability.lower().split()):
                capabilities_matched.append(capability)
        
        can_handle = len(keywords_matched) > 0 or len(capabilities_matched) > 0
        
        return {
            "can_handle": can_handle,
            "confidence": min(1.0, (len(keywords_matched) * 0.3 + len(capabilities_matched) * 0.2)),
            "matched_keywords": keywords_matched,
            "matched_capabilities": capabilities_matched,
            "agent_name": agent.name
        }
    
    async def get_agent_config(
        self,
        db: AsyncSession,
        agent: DynamicAgent
    ) -> Dict[str, Any]:
        """Get agent configuration for runtime"""
        
        return {
            "name": agent.name,
            "display_name": agent.display_name,
            "system_prompt": agent.system_prompt,
            "model_provider": agent.model_provider,
            "model_name": agent.model_name,
            "temperature": agent.temperature.get("value", 0.0) if isinstance(agent.temperature, dict) else agent.temperature,
            "max_tokens": agent.max_tokens,
            "tools": agent.tools or [],
            "mcp_servers": agent.mcp_servers or []
        }
    
    async def update_usage_stats(
        self,
        db: AsyncSession,
        agent_id: int,
        success: bool,
        response_time: int = None
    ):
        """Update agent usage statistics"""
        
        result = await db.execute(
            select(DynamicAgent).where(DynamicAgent.id == agent_id)
        )
        agent = result.scalar_one_or_none()
        
        if agent:
            # Initialize usage_count if None
            if agent.usage_count is None:
                agent.usage_count = 0
            agent.usage_count += 1
            
            # Update success rate
            stats = agent.success_rate or {"success": 0, "total": 0}
            stats["total"] += 1
            if success:
                stats["success"] += 1
            agent.success_rate = stats
            
            # Update average response time
            if response_time:
                if agent.avg_response_time:
                    # Rolling average
                    agent.avg_response_time = int(
                        (agent.avg_response_time * (agent.usage_count - 1) + response_time) 
                        / agent.usage_count
                    )
                else:
                    agent.avg_response_time = response_time
            
            await db.commit()


# Singleton instance
_dynamic_agent_service: Optional[DynamicAgentService] = None

def get_dynamic_agent_service() -> DynamicAgentService:
    """Get or create the dynamic agent service singleton"""
    global _dynamic_agent_service
    if _dynamic_agent_service is None:
        _dynamic_agent_service = DynamicAgentService()
    return _dynamic_agent_service