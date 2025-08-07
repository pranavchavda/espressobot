"""
LLM Factory for creating model instances with multiple provider support
Supports OpenRouter, OpenAI direct, and Anthropic
"""
import os
import logging
from typing import Optional, Dict, Any
from enum import Enum
from langchain_openai import ChatOpenAI

# Conditional imports for optional providers
try:
    from langchain_anthropic import ChatAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    ChatAnthropic = None

logger = logging.getLogger(__name__)

class Provider(Enum):
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

class LLMFactory:
    """Factory for creating LLM instances with fallback support"""
    
    # Model mappings for different providers
    MODEL_MAPPINGS = {
        "gpt-5": {
            Provider.OPENROUTER: "openai/gpt-5",
            Provider.OPENAI: "gpt-5"
        },
        "gpt-5-mini": {
            Provider.OPENROUTER: "openai/gpt-5-mini",
            Provider.OPENAI: "gpt-5-mini"
        },
        "gpt-5-nano": {
            Provider.OPENROUTER: "openai/gpt-5-nano",
            Provider.OPENAI: "gpt-5-nano"
        },
        "gpt-4": {
            Provider.OPENROUTER: "openai/gpt-4-turbo-preview",
            Provider.OPENAI: "gpt-4-turbo-preview"
        },
        "claude-3-opus": {
            Provider.OPENROUTER: "anthropic/claude-3-opus-20240229",
            Provider.ANTHROPIC: "claude-3-opus-20240229"
        },
        "claude-3-5-haiku": {
            Provider.OPENROUTER: "anthropic/claude-3-5-haiku-20241022",
            Provider.ANTHROPIC: "claude-3-5-haiku-20241022"
        },
        "deepseek-chat": {
            Provider.OPENROUTER: "deepseek/deepseek-chat",
            Provider.OPENAI: None  # Not available via OpenAI
        },
        "qwen-2-72b": {
            Provider.OPENROUTER: "qwen/qwen-2-72b-instruct",
            Provider.OPENAI: None  # Not available via OpenAI
        }
    }
    
    def __init__(self):
        # Load API keys
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        # Determine available providers
        self.available_providers = []
        if self.openrouter_key:
            self.available_providers.append(Provider.OPENROUTER)
            logger.info("✅ OpenRouter API configured")
        if self.openai_key:
            self.available_providers.append(Provider.OPENAI)
            logger.info("✅ OpenAI API configured")
        if self.anthropic_key and ANTHROPIC_AVAILABLE:
            self.available_providers.append(Provider.ANTHROPIC)
            logger.info("✅ Anthropic API configured")
        elif self.anthropic_key and not ANTHROPIC_AVAILABLE:
            logger.warning("⚠️ Anthropic API key provided but langchain_anthropic not installed")
    
    def create_llm(
        self,
        model_name: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        preferred_provider: Optional[Provider] = None
    ):
        """
        Create an LLM instance with automatic provider selection and fallback
        
        Args:
            model_name: Generic model name (e.g., "gpt-5", "claude-3-opus")
            temperature: Model temperature
            max_tokens: Maximum tokens to generate
            preferred_provider: Preferred provider to use
        
        Returns:
            LangChain LLM instance
        """
        
        # Get model mapping
        if model_name not in self.MODEL_MAPPINGS:
            logger.warning(f"Unknown model: {model_name}, falling back to GPT-4")
            model_name = "gpt-4"
        
        model_map = self.MODEL_MAPPINGS[model_name]
        
        # Determine provider order
        if preferred_provider and preferred_provider in self.available_providers:
            providers = [preferred_provider] + [p for p in self.available_providers if p != preferred_provider]
        else:
            # Default order: OpenAI direct, then OpenRouter, then Anthropic
            provider_order = [Provider.OPENAI, Provider.OPENROUTER, Provider.ANTHROPIC]
            providers = [p for p in provider_order if p in self.available_providers]
        
        # Try each provider
        for provider in providers:
            try:
                llm = self._create_llm_for_provider(
                    provider, model_map, temperature, max_tokens
                )
                if llm:
                    logger.info(f"Using {model_name} via {provider.value}")
                    return llm
            except Exception as e:
                logger.warning(f"Failed to create {model_name} via {provider.value}: {e}")
                continue
        
        # Ultimate fallback - use GPT-4 if available
        logger.warning(f"All providers failed for {model_name}, using GPT-4 fallback")
        if self.openai_key:
            return ChatOpenAI(
                model="gpt-4-turbo-preview",
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.openai_key,
                timeout=30,
                max_retries=1
            )
        elif self.openrouter_key:
            return ChatOpenAI(
                model="openai/gpt-4-turbo-preview",
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.openrouter_key,
                base_url="https://openrouter.ai/api/v1",
                timeout=30,
                max_retries=1,
                default_headers={
                    "HTTP-Referer": os.getenv("APP_URL", "https://espressobot.com"),
                    "X-Title": "EspressoBot"
                }
            )
        else:
            raise Exception("No available providers for fallback")
    
    def _create_llm_for_provider(
        self,
        provider: Provider,
        model_map: Dict[Provider, str],
        temperature: float,
        max_tokens: int
    ):
        """Create LLM for specific provider"""
        
        model_id = model_map.get(provider)
        if not model_id:
            return None
        
        if provider == Provider.OPENROUTER:
            # GPT-5 models have different parameters
            if "gpt-5" in model_id:
                # GPT-5 uses max_completion_tokens instead of max_tokens
                return ChatOpenAI(
                    model=model_id,
                    api_key=self.openrouter_key,
                    base_url="https://openrouter.ai/api/v1",
                    max_completion_tokens=max_tokens,
                    timeout=30,  # 30 second timeout
                    max_retries=1,  # Reduce retries to prevent hanging
                    default_headers={
                        "HTTP-Referer": os.getenv("APP_URL", "https://espressobot.com"),
                        "X-Title": "EspressoBot"
                    }
                    # No temperature or max_tokens for GPT-5
                )
            else:
                return ChatOpenAI(
                    model=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=self.openrouter_key,
                    base_url="https://openrouter.ai/api/v1",
                    timeout=30,  # 30 second timeout
                    max_retries=1,  # Reduce retries
                    default_headers={
                        "HTTP-Referer": os.getenv("APP_URL", "https://espressobot.com"),
                        "X-Title": "EspressoBot"
                    }
                )
        
        elif provider == Provider.OPENAI:
            # GPT-5 models have different parameters
            if "gpt-5" in model_id:
                # GPT-5 uses max_completion_tokens instead of max_tokens
                # and doesn't support temperature
                return ChatOpenAI(
                    model=model_id,
                    api_key=self.openai_key,
                    max_completion_tokens=max_tokens,
                    timeout=30,  # 30 second timeout
                    max_retries=1  # Reduce retries to prevent hanging
                    # No temperature or max_tokens for GPT-5
                )
            else:
                return ChatOpenAI(
                    model=model_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=self.openai_key,
                    timeout=30,  # 30 second timeout
                    max_retries=1  # Reduce retries
                )
        
        elif provider == Provider.ANTHROPIC:
            if not ANTHROPIC_AVAILABLE:
                logger.error("Anthropic provider requested but langchain_anthropic not available")
                return None
            return ChatAnthropic(
                model=model_id,
                temperature=temperature,
                max_tokens=max_tokens,
                api_key=self.anthropic_key
            )
        
        return None
    
    def test_providers(self):
        """Test all configured providers"""
        results = {}
        
        test_prompt = "Say 'Hello from {provider}' where provider is your model name."
        
        for provider in self.available_providers:
            try:
                # Try GPT-5 or Claude depending on provider
                if provider in [Provider.OPENAI, Provider.OPENROUTER]:
                    model = "gpt-5-mini"
                else:
                    model = "claude-3-5-haiku"
                
                llm = self.create_llm(model, preferred_provider=provider)
                response = llm.invoke(test_prompt)
                results[provider.value] = {
                    "status": "success",
                    "response": response.content[:100] if hasattr(response, 'content') else str(response)[:100]
                }
            except Exception as e:
                results[provider.value] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results

# Global factory instance
llm_factory = LLMFactory()