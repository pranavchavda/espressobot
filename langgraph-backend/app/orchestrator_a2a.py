"""
Agent-to-Agent (A2A) Orchestrator Pattern for LangGraph
Enables agents to collaborate through orchestrated communication
"""
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from typing_extensions import Literal
import logging
import os
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_anthropic import ChatAnthropic
import json
import operator

logger = logging.getLogger(__name__)

class A2AState(TypedDict):
    """Enhanced state for Agent-to-Agent communication"""
    messages: Annotated[List[BaseMessage], operator.add]
    primary_agent: str
    current_agent: str
    agent_requests: List[Dict]  # Requests between agents
    agent_responses: Dict[str, Any]  # Collected responses
    execution_path: List[str]  # Track A2A flow
    context: Dict[str, Any]  # Shared context
    needs_help: bool  # Flag for agent needing assistance
    help_request: Optional[Dict]  # Current help request
    final_response: Optional[str]  # Synthesized response

class A2AOrchestrator:
    """Orchestrator enabling Agent-to-Agent communication patterns"""
    
    def __init__(self, checkpointer=None):
        self.agents = {}
        self._connection_pool = None  # For cleanup
        self.checkpointer = checkpointer or self._create_checkpointer()
        self.graph = None
        self.model = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0.0,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        try:
            self._initialize_agents()
            self._build_graph()
            logger.info("A2A Orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize A2A Orchestrator: {e}")
            raise
    
    def _create_checkpointer(self):
        """Create PostgreSQL checkpointer with proper connection handling"""
        db_uri = os.getenv("DATABASE_URL", "postgresql://espressobot:localdev123@localhost:5432/espressobot_dev")
        try:
            # Create a direct connection for the checkpointer
            import psycopg
            from psycopg.rows import dict_row
            from psycopg_pool import ConnectionPool
            
            # Create connection pool with conservative settings for A2A orchestrator
            pool = ConnectionPool(
                db_uri,
                min_size=1,
                max_size=5,  # Reduced pool size for A2A orchestrator
                max_waiting=0,  # Don't wait for connections
                max_idle=300,  # 5 minute idle timeout
                kwargs={
                    "autocommit": True,
                    "prepare_threshold": 0,
                    "row_factory": dict_row
                }
            )
            
            checkpointer = PostgresSaver(pool)
            
            # Setup the database schema
            try:
                checkpointer.setup()
                logger.info("A2A PostgreSQL checkpointer initialized with schema setup")
            except Exception as setup_error:
                # Schema might already exist
                logger.debug(f"A2A checkpointer schema setup note: {setup_error}")
            
            # Store pool reference for cleanup
            self._connection_pool = pool
            
            return checkpointer
            
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL checkpointer for A2A: {e}")
            # Fallback to in-memory checkpointer
            from langgraph.checkpoint.memory import MemorySaver
            logger.warning("A2A orchestrator falling back to in-memory checkpointer")
            return MemorySaver()
    
    def _initialize_agents(self):
        """Initialize all specialist agents with A2A capabilities"""
        from app.agents.products_native_mcp_final import ProductsAgentNativeMCPFinal
        from app.agents.pricing_native_mcp import PricingAgentNativeMCP
        from app.agents.inventory_native_mcp import InventoryAgentNativeMCP
        from app.agents.sales_native_mcp import SalesAgentNativeMCP
        from app.agents.features_native_mcp import FeaturesAgentNativeMCP
        from app.agents.general import GeneralAgent
        
        # Initialize agents
        agent_classes = [
            ("products", ProductsAgentNativeMCPFinal),
            ("pricing", PricingAgentNativeMCP),
            ("inventory", InventoryAgentNativeMCP),
            ("sales", SalesAgentNativeMCP),
            ("features", FeaturesAgentNativeMCP),
            ("general", GeneralAgent)
        ]
        
        for name, AgentClass in agent_classes:
            try:
                agent = AgentClass()
                self.agents[name] = agent
                logger.info(f"Initialized {name} agent for A2A communication")
            except Exception as e:
                logger.error(f"Failed to initialize {name} agent: {e}")
    
    def _build_graph(self):
        """Build the A2A communication graph"""
        graph = StateGraph(A2AState)
        
        # Add nodes
        graph.add_node("analyze", self.analyze_request)
        graph.add_node("route", self.route_to_primary)
        graph.add_node("execute_agent", self.execute_current_agent)
        graph.add_node("coordinate_help", self.coordinate_help_request)
        graph.add_node("synthesize", self.synthesize_response)
        
        # Define flow
        graph.add_edge(START, "analyze")
        graph.add_edge("analyze", "route")
        
        # After routing, execute the selected agent
        graph.add_edge("route", "execute_agent")
        
        # Agent execution can lead to help request or completion
        graph.add_conditional_edges(
            "execute_agent",
            self.check_agent_needs,
            {
                "needs_help": "coordinate_help",
                "complete": "synthesize"
            }
        )
        
        # After help coordination, return to agent execution
        graph.add_edge("coordinate_help", "execute_agent")
        
        # Synthesize and end
        graph.add_edge("synthesize", END)
        
        # Compile graph with checkpointer
        try:
            self.graph = graph.compile(checkpointer=self.checkpointer)
            logger.info("A2A graph compiled successfully with PostgreSQL checkpointer")
        except Exception as e:
            logger.error(f"Failed to compile A2A graph with checkpointer: {e}")
            # Try without checkpointer as fallback
            self.graph = graph.compile()
            logger.warning("A2A graph compiled without checkpointer (fallback mode)")
    
    async def analyze_request(self, state: A2AState) -> A2AState:
        """Analyze the request complexity and needs"""
        messages = state.get("messages", [])
        if not messages:
            return state
        
        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage):
            return state
        
        logger.info(f"🔍 A2A Orchestrator analyzing: {last_message.content[:100]}...")
        
        # Analyze complexity
        analysis_prompt = """Analyze this request and determine:
1. Is this a simple request (single agent) or complex (needs multiple agents)?
2. What agents might need to collaborate?
3. What data dependencies exist?

Request: {request}

Return JSON: {{"complexity": "simple|complex", "primary_agent": "...", "potential_collaborators": ["..."], "reason": "..."}}"""
        
        response = self.model.invoke([
            {"role": "system", "content": analysis_prompt},
            {"role": "user", "content": last_message.content}
        ])
        
        try:
            analysis = json.loads(response.content)
            state["context"] = {
                "complexity": analysis.get("complexity", "simple"),
                "potential_collaborators": analysis.get("potential_collaborators", []),
                "analysis_reason": analysis.get("reason", "")
            }
            state["primary_agent"] = analysis.get("primary_agent", "general")
            state["execution_path"] = ["orchestrator"]
            state["agent_requests"] = []
            state["agent_responses"] = {}
            logger.info(f"📊 Analysis complete: {analysis.get('complexity')} request, primary: {state['primary_agent']}")
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            state["primary_agent"] = "general"
            state["context"] = {"complexity": "simple"}
        
        return state
    
    async def route_to_primary(self, state: A2AState) -> A2AState:
        """Route to the primary agent"""
        primary = state.get("primary_agent", "general")
        state["current_agent"] = primary
        state["execution_path"].append(f"route_to_{primary}")
        logger.info(f"🚀 Routing to primary agent: {primary}")
        return state
    
    async def execute_current_agent(self, state: A2AState) -> A2AState:
        """Execute the current agent with A2A awareness"""
        current = state.get("current_agent", "general")
        
        if current not in self.agents:
            logger.error(f"Agent {current} not found")
            state["needs_help"] = False
            return state
        
        logger.info(f"⚙️ Executing agent: {current}")
        state["execution_path"].append(f"execute_{current}")
        
        # Create enhanced state for agent with A2A context
        agent_state = {
            "messages": state["messages"],
            "agent_responses": state.get("agent_responses", {}),
            "context": state.get("context", {}),
            "execution_path": state.get("execution_path", [])
        }
        
        # Execute agent
        agent = self.agents[current]
        result = await agent(agent_state)
        
        # Check if agent added a help request
        if "help_request" in result:
            state["needs_help"] = True
            state["help_request"] = result["help_request"]
            state["agent_requests"].append(result["help_request"])
            logger.info(f"🆘 Agent {current} requesting help: {result['help_request']}")
        else:
            state["needs_help"] = False
            # Store agent's response
            if result.get("messages"):
                last_response = result["messages"][-1]
                state["agent_responses"][current] = last_response.content
                state["messages"] = result["messages"]
        
        return state
    
    async def coordinate_help_request(self, state: A2AState) -> A2AState:
        """Coordinate help request between agents"""
        help_request = state.get("help_request")
        if not help_request:
            state["needs_help"] = False
            return state
        
        requesting_agent = help_request.get("from", state["current_agent"])
        helping_agent = help_request.get("to")
        need = help_request.get("need")
        
        logger.info(f"🤝 Coordinating: {requesting_agent} → {helping_agent} for {need}")
        state["execution_path"].append(f"coordinate_{requesting_agent}_to_{helping_agent}")
        
        # Switch to helping agent
        state["current_agent"] = helping_agent
        
        # Add context about the help request
        help_context = HumanMessage(
            content=f"[A2A Request from {requesting_agent}]: {need}",
            metadata={"type": "a2a_request", "from": requesting_agent}
        )
        state["messages"].append(help_context)
        
        # Clear help request for next iteration
        state["help_request"] = None
        state["needs_help"] = False
        
        return state
    
    def check_agent_needs(self, state: A2AState) -> Literal["needs_help", "complete"]:
        """Check if agent needs help or is complete"""
        if state.get("needs_help", False):
            return "needs_help"
        return "complete"
    
    async def synthesize_response(self, state: A2AState) -> A2AState:
        """Synthesize final response from all agent interactions"""
        logger.info(f"🎯 Synthesizing response from {len(state['agent_responses'])} agents")
        
        # Build execution summary
        execution_summary = " → ".join(state["execution_path"])
        
        # Collect all agent responses
        responses = state.get("agent_responses", {})
        
        if state["context"].get("complexity") == "complex" and len(responses) > 1:
            # Multi-agent synthesis
            synthesis_prompt = """Synthesize these agent responses into a cohesive answer:

Agent Responses:
{responses}

Execution Path: {path}

Create a unified, well-formatted response that combines all relevant information."""
            
            formatted_responses = "\n".join([f"{agent}: {resp}" for agent, resp in responses.items()])
            
            response = self.model.invoke([
                {"role": "system", "content": synthesis_prompt.format(
                    responses=formatted_responses,
                    path=execution_summary
                )},
                {"role": "user", "content": "Synthesize the response"}
            ])
            
            final_content = response.content
        else:
            # Single agent response
            final_content = list(responses.values())[0] if responses else "No response generated"
        
        # Add execution metadata
        final_message = AIMessage(
            content=final_content,
            metadata={
                "execution_path": execution_summary,
                "agents_involved": list(responses.keys()),
                "a2a_requests": state.get("agent_requests", []),
                "pattern": "a2a_orchestration"
            }
        )
        
        state["messages"].append(final_message)
        state["final_response"] = final_content
        
        logger.info(f"✅ A2A Orchestration complete. Path: {execution_summary}")
        
        return state
    
    async def run(self, message: str, thread_id: str, **kwargs) -> Dict[str, Any]:
        """Run the A2A orchestrator"""
        if not self.graph:
            raise RuntimeError("A2A orchestrator graph not initialized")
        
        initial_state = {
            "messages": [HumanMessage(content=message)],
            "primary_agent": "",
            "current_agent": "",
            "agent_requests": [],
            "agent_responses": {},
            "execution_path": [],
            "context": {},
            "needs_help": False,
            "help_request": None,
            "final_response": None
        }
        
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            logger.info(f"Starting A2A orchestration for thread: {thread_id}")
            result = await self.graph.ainvoke(initial_state, config)
            
            logger.info(f"A2A orchestration completed for thread: {thread_id}")
            return {
                "response": result.get("final_response", ""),
                "execution_path": result.get("execution_path", []),
                "agents_involved": list(result.get("agent_responses", {}).keys()),
                "a2a_requests": result.get("agent_requests", [])
            }
        except Exception as e:
            logger.error(f"A2A orchestration failed for thread {thread_id}: {e}")
            return {
                "response": "I encountered an error while processing your request. Please try again.",
                "execution_path": ["error"],
                "agents_involved": [],
                "a2a_requests": [],
                "error": str(e)
            }
    
    def close(self):
        """Clean up resources"""
        try:
            if hasattr(self, '_connection_pool') and self._connection_pool:
                self._connection_pool.close()
                logger.info("A2A orchestrator connection pool closed")
        except Exception as e:
            logger.error(f"Error closing A2A orchestrator connection pool: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup"""
        self.close()
    
    def __del__(self):
        """Destructor cleanup"""
        try:
            self.close()
        except:
            pass  # Ignore cleanup errors in destructor