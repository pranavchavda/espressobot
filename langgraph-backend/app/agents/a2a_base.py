"""
Base class for A2A-enabled agents that can request help from other agents
"""
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class A2AAgent(ABC):
    """Base class for agents that support Agent-to-Agent communication"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"A2A.{name}")
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process state with A2A awareness"""
        # Check if this is an A2A request
        messages = state.get("messages", [])
        is_a2a_request = False
        
        for msg in messages:
            if hasattr(msg, 'metadata') and msg.metadata.get('type') == 'a2a_request':
                is_a2a_request = True
                self.logger.info(f"📨 Received A2A request: {msg.content[:100]}...")
                break
        
        # Execute the agent's main logic
        result = await self.execute(state, is_a2a_request)
        
        # Check if we need help from another agent
        if self.needs_help(result, state):
            help_request = self.create_help_request(result, state)
            if help_request:
                result["help_request"] = help_request
                self.logger.info(f"🆘 Requesting help from {help_request.get('to')}")
        
        return result
    
    @abstractmethod
    async def execute(self, state: Dict[str, Any], is_a2a_request: bool) -> Dict[str, Any]:
        """Execute the agent's main logic"""
        pass
    
    def needs_help(self, result: Dict[str, Any], state: Dict[str, Any]) -> bool:
        """Determine if this agent needs help from another agent"""
        # Default: check if result indicates incomplete execution
        return result.get("needs_assistance", False)
    
    def create_help_request(self, result: Dict[str, Any], state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a help request for another agent"""
        if not result.get("help_needed"):
            return None
        
        return {
            "from": self.name,
            "to": result.get("help_from_agent"),
            "need": result.get("help_needed"),
            "context": result.get("help_context", {})
        }
    
    def can_help_with(self, request: str) -> bool:
        """Check if this agent can help with a specific request"""
        # Override in subclasses with specific capabilities
        return False