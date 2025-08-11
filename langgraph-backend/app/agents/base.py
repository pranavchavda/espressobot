from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import logging
import os
from langsmith.run_helpers import traceable

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base agent class for all specialist agents"""
    
    def __init__(
        self,
        name: str,
        description: str,
        model: str = None,  # Deprecated, will use agent-specific model from config
        temperature: float = 0.0
    ):
        self.name = name
        self.description = description
        
        # Use Agent Model Manager for proper parameter handling
        from app.config.agent_model_manager import AgentModelManager
        try:
            agent_model_manager = AgentModelManager()
            self.model = agent_model_manager.get_model_for_agent(self.name)
            logger.info(f"Initialized {self.name} agent with model via AgentModelManager")
        except Exception as e:
            logger.warning(f"Failed to create model for {self.name} via AgentModelManager, falling back: {e}")
            # Fallback to direct factory call with safe parameters
            from app.config.llm_factory import llm_factory, Provider
            # Use Claude as safe fallback (no GPT-5 parameter issues)
            from langchain_anthropic import ChatAnthropic
            self.model = ChatAnthropic(
                model="claude-3-5-haiku-20241022",
                temperature=temperature,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
        
        self.tools: List[Any] = []
        self.system_prompt = self._get_system_prompt()
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Return the system prompt for this agent"""
        pass
    
    @abstractmethod
    def _get_tools(self) -> List[Any]:
        """Return the tools available to this agent"""
        pass
    
    @traceable(name="agent_call", run_type="chain")
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the current state and return updated state"""
        try:
            messages = state.get("messages", [])
            
            if not messages:
                return state
            
            response = await self._process_messages(messages)
            
            state["messages"].append(response)
            state["last_agent"] = self.name
            
            return state
            
        except Exception as e:
            logger.error(f"Error in {self.name}: {str(e)}")
            error_message = AIMessage(
                content=f"Error in {self.name}: {str(e)}",
                metadata={"agent": self.name, "error": True}
            )
            state["messages"].append(error_message)
            return state
    
    @traceable(name="agent_process_messages", run_type="llm")
    async def _process_messages(self, messages: List[BaseMessage]) -> AIMessage:
        
        formatted_messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted_messages.append({"role": "assistant", "content": msg.content})
        
        if self.tools:
            response = await self.model.ainvoke(
                formatted_messages,
                tools=self.tools
            )
        else:
            response = await self.model.ainvoke(formatted_messages)
        
        return AIMessage(
            content=response.content,
            metadata={"agent": self.name}
        )
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the current request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = self._get_keywords()
        message_content = last_message.content.lower()
        
        return any(keyword in message_content for keyword in keywords)
    
    @abstractmethod
    def _get_keywords(self) -> List[str]:
        """Return keywords that trigger this agent"""
        pass