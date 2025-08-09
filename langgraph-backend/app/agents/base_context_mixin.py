"""
Base context mixin for agents to handle orchestrator-provided context
"""
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import logging

logger = logging.getLogger(__name__)

class ContextAwareMixin:
    """Mixin to handle context passed from orchestrator via A2A"""
    
    def get_context_from_state(self, state: Dict[str, Any]) -> tuple[str, str]:
        """
        Extract context from state - either orchestrator-provided or build from history
        
        Returns:
            tuple: (conversation_context, entity_context)
        """
        # Check if orchestrator passed context (A2A context)
        agent_context = state.get("agent_context", {})
        
        if agent_context:
            # Use orchestrator-provided context
            conversation_context = agent_context.get("conversation_summary", "")
            key_entities = agent_context.get("key_entities", {})
            
            # Build entity context
            entity_parts = []
            if key_entities.get("people"):
                entity_parts.append(f"People mentioned: {', '.join(set(key_entities['people']))}")
            if key_entities.get("references"):
                entity_parts.append(f"References: {', '.join(set(key_entities['references']))}")
            if key_entities.get("topics"):
                entity_parts.append(f"Topics: {', '.join(set(key_entities['topics']))}")
            if key_entities.get("products"):
                entity_parts.append(f"Products: {', '.join(set(key_entities['products']))}")
            
            entity_context = "\n".join(entity_parts) if entity_parts else ""
            
            logger.info(f"📋 Using orchestrator-provided context: {len(conversation_context)} chars")
            return conversation_context, entity_context
        else:
            # Fallback: Build context from conversation history
            messages = state.get("messages", [])
            context_messages = []
            
            for msg in messages[-10:]:  # Include last 10 messages for context
                if isinstance(msg, HumanMessage):
                    context_messages.append(f"User: {msg.content[:200]}")
                elif isinstance(msg, AIMessage):
                    # Skip error messages
                    if not msg.metadata.get("error"):
                        context_messages.append(f"Assistant: {msg.content[:200]}")
            
            conversation_context = "\n".join(context_messages[-6:])  # Last 3 exchanges
            logger.info(f"📋 Building context from message history")
            return conversation_context, ""
    
    def build_context_aware_prompt(self, base_prompt: str, state: Dict[str, Any]) -> str:
        """
        Build an enhanced prompt with conversation context
        
        Args:
            base_prompt: The agent's base system prompt
            state: The current graph state
            
        Returns:
            Enhanced prompt with context
        """
        conversation_context, entity_context = self.get_context_from_state(state)
        
        enhanced_prompt = f"""{base_prompt}

## Recent Conversation Context:
{conversation_context}

{f'## Key Information:' if entity_context else ''}
{entity_context}

## Current Request:
Please help with the user's current request based on the above context."""
        
        return enhanced_prompt
    
    def build_context_aware_messages(self, state: Dict[str, Any], system_prompt: str) -> List:
        """
        Build message list with context-aware system prompt
        
        Args:
            state: The current graph state
            system_prompt: The agent's system prompt
            
        Returns:
            List of messages with context
        """
        messages = state.get("messages", [])
        enhanced_prompt = self.build_context_aware_prompt(system_prompt, state)
        
        # Return messages with enhanced system prompt
        return [
            SystemMessage(content=enhanced_prompt),
            *messages[-8:],  # Include recent message history
        ]