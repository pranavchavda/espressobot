"""
Thinking service implementation for structured reasoning.
Replaces the SequentialThinkingMCPServer with a direct implementation.
"""
import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
import logging
import openai

from services.base_service import BaseService, ServiceError
from services.config import service_config

class ThinkingServiceError(ServiceError):
    """Exception raised for thinking service errors."""
    pass

class ThinkingService(BaseService):
    """
    Direct implementation of thinking service functionality.
    Provides structured reasoning without MCP overhead.
    """
    def __init__(self):
        """Initialize the thinking service."""
        super().__init__("thinking")
        
        # Get API key from config
        self.api_key = service_config.get("openai", "api_key", os.environ.get("OPENAI_API_KEY", ""))
        
        # Set preferred model (using gpt-4.1-mini or gpt-4.1 as recommended)
        self.model = service_config.get("thinking", "model", "gpt-4.1-mini")
        
        # Maximum steps for thinking
        self.default_max_steps = service_config.get("thinking", "max_steps", 5)
        
        # Configure OpenAI client
        openai.api_key = self.api_key
    
    async def think(self, prompt: str, thinking_type: str = "general", max_steps: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform step-by-step thinking on a prompt.
        
        Args:
            prompt: The prompt to think about
            thinking_type: Type of thinking (general, problem, code)
            max_steps: Maximum number of thinking steps
            
        Returns:
            Thinking steps and conclusion
        """
        try:
            # Validate API key
            if not self.api_key:
                raise ThinkingServiceError("Missing OpenAI API key")
            
            # Set max steps
            max_steps = max_steps or self.default_max_steps
            
            # Create system message based on thinking type
            if thinking_type == "problem":
                system_message = "You are an expert problem solver. Break down the problem step by step, analyze it thoroughly, and provide a clear solution."
            elif thinking_type == "code":
                system_message = "You are an expert programmer. Think through the coding task step by step, plan your approach, and provide a detailed implementation strategy."
            else:  # general
                system_message = "You are a thoughtful assistant. Think through the prompt step by step, considering different aspects and providing a well-reasoned response."
            
            # Create messages for the API call
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Think through the following step by step (maximum {max_steps} steps):\n\n{prompt}"}
            ]
            
            # Call OpenAI API using the Responses API approach
            try:
                # Try using the Responses API if available
                response = await openai.responses.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                thinking_content = response.content
            except (AttributeError, ImportError):
                # Fall back to ChatCompletion if Responses API is not available
                response = await openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=2000,
                    temperature=0.7
                )
                thinking_content = response.choices[0].message.content
            
            # Parse thinking steps
            steps = self._parse_thinking_steps(thinking_content)
            
            return {
                "success": True,
                "thinking_type": thinking_type,
                "steps": steps,
                "conclusion": steps[-1] if steps else "",
                "raw_thinking": thinking_content
            }
        except Exception as e:
            raise ThinkingServiceError(f"Failed to perform thinking: {str(e)}")
    
    async def solve_problem(self, problem: str, max_steps: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform problem-solving thinking.
        
        Args:
            problem: The problem to solve
            max_steps: Maximum number of thinking steps
            
        Returns:
            Problem-solving steps and solution
        """
        return await self.think(problem, thinking_type="problem", max_steps=max_steps)
    
    async def plan_code(self, coding_task: str, max_steps: Optional[int] = None) -> Dict[str, Any]:
        """
        Perform code planning thinking.
        
        Args:
            coding_task: The coding task to plan
            max_steps: Maximum number of thinking steps
            
        Returns:
            Code planning steps and implementation strategy
        """
        return await self.think(coding_task, thinking_type="code", max_steps=max_steps)
    
    def _parse_thinking_steps(self, thinking_content: str) -> List[str]:
        """
        Parse thinking steps from the raw thinking content.
        
        Args:
            thinking_content: Raw thinking content from the API
            
        Returns:
            List of thinking steps
        """
        # Split by numbered steps (1., 2., etc.) or Step 1:, Step 2:, etc.
        import re
        
        # Try to find numbered steps with different formats
        step_patterns = [
            r'\b(\d+)\.\s+(.*?)(?=\b\d+\.\s+|\Z)',  # 1. Step content
            r'Step\s+(\d+):\s+(.*?)(?=Step\s+\d+:|\Z)',  # Step 1: Step content
            r'Step\s+(\d+)\s+(.*?)(?=Step\s+\d+\s+|\Z)'  # Step 1 Step content
        ]
        
        for pattern in step_patterns:
            matches = re.findall(pattern, thinking_content, re.DOTALL)
            if matches:
                # Sort by step number and extract content
                steps = [content.strip() for _, content in sorted(matches, key=lambda x: int(x[0]))]
                if steps:
                    return steps
        
        # If no structured steps found, split by paragraphs
        paragraphs = [p.strip() for p in thinking_content.split('\n\n') if p.strip()]
        if paragraphs:
            return paragraphs
        
        # Fallback: return the whole content as a single step
        return [thinking_content.strip()]

# Create a singleton instance
thinking_service = ThinkingService()
