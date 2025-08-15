"""
Utility Agent using native LangChain MCP support with MultiServerMCPClient
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import logging
import os
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

# Import the model manager
from app.config.agent_model_manager import agent_model_manager

# Import context mixin for A2A context handling
from app.agents.base_context_mixin import ContextAwareMixin

class UtilityAgentNativeMCP(ContextAwareMixin):
    """Utility agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "utility"
        self.description = "Handles utility functions, memory, and research tasks"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")

        self.client = None
        self.tools = None
        self.agent = None
        self.system_prompt = self._get_system_prompt()
        
    async def _ensure_mcp_connected(self):
        """Ensure MCP client and agent are initialized"""
        if not self.agent:
            try:
                # Initialize MultiServerMCPClient with utility server
                self.client = MultiServerMCPClient({
                    "utility": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-utility-server.py"))],
                        "transport": "stdio",
                        "env": {
                            **os.environ,
                            "PYTHONPATH": "/home/pranav/espressobot/frontend/python-tools"
                        }
                    }
                })
                
                # Get tools from client
                self.tools = await self.client.get_tools()
                
                # Create react agent with tools
                self.agent = create_react_agent(
                    self.model,
                    self.tools,
                    prompt=self.system_prompt
                )
                
                logger.info(f"Connected to Utility MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a Utility specialist agent with expertise in memory management, research, and helper functions.

You have access to utility tools through the MCP server. Use these tools for memory operations, 
research tasks, and various helper functions.

Available tools include:
- memory_operations: Search, add, manage memories in local memory system
- perplexity_research: Research products, competitors, and industry information

## Your Expertise:
- Memory system management
- Semantic search in memories
- Research and information gathering
- Competitive analysis
- Industry trends and insights

## Memory System:
- Operations: search, add, list, delete
- User-isolated memories
- Semantic search via embeddings
- Automatic deduplication
- SQLite local storage

## Memory Use Cases:
- Store important facts about products/customers
- Remember past conversations and decisions
- Build context for future interactions
- Track business rules and patterns

## Research Capabilities:
- Product specifications and reviews
- Competitor pricing and features
- Industry trends and news
- Technical specifications
- Market analysis
- Real-time web data with citations

## Research Models:
- sonar: Fast, efficient searches
- sonar-pro: Detailed, comprehensive research

## Best Practices:
- Add memories for important decisions
- Search memories before making recommendations
- Use research for competitive pricing
- Verify information with multiple sources
- Include citations when sharing research

Always provide clear, formatted responses with relevant information from memories or research."""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state and return updated state"""
        try:
            await self._ensure_mcp_connected()
            
            messages = state.get("messages", [])
            
            if not messages:
                return state
            
            # Get last user message
            last_message = messages[-1]
            if not isinstance(last_message, HumanMessage):
                return state
            
            # Use context-aware messages from the mixin
            context_aware_messages = self.build_context_aware_messages(state, self.system_prompt)
            
            # Use the agent to process the request with context
            agent_state = {"messages": context_aware_messages}
            
            # Run the agent
            logger.info(f"🚀 Running Utility agent with context-aware prompt with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Utility agent completed")
            
            # Extract the response
            if result.get("messages"):
                # Get the last AI message from the agent's response
                agent_messages = result["messages"]
                for msg in reversed(agent_messages):
                    if hasattr(msg, 'content') and msg.content:
                        state["messages"].append(AIMessage(
                            content=msg.content,
                            metadata={"agent": self.name, "intermediate": True}
                        ))
                        break
            else:
                state["messages"].append(AIMessage(
                    content="I processed your request but couldn't generate a response.",
                    metadata={"agent": self.name, "intermediate": True}
                ))
            
            state["last_agent"] = self.name
            return state
            
        except Exception as e:
            logger.error(f"Error in UtilityAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in utility agent: {str(e)}",
                metadata={"agent": self.name, "intermediate": True, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["memory", "remember", "recall", "research", "perplexity", 
                   "competitor", "industry", "trend", "analysis", "search memory",
                   "add memory", "what do you know", "competitive analysis"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)