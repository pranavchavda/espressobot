"""
General conversation agent for handling greetings and non-specific queries
"""
from typing import Dict, Any
from langchain_core.messages import AIMessage, HumanMessage
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

class GeneralAgent:
    """Agent for general conversation and greetings"""
    
    def __init__(self):
        self.name = "general"
        self.description = "Handles general conversation, greetings, and queries that don't fit other agents"
        # Use LLM factory to get GPT-5 model for general conversation
        from app.config.llm_factory import llm_factory
        self.model = llm_factory.create_llm(
            model_name="gpt-5-nano",
            temperature=0.3,
            max_tokens=1024
        )
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        return """You are EspressoBot, a helpful assistant powered by GPT-5-nano by OpenAI for iDrinkCoffee.com. You help customers with their coffee-related needs.

When greeting users:
- Be friendly and welcoming
- Remember their name if they tell you
- Ask how you can help them today

You work alongside specialized agents for specific tasks:
- Products: For product searches and information
- Pricing: For price updates and discounts
- Inventory: For stock management
- Sales: For sales and promotions
- And others for various specialized tasks

If the user asks about something specific (products, prices, inventory, etc.), let them know you can help with that.
For general conversation, be helpful and guide them toward what you can assist with.

If asked about what model you are, respond that you're powered by GPT-5-nano by OpenAI.

Keep responses concise and friendly."""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state and return updated state"""
        try:
            messages = state.get("messages", [])
            
            if not messages:
                return state
            
            # Get last user message
            last_message = messages[-1]
            if not isinstance(last_message, HumanMessage):
                return state
            
            # Prepare full conversation history for the model
            conversation = [{"role": "system", "content": self.system_prompt}]
            
            # Add all previous messages to maintain context
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    conversation.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    conversation.append({"role": "assistant", "content": msg.content})
            
            # Get response from model with full context using timeout
            try:
                # Add timeout to prevent hanging (30 seconds)
                response = await asyncio.wait_for(
                    self.model.ainvoke(conversation),
                    timeout=30.0
                )
                
                # Ensure we have content
                if not hasattr(response, 'content') or not response.content:
                    raise ValueError("Empty response from model")
                    
                # Add response to state
                state["messages"].append(AIMessage(
                    content=response.content,
                    metadata={"agent": self.name}
                ))
            except asyncio.TimeoutError:
                logger.error("GeneralAgent: Model invocation timed out after 30 seconds")
                # Provide a fallback response for timeout
                state["messages"].append(AIMessage(
                    content="Hello! I'm EspressoBot, powered by GPT-5-nano by OpenAI. I'm here to help you with your coffee needs. How can I assist you today?",
                    metadata={"agent": self.name, "timeout": True}
                ))
            except Exception as model_error:
                logger.error(f"Model invocation error in GeneralAgent: {model_error}")
                # Provide a fallback response
                state["messages"].append(AIMessage(
                    content="Hello! I'm EspressoBot, powered by GPT-5-nano by OpenAI. I'm here to help you with your coffee needs. How can I assist you today?",
                    metadata={"agent": self.name, "fallback": True}
                ))
                # Don't re-raise; we've handled it with fallback
            
            state["last_agent"] = self.name
            return state
            
        except Exception as e:
            logger.error(f"Error in GeneralAgent: {e}")
            # Provide a helpful fallback response that identifies the bot correctly
            fallback_content = (
                "Hello! I'm EspressoBot, powered by GPT-5-nano by OpenAI. "
                "I help customers with coffee-related needs at iDrinkCoffee.com. "
                "I can assist you with products, pricing, inventory, and general questions. "
                "How can I help you today?"
            )
            state["messages"].append(AIMessage(
                content=fallback_content,
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        message_lower = last_message.content.lower()
        
        # Handle greetings and general conversation
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", 
                     "good evening", "greetings", "howdy"]
        
        general_queries = ["help", "what can you do", "who are you", "your name",
                          "ok", "okay", "thanks", "thank you", "bye", "goodbye",
                          "yes", "no", "sure", "please"]
        
        # Check if it's a greeting or general query
        for greeting in greetings:
            if greeting in message_lower:
                return True
        
        for query in general_queries:
            if query in message_lower:
                return True
        
        # Also handle when user introduces themselves
        if "my name is" in message_lower or "i am" in message_lower or "i'm" in message_lower:
            return True
        
        # This agent has lowest priority - only handles if no other agent claims it
        # But we'll let the router decide that
        return False