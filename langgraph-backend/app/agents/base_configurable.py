"""
Base class for agents with configurable model selection
"""
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from app.config.model_config import model_config
import logging

logger = logging.getLogger(__name__)

class ConfigurableAgent(ABC):
    """Base agent class with configurable model selection"""
    
    def __init__(self, name: str, description: str, override_model: Optional[str] = None):
        self.name = name
        self.description = description
        self.override_model = override_model
        
        # Get LLM based on agent configuration
        self.model = self._initialize_model()
        
        # Track token usage for cost monitoring
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
    
    def _initialize_model(self):
        """Initialize the model based on configuration"""
        if self.override_model:
            # Use specific model override
            logger.info(f"Agent {self.name} using override model: {self.override_model}")
            # Parse override format and create model
            # This would need implementation based on override format
            pass
        
        # Use model configuration
        model = model_config.get_langchain_llm(self.name)
        config = model_config.get_model_for_agent(self.name)
        
        logger.info(f"Agent {self.name} initialized with model: {config['model']} (tier: {config.get('tier', 'default')})")
        
        return model
    
    def track_usage(self, input_tokens: int, output_tokens: int):
        """Track token usage and cost"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        # Estimate cost
        cost = model_config.estimate_cost(self.name, input_tokens, output_tokens)
        self.total_cost += cost
        
        logger.debug(f"Agent {self.name} usage - Input: {input_tokens}, Output: {output_tokens}, Cost: ${cost:.4f}")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for this agent"""
        return {
            "agent": self.name,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "model": model_config.get_model_for_agent(self.name)["model"]
        }
    
    @abstractmethod
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent logic"""
        pass