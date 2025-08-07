from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any, List, Optional
import logging
import os
from app.state.graph_state import GraphState
from app.agents.base import BaseAgent
from app.agents.router import RouterAgent
from app.memory.memory_config import MemoryConfig
from langchain_core.messages import AIMessage
import asyncio

logger = logging.getLogger(__name__)

class Orchestrator:
    """Main orchestrator for routing and managing agent interactions"""
    
    def __init__(self, checkpointer = None):
        self.agents: Dict[str, BaseAgent] = {}
        # Use configured checkpointer for persistent memory
        if not checkpointer:
            memory_config = MemoryConfig()
            self.checkpointer = memory_config.get_checkpointer()
            self.memory_config = memory_config
        else:
            self.checkpointer = checkpointer
            self.memory_config = MemoryConfig()
        self.graph = None
        self.router = None
        self._initialize_agents()
        self._build_graph()
    
    def _initialize_agents(self):
        """Initialize all specialist agents"""
        # Use MCP-enabled agents
        from app.agents.products_native_mcp_final import ProductsAgentNativeMCPFinal
        from app.agents.pricing_native_mcp import PricingAgentNativeMCP
        from app.agents.inventory_native_mcp import InventoryAgentNativeMCP
        from app.agents.sales_native_mcp import SalesAgentNativeMCP
        from app.agents.features_native_mcp import FeaturesAgentNativeMCP
        from app.agents.media_native_mcp import MediaAgentNativeMCP
        from app.agents.integrations_native_mcp import IntegrationsAgentNativeMCP
        from app.agents.product_mgmt_native_mcp import ProductManagementAgentNativeMCP
        from app.agents.utility_native_mcp import UtilityAgentNativeMCP
        from app.agents.graphql_native_mcp import GraphQLAgentNativeMCP
        from app.agents.orders_native_mcp import OrdersAgentNativeMCP
        from app.agents.google_workspace_native_mcp import GoogleWorkspaceAgentNativeMCP
        from app.agents.ga4_analytics_native_mcp import GA4AnalyticsAgentNativeMCP
        from app.agents.general import GeneralAgent
        
        # Initialize general agent first (for greetings and general chat)
        try:
            general_agent = GeneralAgent()
            self.agents[general_agent.name] = general_agent
            logger.info(f"Initialized General conversation agent")
        except Exception as e:
            logger.error(f"Failed to initialize GeneralAgent: {e}")
        
        # Use the native MCP version for products
        try:
            products_agent = ProductsAgentNativeMCPFinal()
            self.agents[products_agent.name] = products_agent
            logger.info(f"Initialized native MCP Products agent (final)")
        except Exception as e:
            logger.error(f"Failed to initialize ProductsAgentNativeMCPFinal: {e}")
        
        # Use the native MCP version for pricing
        try:
            pricing_agent = PricingAgentNativeMCP()
            self.agents[pricing_agent.name] = pricing_agent
            logger.info(f"Initialized native MCP Pricing agent")
        except Exception as e:
            logger.error(f"Failed to initialize PricingAgentNativeMCP: {e}")
        
        # Use the native MCP version for inventory
        try:
            inventory_agent = InventoryAgentNativeMCP()
            self.agents[inventory_agent.name] = inventory_agent
            logger.info(f"Initialized native MCP Inventory agent")
        except Exception as e:
            logger.error(f"Failed to initialize InventoryAgentNativeMCP: {e}")
        
        # Use the native MCP version for sales
        try:
            sales_agent = SalesAgentNativeMCP()
            self.agents[sales_agent.name] = sales_agent
            logger.info(f"Initialized native MCP Sales agent")
        except Exception as e:
            logger.error(f"Failed to initialize SalesAgentNativeMCP: {e}")
        
        # Use the native MCP version for features
        try:
            features_agent = FeaturesAgentNativeMCP()
            self.agents[features_agent.name] = features_agent
            logger.info(f"Initialized native MCP Features agent")
        except Exception as e:
            logger.error(f"Failed to initialize FeaturesAgentNativeMCP: {e}")
        
        # Use the native MCP version for media
        try:
            media_agent = MediaAgentNativeMCP()
            self.agents[media_agent.name] = media_agent
            logger.info(f"Initialized native MCP Media agent")
        except Exception as e:
            logger.error(f"Failed to initialize MediaAgentNativeMCP: {e}")
        
        # Use the native MCP version for integrations
        try:
            integrations_agent = IntegrationsAgentNativeMCP()
            self.agents[integrations_agent.name] = integrations_agent
            logger.info(f"Initialized native MCP Integrations agent")
        except Exception as e:
            logger.error(f"Failed to initialize IntegrationsAgentNativeMCP: {e}")
        
        # Use the native MCP version for product management
        try:
            product_mgmt_agent = ProductManagementAgentNativeMCP()
            self.agents[product_mgmt_agent.name] = product_mgmt_agent
            logger.info(f"Initialized native MCP Product Management agent")
        except Exception as e:
            logger.error(f"Failed to initialize ProductManagementAgentNativeMCP: {e}")
        
        # Use the native MCP version for utility
        try:
            utility_agent = UtilityAgentNativeMCP()
            self.agents[utility_agent.name] = utility_agent
            logger.info(f"Initialized native MCP Utility agent")
        except Exception as e:
            logger.error(f"Failed to initialize UtilityAgentNativeMCP: {e}")
        
        # Use the native MCP version for GraphQL
        try:
            graphql_agent = GraphQLAgentNativeMCP()
            self.agents[graphql_agent.name] = graphql_agent
            logger.info(f"Initialized native MCP GraphQL agent")
        except Exception as e:
            logger.error(f"Failed to initialize GraphQLAgentNativeMCP: {e}")
        
        # Use the native MCP version for Orders
        try:
            orders_agent = OrdersAgentNativeMCP()
            self.agents[orders_agent.name] = orders_agent
            logger.info(f"Initialized native MCP Orders agent")
        except Exception as e:
            logger.error(f"Failed to initialize OrdersAgentNativeMCP: {e}")
        
        # Use the native version for Google Workspace
        try:
            google_workspace_agent = GoogleWorkspaceAgentNativeMCP()
            self.agents[google_workspace_agent.name] = google_workspace_agent
            logger.info(f"Initialized native Google Workspace agent")
        except Exception as e:
            logger.error(f"Failed to initialize GoogleWorkspaceAgentNativeMCP: {e}")
        
        # Use the native version for GA4 Analytics
        try:
            ga4_agent = GA4AnalyticsAgentNativeMCP()
            self.agents[ga4_agent.name] = ga4_agent
            logger.info(f"Initialized native GA4 Analytics agent")
        except Exception as e:
            logger.error(f"Failed to initialize GA4AnalyticsAgentNativeMCP: {e}")
        
        # Price Monitor will be implemented as API proxy later
        # (Frontend already has working price monitor API)
        
        # Initialize the intelligent router with available agents
        self.router = RouterAgent(self.agents)
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(GraphState)
        
        workflow.add_node("router", self.route_request)
        
        # Create synchronous wrappers for async agents
        def make_sync_wrapper(agent_callable):
            """Create a synchronous wrapper for async agent callables"""
            import asyncio
            import concurrent.futures
            
            def sync_wrapper(state):
                # Run the async function in a new event loop in a thread pool
                # This avoids conflicts with uvloop
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, agent_callable(state))
                    return future.result()
            
            return sync_wrapper
        
        for agent_name, agent in self.agents.items():
            # Wrap async agents in sync wrapper
            workflow.add_node(agent_name, make_sync_wrapper(agent))
        
        workflow.add_conditional_edges(
            "router",
            self.determine_next_agent,
            {
                **{agent_name: agent_name for agent_name in self.agents.keys()},
                "end": END
            }
        )
        
        for agent_name in self.agents.keys():
            workflow.add_edge(agent_name, END)
        
        workflow.set_entry_point("router")
        
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        logger.info("Graph compiled successfully")
    
    def route_request(self, state: GraphState) -> GraphState:
        """Route the request to the appropriate agent"""
        try:
            # Trim message history to manage tokens
            if state["messages"] and len(state["messages"]) > self.memory_config.max_history_length:
                state["messages"] = self.memory_config.trim_messages(state["messages"])
                logger.info(f"Trimmed message history to {len(state['messages'])} messages")
            
            last_message = state["messages"][-1] if state["messages"] else None
            
            if not last_message:
                state["error"] = "No message to process"
                state["should_continue"] = False
                return state
            
            logger.info(f"Routing request: {last_message.content[:100]}...")
            
            # Use intelligent router to determine the best agent
            routing_decision = self.router.route(last_message.content)
            agent_name = routing_decision["agent"]
            reason = routing_decision["reason"]
            
            if agent_name in self.agents:
                state["current_agent"] = agent_name
                logger.info(f"Intelligent routing to agent: {agent_name} - Reason: {reason}")
                return state
            else:
                # Fallback to general agent if router returns invalid agent
                if "general" in self.agents:
                    state["current_agent"] = "general"
                    logger.info(f"Fallback routing to general agent")
                    return state
            
            # Fallback if general agent not available
            state["messages"].append(
                AIMessage(
                    content="I'm here to help! How can I assist you with your coffee needs today?",
                    metadata={"agent": "router"}
                )
            )
            state["should_continue"] = False
            
            return state
            
        except Exception as e:
            logger.error(f"Error in router: {e}")
            state["error"] = str(e)
            state["should_continue"] = False
            return state
    
    def determine_next_agent(self, state: GraphState) -> str:
        """Determine the next node based on current state"""
        
        if state.get("error") or not state.get("should_continue", True):
            return "end"
        
        current_agent = state.get("current_agent")
        
        if current_agent and current_agent in self.agents:
            return current_agent
        
        return "end"
    
    async def run(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the orchestrator with a user message"""
        
        from app.state.graph_state import create_initial_state
        from langchain_core.messages import HumanMessage
        
        actual_thread_id = thread_id or conversation_id or "default"
        config = {"configurable": {"thread_id": actual_thread_id}}
        logger.info(f"Stream: Using thread_id: {actual_thread_id}")
        
        # Check if there's an existing checkpoint for this thread
        existing_state = None
        try:
            existing_state = self.checkpointer.get(config)
        except Exception as e:
            logger.debug(f"No existing checkpoint for thread {actual_thread_id}: {e}")
        
        if existing_state and "channel_values" in existing_state:
            # Use existing state and append new message
            initial_state = existing_state["channel_values"]
            # Ensure messages is a list
            if "messages" not in initial_state:
                initial_state["messages"] = []
            logger.info(f"Found existing state with {len(initial_state.get('messages', []))} messages")
            # Append the new user message
            initial_state["messages"].append(HumanMessage(content=message))
            # Update context if provided
            if context:
                initial_state["context"] = context
        else:
            # No existing state, create new one
            logger.info(f"No existing state found for thread {actual_thread_id}, creating new state")
            initial_state = create_initial_state(
                user_message=message,
                conversation_id=conversation_id,
                user_id=user_id,
                context=context
            )
        
        try:
            result = await self.graph.ainvoke(initial_state, config)
            
            return {
                "success": True,
                "messages": result.get("messages", []),
                "last_agent": result.get("last_agent"),
                "metadata": result.get("metadata", {})
            }
        except Exception as e:
            logger.error(f"Error running orchestrator: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": []
            }
    
    async def stream(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        thread_id: Optional[str] = None
    ):
        """Stream the orchestrator response"""
        
        from app.state.graph_state import create_initial_state
        from langchain_core.messages import HumanMessage
        import asyncio
        
        actual_thread_id = thread_id or conversation_id or "default"
        config = {"configurable": {"thread_id": actual_thread_id}}
        logger.info(f"Stream: Using thread_id: {actual_thread_id}")
        
        # Check if there's an existing checkpoint for this thread
        existing_state = None
        try:
            existing_state = self.checkpointer.get(config)
        except Exception as e:
            logger.debug(f"No existing checkpoint for thread {actual_thread_id}: {e}")
        
        if existing_state and "channel_values" in existing_state:
            # Use existing state and append new message
            initial_state = existing_state["channel_values"]
            # Ensure messages is a list
            if "messages" not in initial_state:
                initial_state["messages"] = []
            logger.info(f"Found existing state with {len(initial_state.get('messages', []))} messages")
            # Append the new user message
            initial_state["messages"].append(HumanMessage(content=message))
            # Update context if provided
            if context:
                initial_state["context"] = context
        else:
            # No existing state, create new one
            logger.info(f"No existing state found for thread {actual_thread_id}, creating new state")
            initial_state = create_initial_state(
                user_message=message,
                conversation_id=conversation_id,
                user_id=user_id,
                context=context
            )
        
        try:
            event_count = 0
            
            # Use the synchronous stream method
            for chunk in self.graph.stream(initial_state, config):
                event_count += 1
                logger.debug(f"Chunk {event_count}: {type(chunk)}, keys: {chunk.keys() if isinstance(chunk, dict) else 'not a dict'}")
                
                # LangGraph returns chunks as {node_name: state_update}
                # Each chunk represents an update from a specific node
                if isinstance(chunk, dict):
                    for node_name, node_output in chunk.items():
                        if isinstance(node_output, dict) and "messages" in node_output:
                            messages = node_output.get("messages", [])
                            if messages:
                                last_message = messages[-1]
                                # Check if it's an AI message (not HumanMessage)
                                from langchain_core.messages import AIMessage
                                if isinstance(last_message, AIMessage):
                                    content = last_message.content
                                    agent = node_name  # Use node name as agent
                                    
                                    # Yield the content as tokens
                                    if content:
                                        yield {
                                            "type": "token",
                                            "content": content,
                                            "agent": agent
                                        }
            
            # Add explicit completion signal
            logger.info(f"Stream completed with {event_count} chunks")
            yield {
                "type": "complete",
                "message": "Stream completed"
            }
            
        except Exception as e:
            import traceback
            error_msg = f"Error streaming response: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")
            yield {
                "type": "error",
                "error": str(e)
            }