"""
Extension to orchestrator for loading dynamic agents
"""

import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DynamicAgentLoader:
    """Loads dynamic agents into the orchestrator"""
    
    @staticmethod
    async def load_dynamic_agents(orchestrator, db_session: AsyncSession):
        """
        Load all active dynamic agents and register them with the orchestrator
        
        Args:
            orchestrator: The orchestrator instance to add agents to
            db_session: Database session for loading agent configurations
        """
        from app.agents.dynamic_agent import DynamicAgentFactory
        
        try:
            # Get list of available dynamic agents
            available_agents = await DynamicAgentFactory.list_available_agents(db_session)
            
            logger.info(f"Found {len(available_agents)} dynamic agents to load")
            
            # Load each agent
            for agent_info in available_agents:
                agent_name = agent_info['name']
                
                try:
                    # Create agent from database
                    agent = await DynamicAgentFactory.create_from_database(
                        db_session, 
                        agent_name
                    )
                    
                    if agent:
                        # Register with orchestrator
                        orchestrator.agents[agent.name] = agent
                        logger.info(f"Loaded dynamic agent: {agent.name}")
                        
                        # Optionally add to routing logic
                        if hasattr(orchestrator, '_dynamic_agents'):
                            orchestrator._dynamic_agents.append(agent)
                    
                except Exception as e:
                    logger.error(f"Failed to load dynamic agent {agent_name}: {e}")
            
            logger.info(f"Successfully loaded {len(orchestrator.agents)} total agents")
            
        except Exception as e:
            logger.error(f"Failed to load dynamic agents: {e}")
    
    @staticmethod
    async def reload_agent(orchestrator, db_session: AsyncSession, agent_name: str):
        """
        Reload a specific dynamic agent (useful after UI updates)
        
        Args:
            orchestrator: The orchestrator instance
            db_session: Database session
            agent_name: Name of the agent to reload
        """
        from app.agents.dynamic_agent import DynamicAgentFactory
        
        try:
            # Remove existing agent if present
            if agent_name in orchestrator.agents:
                del orchestrator.agents[agent_name]
                logger.info(f"Removed existing agent: {agent_name}")
            
            # Load updated agent
            agent = await DynamicAgentFactory.create_from_database(
                db_session,
                agent_name
            )
            
            if agent:
                orchestrator.agents[agent.name] = agent
                logger.info(f"Reloaded dynamic agent: {agent.name}")
                return True
            else:
                logger.warning(f"Failed to reload agent: {agent_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error reloading agent {agent_name}: {e}")
            return False


# Monkey-patch the orchestrator to support dynamic agents
def enhance_orchestrator_with_dynamic_loading(orchestrator_class):
    """
    Enhance the orchestrator class with dynamic agent loading capabilities
    """
    original_init = orchestrator_class.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self._dynamic_agents = []
        
        # Add method to load dynamic agents
        self.load_dynamic_agents = lambda db_session: DynamicAgentLoader.load_dynamic_agents(self, db_session)
        self.reload_agent = lambda db_session, agent_name: DynamicAgentLoader.reload_agent(self, db_session, agent_name)
    
    orchestrator_class.__init__ = new_init
    
    # Override routing to check dynamic agents
    original_route = orchestrator_class.route_request if hasattr(orchestrator_class, 'route_request') else None
    
    if original_route:
        def new_route(self, state):
            # First try static agents
            result = original_route(state)
            
            # If no static agent matched, check dynamic agents
            if result == 'general' or result == 'unknown':
                query = state.get('messages', [])[-1].content if state.get('messages') else ""
                
                for agent in self._dynamic_agents:
                    if agent.can_handle(query):
                        logger.info(f"Dynamic agent {agent.name} can handle query")
                        return agent.name
            
            return result
        
        orchestrator_class.route_request = new_route
    
    return orchestrator_class