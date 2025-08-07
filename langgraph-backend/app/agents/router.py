"""Intelligent Router Agent for routing requests to appropriate specialist agents"""

from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage
import json
import logging
import os

logger = logging.getLogger(__name__)

class RouterAgent:
    """Intelligent router that uses LLM to determine the best agent for each request"""
    
    def __init__(self, available_agents: Dict[str, Any]):
        self.name = "router"
        self.description = "Intelligently routes requests to the most appropriate specialist agent"
        self.available_agents = available_agents
        # Use LLM factory to get GPT-5-mini for routing
        from app.config.llm_factory import llm_factory
        self.model = llm_factory.create_llm(
            model_name="gpt-5-mini",
            temperature=0.0,
            max_tokens=1024
        )
        
    def _get_routing_prompt(self) -> str:
        """Generate routing prompt with available agents"""
        
        agent_descriptions = []
        for name, agent in self.available_agents.items():
            if name != "general":  # Skip general agent in descriptions
                agent_descriptions.append(f"- {name}: {agent.description}")
        
        return f"""You are an intelligent router for a coffee e-commerce assistant system.
Your job is to analyze user requests and route them to the most appropriate specialist agent.

Available specialist agents:
{chr(10).join(agent_descriptions)}

- general: For greetings, general questions, and conversations not handled by specialists

IMPORTANT ROUTING RULES:
1. For READING/QUERYING product information (price, details, SKU lookup): Route to 'products'
2. For UPDATING/CHANGING prices, costs, or margins: Route to 'pricing'  
3. For sales data, revenue reports, order analytics: Route to 'orders'
4. For MAP/promotional sales management: Route to 'sales'
5. For inventory levels, stock management: Route to 'inventory'
6. For product features, metafields, descriptions: Route to 'features'
7. For images and media: Route to 'media'
8. For system integrations: Route to 'integrations'
9. For complex product creation, variants: Route to 'product_management'
10. For utility operations: Route to 'utility'
11. For GraphQL queries: Route to 'graphql'
12. For greetings or unclear requests: Route to 'general'

Analyze the user's intent carefully. Look for:
- Action verbs (get, show, find, update, change, set, create)
- Object types (price, product, SKU, inventory, order, sale)
- Context clues about reading vs writing

Return ONLY a JSON object with the agent name and reasoning:
{{"agent": "agent_name", "reason": "Brief explanation"}}"""

    def route(self, user_message: str) -> Dict[str, str]:
        """Route a user message to the appropriate agent"""
        
        logger.info(f"🔀 Router analyzing message: {user_message[:100]}...")
        
        try:
            routing_prompt = self._get_routing_prompt()
            
            response = self.model.invoke([
                {"role": "system", "content": routing_prompt},
                {"role": "user", "content": f"Route this request: {user_message}"}
            ])
            
            # Parse the response
            content = response.content
            if isinstance(content, list):
                content = content[0].text if content else ""
            
            # Extract JSON from response
            try:
                # Try to parse the entire response as JSON first
                result = json.loads(content)
            except json.JSONDecodeError:
                # If that fails, look for JSON in the response
                import re
                json_match = re.search(r'\{[^}]+\}', content)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    # Fallback to general agent
                    logger.warning(f"Could not parse routing response: {content}")
                    result = {"agent": "general", "reason": "Failed to parse routing"}
            
            agent_name = result.get("agent", "general")
            reason = result.get("reason", "")
            
            # Validate agent exists
            if agent_name not in self.available_agents:
                logger.warning(f"Router selected unknown agent: {agent_name}")
                agent_name = "general"
                reason = f"Unknown agent selected, falling back to general"
            
            logger.info(f"✅ Routing decision: {agent_name} - {reason}")
            return {"agent": agent_name, "reason": reason}
            
        except Exception as e:
            logger.error(f"Error in routing: {e}")
            return {"agent": "general", "reason": f"Routing error: {str(e)}"}