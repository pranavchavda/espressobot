"""
Configuration service for unified service configuration management.
Provides a centralized way to manage configuration for all services.
"""
import os
import json
from typing import Any, Dict, Optional
from dotenv import load_dotenv

class ServiceConfig:
    """
    Unified configuration management for all services.
    Handles loading configuration from environment variables, config files, and defaults.
    """
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration service.
        
        Args:
            config_file: Optional path to a JSON configuration file
        """
        # Load environment variables
        load_dotenv()
        
        # Initialize configuration dictionary
        self.config = {}
        
        # Load from config file if provided
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                self.config = json.load(f)
    
    def get(self, service: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value for a specific service.
        
        Args:
            service: Service name (e.g., 'shopify', 'memory')
            key: Configuration key
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        # Check environment variables first (format: SERVICE_KEY)
        env_key = f"{service.upper()}_{key.upper()}"
        env_value = os.environ.get(env_key)
        if env_value is not None:
            return env_value
            
        # Check config dictionary
        service_config = self.config.get(service, {})
        if key in service_config:
            return service_config[key]
            
        # Return default value
        return default
    
    def set(self, service: str, key: str, value: Any) -> None:
        """
        Set a configuration value for a specific service.
        
        Args:
            service: Service name (e.g., 'shopify', 'memory')
            key: Configuration key
            value: Configuration value
        """
        if service not in self.config:
            self.config[service] = {}
        self.config[service][key] = value
    
    def save(self, config_file: str) -> None:
        """
        Save the current configuration to a file.
        
        Args:
            config_file: Path to save the configuration
        """
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

# Create a singleton instance
service_config = ServiceConfig()
