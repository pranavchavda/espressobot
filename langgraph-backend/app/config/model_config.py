"""
Model configuration for multi-model support via OpenRouter
"""
import os
from typing import Dict, Any, Optional
from enum import Enum

class ModelTier(Enum):
    """Model tiers for different use cases"""
    ORCHESTRATOR = "orchestrator"  # Complex reasoning, A2A coordination
    PRIMARY = "primary"            # Main agent operations
    AUXILIARY = "auxiliary"        # Simple tasks, utilities
    SPECIALIZED = "specialized"    # Domain-specific models

class ModelProvider(Enum):
    """Supported model providers"""
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    OPENAI = "openai"

class ModelConfig:
    """Configuration for model selection and routing"""
    
    # Default models for each tier (can be overridden by env vars)
    DEFAULT_MODELS = {
        ModelTier.ORCHESTRATOR: {
            "provider": ModelProvider.OPENROUTER,
            "model": "openai/gpt-5",  # When available
            "fallback": "anthropic/claude-3-opus-20240229",
            "temperature": 0.0,
            "max_tokens": 4096
        },
        ModelTier.PRIMARY: {
            "provider": ModelProvider.OPENROUTER,
            "model": "openai/gpt-5-mini",  # When available
            "fallback": "anthropic/claude-3-5-haiku-20241022",
            "temperature": 0.0,
            "max_tokens": 2048
        },
        ModelTier.AUXILIARY: {
            "provider": ModelProvider.OPENROUTER,
            "model": "openai/gpt-5-nano",  # When available
            "fallback": "anthropic/claude-3-haiku-20240307",
            "temperature": 0.0,
            "max_tokens": 1024
        },
        ModelTier.SPECIALIZED: {
            "provider": ModelProvider.OPENROUTER,
            "model": "deepseek/deepseek-chat",  # Good for code/data
            "fallback": "qwen/qwen-2-72b-instruct",
            "temperature": 0.0,
            "max_tokens": 2048
        }
    }
    
    # Agent to tier mapping
    AGENT_TIERS = {
        "orchestrator": ModelTier.ORCHESTRATOR,
        "a2a_orchestrator": ModelTier.ORCHESTRATOR,
        "router": ModelTier.PRIMARY,
        "products": ModelTier.PRIMARY,
        "pricing": ModelTier.PRIMARY,
        "inventory": ModelTier.PRIMARY,
        "sales": ModelTier.PRIMARY,
        "product_management": ModelTier.PRIMARY,
        "features": ModelTier.AUXILIARY,
        "media": ModelTier.AUXILIARY,
        "utility": ModelTier.AUXILIARY,
        "graphql": ModelTier.SPECIALIZED,
        "integrations": ModelTier.SPECIALIZED,
        "general": ModelTier.AUXILIARY
    }
    
    def __init__(self):
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Override models from environment if specified
        self._load_env_overrides()
    
    def _load_env_overrides(self):
        """Load model overrides from environment variables"""
        for tier in ModelTier:
            env_key = f"MODEL_{tier.value.upper()}"
            model_name = os.getenv(env_key)
            if model_name:
                # Parse format: provider/model
                if "/" in model_name:
                    provider, model = model_name.split("/", 1)
                    self.DEFAULT_MODELS[tier]["model"] = model_name
                    if provider == "openrouter":
                        self.DEFAULT_MODELS[tier]["provider"] = ModelProvider.OPENROUTER
                    elif provider == "anthropic":
                        self.DEFAULT_MODELS[tier]["provider"] = ModelProvider.ANTHROPIC
                    elif provider == "openai":
                        self.DEFAULT_MODELS[tier]["provider"] = ModelProvider.OPENAI
    
    def get_model_for_agent(self, agent_name: str) -> Dict[str, Any]:
        """Get model configuration for a specific agent"""
        tier = self.AGENT_TIERS.get(agent_name, ModelTier.AUXILIARY)
        return self.get_model_for_tier(tier)
    
    def get_model_for_tier(self, tier: ModelTier) -> Dict[str, Any]:
        """Get model configuration for a tier"""
        config = self.DEFAULT_MODELS[tier].copy()
        
        # Add API keys based on provider
        if config["provider"] == ModelProvider.OPENROUTER:
            config["api_key"] = self.openrouter_api_key
            config["base_url"] = "https://openrouter.ai/api/v1"
        elif config["provider"] == ModelProvider.ANTHROPIC:
            config["api_key"] = self.anthropic_api_key
        elif config["provider"] == ModelProvider.OPENAI:
            config["api_key"] = self.openai_api_key
        
        return config
    
    def get_langchain_llm(self, agent_name: str):
        """Get a LangChain LLM instance for an agent using the LLM factory"""
        from app.config.llm_factory import llm_factory, Provider
        
        config = self.get_model_for_agent(agent_name)
        
        # Map our provider enum to factory provider
        provider_map = {
            ModelProvider.OPENROUTER: Provider.OPENROUTER,
            ModelProvider.OPENAI: Provider.OPENAI,
            ModelProvider.ANTHROPIC: Provider.ANTHROPIC
        }
        
        preferred_provider = provider_map.get(config["provider"])
        
        # Extract base model name (remove provider prefix)
        model_name = config["model"]
        if "/" in model_name:
            model_name = model_name.split("/", 1)[1]
        
        # Map to our standardized model names
        model_map = {
            "gpt-5": "gpt-5",
            "gpt-5-mini": "gpt-5-mini",
            "gpt-5-nano": "gpt-5-nano",
            "claude-3-opus-20240229": "claude-3-opus",
            "claude-3-5-haiku-20241022": "claude-3-5-haiku",
            "claude-3-haiku-20240307": "claude-3-5-haiku",
            "deepseek-chat": "deepseek-chat",
            "qwen-2-72b-instruct": "qwen-2-72b"
        }
        
        standardized_model = model_map.get(model_name, model_name)
        
        return llm_factory.create_llm(
            model_name=standardized_model,
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            preferred_provider=preferred_provider
        )
    
    def estimate_cost(self, agent_name: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a model call"""
        config = self.get_model_for_agent(agent_name)
        model = config["model"]
        
        # Rough cost estimates (per 1M tokens)
        # These should be updated with actual pricing
        COSTS = {
            "gpt-5": {"input": 15.0, "output": 60.0},
            "gpt-5-mini": {"input": 2.0, "output": 8.0},
            "gpt-5-nano": {"input": 0.5, "output": 2.0},
            "claude-3-opus": {"input": 15.0, "output": 75.0},
            "claude-3-5-haiku": {"input": 0.25, "output": 1.25},
            "deepseek-chat": {"input": 0.14, "output": 0.28},
            "qwen-2-72b": {"input": 0.35, "output": 0.40}
        }
        
        # Find matching cost
        for key, cost in COSTS.items():
            if key in model.lower():
                input_cost = (input_tokens / 1_000_000) * cost["input"]
                output_cost = (output_tokens / 1_000_000) * cost["output"]
                return input_cost + output_cost
        
        # Default fallback cost
        return (input_tokens / 1_000_000) * 1.0 + (output_tokens / 1_000_000) * 2.0

# Global instance
model_config = ModelConfig()