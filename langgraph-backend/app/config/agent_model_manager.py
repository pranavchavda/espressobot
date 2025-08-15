"""
Agent Model Manager - Dynamic model configuration for agents
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from app.config.llm_factory import llm_factory, Provider

logger = logging.getLogger(__name__)

class AgentModelManager:
    """Manages dynamic model configuration for agents"""
    
    def __init__(self):
        self.config_file = Path("app/config/agent_models.json")
        self.configs = self._load_configs()
    
    def _load_configs(self) -> Dict[str, Any]:
        """Load configurations from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading agent configs: {e}")
        return {}
    
    def get_model_for_agent(self, agent_name: str):
        """Get configured model for an agent, or create default"""
        # Check if we have a saved configuration
        if agent_name in self.configs:
            config = self.configs[agent_name]
            
            # Map provider strings to Provider enum
            provider_map = {
                "openrouter": Provider.OPENROUTER,
                "openai": Provider.OPENAI,
                "anthropic": Provider.ANTHROPIC
            }
            
            preferred_provider = provider_map.get(config.get("model_provider"))
            
            # Get model name - only normalize if NOT using OpenRouter
            model_name = config.get("model_name")
            if preferred_provider != Provider.OPENROUTER:
                model_name = self._normalize_model_name(model_name)
            
            # Create model using factory with proper parameters
            try:
                # Get proper parameters based on model type
                model_params = self._get_model_parameters(
                    model_name, 
                    config.get("temperature", 0.0),
                    config.get("max_tokens", 2048),
                    preferred_provider
                )
                
                # Convert max_completion_tokens to max_tokens for create_llm()
                create_params = model_params.copy()
                if 'max_completion_tokens' in create_params:
                    create_params['max_tokens'] = create_params.pop('max_completion_tokens')
                
                return llm_factory.create_llm(
                    model_name=model_name,
                    preferred_provider=preferred_provider,
                    **create_params
                )
            except Exception as e:
                logger.error(f"Error creating model for {agent_name}: {e}")
        
        # Default fallback based on agent type
        if agent_name == "orchestrator":
            # Orchestrator uses GPT-5-chat (no temperature/token params for GPT-5)
            model_params = self._get_model_parameters("gpt-5-chat", 0.0, 2048, Provider.OPENROUTER)
            # Convert max_completion_tokens to max_tokens for create_llm()
            create_params = model_params.copy()
            if 'max_completion_tokens' in create_params:
                create_params['max_tokens'] = create_params.pop('max_completion_tokens')
            
            return llm_factory.create_llm(
                model_name="gpt-5-chat",
                preferred_provider=Provider.OPENROUTER,
                **create_params
            )
        else:
            # All other agents use Claude 3.5 Haiku
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model="claude-3-5-haiku-20241022",
                temperature=0.0,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
    
    def _get_model_parameters(self, model_name: str, temperature: float, max_tokens: int, provider: Provider) -> Dict[str, Any]:
        """Get proper parameters based on model type and provider"""
        params = {}
        
        # Check if it's a GPT-5 series model
        is_gpt5_series = any(x in model_name.lower() for x in ['gpt-5', 'gpt5'])
        
        # Check if it's an OpenAI provider model
        is_openai_model = (provider == Provider.OPENAI or 
                          any(x in model_name.lower() for x in ['gpt-', 'o1-']))
        
        # GPT-5 series models don't support temperature or max_tokens parameters
        if is_gpt5_series:
            logger.info(f"GPT-5 series model detected ({model_name}): excluding temperature and token limits")
            # GPT-5 models don't accept temperature or token parameters
            return params
        
        # Add temperature for non-GPT-5 models
        params["temperature"] = temperature
        
        # Use max_completion_tokens for OpenAI models, max_tokens for others
        if is_openai_model and not is_gpt5_series:
            params["max_completion_tokens"] = max_tokens
            logger.info(f"OpenAI model detected ({model_name}): using max_completion_tokens={max_tokens}")
        elif not is_gpt5_series:
            params["max_tokens"] = max_tokens
            logger.info(f"Non-OpenAI model detected ({model_name}): using max_tokens={max_tokens}")
        
        return params
    
    def _normalize_model_name(self, model_name: str) -> str:
        """Normalize model names to match factory expectations"""
        # Map full model names to factory names
        # Note: Don't truncate Claude model dates - they're required!
        mappings = {
            "openai/gpt-5-chat": "gpt-5-chat",
            "openai/gpt-5": "gpt-5",
            "openai/gpt-5-mini": "gpt-5-mini",
            "openai/gpt-5-nano": "gpt-5-nano",
            "openai/gpt-4.1": "gpt-4",
            "deepseek/deepseek-chat": "deepseek-chat",
            "qwen/qwen-2-72b-instruct": "qwen-2-72b",
            "z-ai/glm-4.5": "glm-4.5"
        }
        
        # Check if we have a mapping
        if model_name in mappings:
            return mappings[model_name]
        
        # Check if it already matches a short name
        short_names = ["gpt-5-chat", "gpt-5", "gpt-5-mini", "gpt-5-nano", 
                      "gpt-4", "claude-3-opus", "claude-3-5-haiku", 
                      "deepseek-chat", "qwen-2-72b", "glm-4.5"]
        if model_name in short_names:
            return model_name
        
        # Try to extract from provider prefix
        if "/" in model_name:
            _, short_name = model_name.split("/", 1)
            return short_name
        
        return model_name
    
    def reload_configs(self):
        """Reload configurations from file"""
        self.configs = self._load_configs()
        logger.info(f"Reloaded {len(self.configs)} agent configurations")
        return self.configs
    
    def update_agent_config(self, agent_name: str, config: Dict[str, Any]):
        """Update configuration for an agent"""
        self.configs[agent_name] = config
        self._save_configs()
        # Also reload to ensure consistency
        self.reload_configs()
    
    def _save_configs(self):
        """Save configurations to file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.configs, f, indent=2)
            logger.info(f"Saved agent configurations to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving configs: {e}")

# Global instance
agent_model_manager = AgentModelManager()