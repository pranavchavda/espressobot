"""Simplified orchestrator with working PostgreSQL checkpointing"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from typing import Dict, Any, List, Optional
import logging
import os
from app.state.graph_state import GraphState
from app.agents.base import BaseAgent
from app.agents.router import RouterAgent
from langchain_core.messages import AIMessage, HumanMessage

logger = logging.getLogger(__name__)

class SimpleOrchestrator:
    """Simplified orchestrator with working checkpointing"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.router = None
        self._initialize_agents()
    
    async def _get_graph(self):
        """Create and return graph with async checkpointer context"""
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        # Use the async context manager pattern
        checkpointer_cm = AsyncPostgresSaver.from_conn_string(DATABASE_URL)
        checkpointer = await checkpointer_cm.__aenter__()
        
        try:
            # Setup tables if needed (commented out as per docs pattern)
            # await checkpointer.setup()
            
            workflow = StateGraph(GraphState)
            workflow.add_node("router", self._route_request)
            
            # Add agent nodes - LangGraph handles async agents automatically
            for name, agent in self.agents.items():
                workflow.add_node(name, agent)
            
            # Add edges
            workflow.add_edge(START, "router")
            
            # Add conditional edges from router to agents
            def route_to_agent(state):
                return state.get("next_agent", "general")
            
            workflow.add_conditional_edges(
                "router",
                route_to_agent,
                {name: name for name in self.agents.keys()}
            )
            
            # Add edges from agents to END
            for name in self.agents.keys():
                workflow.add_edge(name, END)
            
            # Compile with checkpointer
            graph = workflow.compile(checkpointer=checkpointer)
            logger.info("Graph compiled successfully with async PostgreSQL checkpointer")
            
            return graph, checkpointer_cm
            
        except Exception:
            await checkpointer_cm.__aexit__(None, None, None)
            raise
    
    def _initialize_agents(self):
        """Initialize all agents"""
        # Import and initialize agents
        from app.agents.general import GeneralAgent
        general_agent = GeneralAgent()
        self.agents[general_agent.name] = general_agent
        logger.info(f"Initialized General conversation agent")
        
        # Initialize other agents (keeping your existing agent initialization code)
        try:
            from app.agents.products_native_mcp_final import ProductsAgentNativeMCPFinal
            products_agent = ProductsAgentNativeMCPFinal()
            self.agents[products_agent.name] = products_agent
            logger.info(f"Initialized native MCP Products agent (final)")
        except Exception as e:
            logger.error(f"Failed to initialize ProductsAgentNativeMCPFinal: {e}")
        
        # Add more agents as needed...
        
        # Initialize router
        self.router = RouterAgent(self.agents)
    
    
    def _route_request(self, state: GraphState) -> GraphState:
        """Route the request to the appropriate agent"""
        messages = state.get("messages", [])
        if not messages:
            state["next_agent"] = "general"
            return state
        
        last_message = messages[-1]
        user_query = last_message.content if hasattr(last_message, 'content') else str(last_message)
        
        # Use router to determine the best agent
        routing_decision = self.router.route(user_query)
        state["next_agent"] = routing_decision["agent"]
        
        logger.info(f"Routing to {routing_decision['agent']}: {routing_decision['reason']}")
        return state
    
    async def run(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the orchestrator"""
        from app.state.graph_state import create_initial_state
        
        initial_state = create_initial_state(
            user_message=message,
            conversation_id=conversation_id,
            user_id=user_id,
            context=context
        )
        
        config = {"configurable": {"thread_id": thread_id or conversation_id or "default"}}
        
        # Get graph with async checkpointer context
        graph, checkpointer_cm = await self._get_graph()
        
        try:
            # Use ainvoke for async agents
            result = await graph.ainvoke(initial_state, config)
            
            return {
                "success": True,
                "messages": result.get("messages", []),
                "last_agent": result.get("last_agent"),
                "metadata": result.get("metadata", {})
            }
            
        except Exception as e:
            logger.error(f"Error running orchestrator: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
                "messages": []
            }
        finally:
            # Clean up the async context manager
            await checkpointer_cm.__aexit__(None, None, None)
    
    async def stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ):
        """Stream the orchestrator response with token-by-token streaming"""
        from app.state.graph_state import create_initial_state
        
        initial_state = create_initial_state(
            user_message=message,
            conversation_id=conversation_id,
            user_id=user_id,
            context=context
        )
        
        config = {"configurable": {"thread_id": thread_id or conversation_id or "default"}}
        
        # Get graph with async checkpointer context
        graph, checkpointer_cm = await self._get_graph()
        
        try:
            # Use astream with messages mode for token-by-token streaming
            async for message_chunk, metadata in graph.astream(initial_state, config, stream_mode="messages"):
                # Process LLM tokens as they arrive
                if message_chunk.content:
                    agent = metadata.get("langgraph_node", "unknown")
                    
                    # Filter out router and other internal nodes - only stream actual agent responses
                    if agent not in ["router", "unknown"]:
                        yield {
                            "type": "token",
                            "content": message_chunk.content,
                            "agent": agent
                        }
            
            yield {
                "type": "complete",
                "message": "Stream completed"
            }
            
        except Exception as e:
            import traceback
            logger.error(f"Error streaming response: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            yield {
                "type": "error",
                "error": str(e)
            }
        finally:
            # Clean up the async context manager
            await checkpointer_cm.__aexit__(None, None, None)