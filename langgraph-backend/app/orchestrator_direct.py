"""
Direct Orchestrator - Handles routing and general conversation with GPT-5
No separate Router or General agents needed
"""
from langgraph.graph import StateGraph, START, END
from typing import Dict, Any, List, Optional, Tuple
import logging
import json
import re
from app.state.graph_state import GraphState
from app.memory.memory_config import MemoryConfig
from langchain_core.messages import AIMessage, HumanMessage
import asyncio
import concurrent.futures

logger = logging.getLogger(__name__)

class DirectOrchestrator:
    """Micromanaging orchestrator that handles both routing and general conversation"""
    
    def __init__(self, checkpointer=None):
        self.agents: Dict[str, Any] = {}
        # Per-thread token queues for real-time streaming of orchestrator direct responses
        self._token_queues: Dict[str, asyncio.Queue] = {}
        # Event loop used by the HTTP layer; needed for thread-safe queue puts
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Memory and checkpointing
        if not checkpointer:
            memory_config = MemoryConfig()
            self.checkpointer = memory_config.get_checkpointer()
            self.memory_config = memory_config
        else:
            self.checkpointer = checkpointer
            self.memory_config = MemoryConfig()
        
        # GPT-5 for orchestration and routing
        from app.config.llm_factory import llm_factory
        self.model = llm_factory.create_llm(
            model_name="gpt-5",
            temperature=0.0,
            max_tokens=2048
        )
        logger.info("Initialized Direct Orchestrator with GPT-5")
        
        self.graph = None
        self._initialize_agents()
        self._build_graph()

    def get_token_queue(self, thread_id: Optional[str]) -> Optional[asyncio.Queue]:
        """Return the token queue for a thread if present"""
        if not thread_id:
            return None
        return self._token_queues.get(thread_id)
    
    def _initialize_agents(self):
        """Initialize all specialist agents (no Router or General needed)"""
        
        # Import all specialist agents
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
        
        # Initialize each specialist agent
        agent_classes = [
            ProductsAgentNativeMCPFinal,
            PricingAgentNativeMCP,
            InventoryAgentNativeMCP,
            SalesAgentNativeMCP,
            FeaturesAgentNativeMCP,
            MediaAgentNativeMCP,
            IntegrationsAgentNativeMCP,
            ProductManagementAgentNativeMCP,
            UtilityAgentNativeMCP,
            GraphQLAgentNativeMCP,
            OrdersAgentNativeMCP,
            GoogleWorkspaceAgentNativeMCP,
            GA4AnalyticsAgentNativeMCP
        ]
        
        for AgentClass in agent_classes:
            try:
                agent = AgentClass()
                self.agents[agent.name] = agent
                logger.info(f"Initialized {agent.name} agent: {agent.description}")
            except Exception as e:
                logger.error(f"Failed to initialize {AgentClass.__name__}: {e}")
    
    def _get_routing_prompt(self) -> str:
        """Generate the routing and conversation prompt"""
        
        agent_descriptions = []
        for name, agent in self.agents.items():
            agent_descriptions.append(f"- **{name}**: {agent.description}")
        
        return f"""You are EspressoBot, a helpful AI assistant powered by GPT-5 for iDrinkCoffee.com.

You have TWO responsibilities:
1. Handle general conversation, greetings, and unclear requests directly
2. Route specific technical requests to specialist agents

## Available Specialist Agents:
{chr(10).join(agent_descriptions)}

## Decision Process:
Analyze the user's request and decide:
- If it's a greeting, general question, or unclear request: Respond directly with a helpful message.
- If it requires specialist knowledge: Route to the appropriate agent.

IMPORTANT EXECUTION PRINCIPLES (Anti-Avoidance):
- Act-first. If the user asks to fetch, list, summarize, or update something, perform the action without asking for confirmation.
- Minimize questions. Only ask a clarifying question when a required parameter is missing or ambiguous.
- Be concise. Return the result directly with a short summary and clear next-step affordances (e.g., "Reply 1/2/3 to open full email").
- Never stall with meta confirmation like "Would you like me to fetch ...?" when the request already authorizes it.

## Routing Rules:
- Product searches, SKU lookups, product details → products
- Price updates, cost changes, margins → pricing
- Sales data, revenue, order analytics → orders
- MAP sales, promotions, discounts → sales
- Stock levels, inventory counts → inventory
- Product features, descriptions, metafields → features
- Images, media management → media
- System integrations, connections → integrations
- Complex product creation, variants → product_management
- Utilities, general operations → utility
- Direct GraphQL operations → graphql
- Google services → google_workspace
- Analytics data → ga4_analytics

## Response Format:
Return a JSON object with ONE of these structures:

For direct response:
{{"action": "respond", "message": "Your friendly response here"}}

For routing:
{{"action": "route", "agent": "agent_name", "reason": "Brief explanation (include any inferred parameters)"}}

For multi-agent tasks (A2A):
{{"action": "multi_agent", "agents": ["agent1", "agent2"], "reason": "Why multiple agents needed"}}"""
    
    async def process_request(self, state: GraphState) -> GraphState:
        """Process request - either respond directly or route to agent"""
        try:
            # Trim messages if needed
            if state["messages"] and len(state["messages"]) > self.memory_config.max_history_length:
                state["messages"] = self.memory_config.trim_messages(state["messages"])
                logger.info(f"Trimmed message history to {len(state['messages'])} messages")
            
            last_message = state["messages"][-1] if state["messages"] else None
            
            if not last_message or not isinstance(last_message, HumanMessage):
                state["messages"].append(AIMessage(
                    content="Hello! I'm EspressoBot, powered by GPT-5. How can I help you with your coffee needs today?",
                    metadata={"agent": "orchestrator"}
                ))
                return state
            
            logger.info(f"Processing request: {last_message.content[:100]}...")
            
            # Get routing decision from GPT-5
            routing_prompt = self._get_routing_prompt()
            
            # Include conversation history for context
            conversation = [{"role": "system", "content": routing_prompt}]
            
            # Add recent conversation history (last 5 exchanges)
            for msg in state["messages"][-10:]:
                if isinstance(msg, HumanMessage):
                    conversation.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    conversation.append({"role": "assistant", "content": msg.content})
            
            # Get decision with timeout protection (increased for complex reasoning)
            try:
                response = await asyncio.wait_for(
                    self.model.ainvoke(conversation),
                    timeout=120.0  # 2 minutes for routing decisions
                )
                
                decision = self._parse_decision(response.content)
                
                if decision["action"] == "respond":
                    # Direct response from orchestrator with TRUE token streaming
                    thread_id = state.get("thread_id") or state.get("configurable", {}).get("thread_id")
                    # Ensure queue exists for this thread
                    if thread_id and thread_id not in self._token_queues:
                        self._token_queues[thread_id] = asyncio.Queue()
                    q = self._token_queues.get(thread_id)

                    full_text = []
                    try:
                        # Stream tokens from the model
                        async for chunk in self.model.astream(conversation):
                            # Try multiple attributes to extract delta safely
                            token = getattr(chunk, "content", None)
                            if not token:
                                token = getattr(chunk, "delta", None)
                            if not token:
                                token = getattr(chunk, "text", None)
                            if not token and hasattr(chunk, "message"):
                                token = getattr(chunk.message, "content", None)
                            if not token:
                                token = ""
                            if token:
                                full_text.append(token)
                                if q:
                                    try:
                                        loop = getattr(self, "_event_loop", None)
                                        if loop is not None:
                                            # We are likely in a different thread; schedule the put on the HTTP loop
                                            import asyncio as _asyncio
                                            _asyncio.run_coroutine_threadsafe(
                                                q.put({"agent": "orchestrator", "delta": token}),
                                                loop,
                                            )
                                        else:
                                            # Fallback if loop not set (same-thread case)
                                            await q.put({"agent": "orchestrator", "delta": token})
                                    except Exception as e:
                                        logger.debug(f"Failed to enqueue token delta: {e}")
                    except Exception as e:
                        logger.warning(f"astream failed, falling back to single response: {e}")
                        full_text.append(decision["message"])  # fall back to decided message

                    final_text = "".join(full_text) if full_text else decision.get("message", "")
                    # Append final AIMessage to state so it persists
                    state["messages"].append(AIMessage(
                        content=final_text,
                        metadata={"agent": "orchestrator", "direct_response": True}
                    ))
                    state["should_continue"] = False
                    logger.info("Orchestrator provided direct response (streamed)")
                    
                elif decision["action"] == "route":
                    # Route to specialist agent
                    agent_name = decision["agent"]
                    if agent_name in self.agents:
                        state["current_agent"] = agent_name
                        state["routing_reason"] = decision.get("reason", "")
                        logger.info(f"Routing to {agent_name}: {decision.get('reason', '')}")
                    else:
                        # Unknown agent, respond directly
                        state["messages"].append(AIMessage(
                            content="I'll help you with that. Let me process your request.",
                            metadata={"agent": "orchestrator", "fallback": True}
                        ))
                        state["should_continue"] = False
                        
                elif decision["action"] == "multi_agent":
                    # Multi-agent coordination (A2A)
                    agents = decision.get("agents", [])
                    state["multi_agent_task"] = {
                        "agents": agents,
                        "reason": decision.get("reason", ""),
                        "responses": {}
                    }
                    state["current_agent"] = agents[0] if agents else None
                    logger.info(f"Multi-agent task with: {agents}")
                    
                else:
                    # Fallback to direct response
                    state["messages"].append(AIMessage(
                        content="I'm here to help! Could you please clarify what you need assistance with?",
                        metadata={"agent": "orchestrator", "parse_error": True}
                    ))
                    state["should_continue"] = False
                    
            except asyncio.TimeoutError:
                logger.error("Orchestrator decision timed out")
                state["messages"].append(AIMessage(
                    content="Hello! I'm EspressoBot. How can I assist you with your coffee needs today?",
                    metadata={"agent": "orchestrator", "timeout": True}
                ))
                state["should_continue"] = False
            
            return state
            
        except Exception as e:
            logger.error(f"Error in orchestrator: {e}")
            state["messages"].append(AIMessage(
                content="I'm here to help! How can I assist you today?",
                metadata={"agent": "orchestrator", "error": str(e)}
            ))
            state["should_continue"] = False
            return state
    
    def _parse_decision(self, content: str) -> Dict[str, Any]:
        """Parse the LLM's decision from its response"""
        try:
            # Try to parse as JSON
            if isinstance(content, str):
                # Look for JSON in the response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            
            # Fallback: analyze content for keywords
            content_lower = content.lower()
            
            # Check for agent mentions
            for agent_name in self.agents.keys():
                if agent_name in content_lower:
                    return {
                        "action": "route",
                        "agent": agent_name,
                        "reason": "Detected agent name in response"
                    }
            
            # Default to direct response
            return {
                "action": "respond",
                "message": content
            }
            
        except Exception as e:
            logger.warning(f"Failed to parse decision: {e}")
            return {
                "action": "respond",
                "message": content if isinstance(content, str) else "How can I help you today?"
            }
    
    def determine_next(self, state: GraphState) -> str:
        """Determine next node in the graph"""
        
        # Check if we should continue
        if state.get("should_continue") == False:
            return "end"
        
        # Check if we already processed with an agent - avoid loops
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        if last_message and hasattr(last_message, 'metadata'):
            # If the last message has an error or is from an agent, end the flow
            if last_message.metadata.get("error") or last_message.metadata.get("agent"):
                return "end"
        
        # Check for multi-agent task
        if state.get("multi_agent_task"):
            task = state["multi_agent_task"]
            completed = len(task.get("responses", {}))
            total = len(task.get("agents", []))
            
            if completed < total:
                # Route to next agent in multi-agent task
                next_agent = task["agents"][completed]
                if next_agent in self.agents:
                    state["current_agent"] = next_agent
                    return next_agent
            else:
                # All agents completed, synthesize response
                return "synthesize"
        
        # Check for current agent routing
        current_agent = state.get("current_agent")
        if current_agent and current_agent in self.agents:
            return current_agent
        
        return "end"
    
    async def synthesize_multi_agent(self, state: GraphState) -> GraphState:
        """Synthesize responses from multiple agents"""
        task = state.get("multi_agent_task", {})
        responses = task.get("responses", {})
        
        if not responses:
            state["messages"].append(AIMessage(
                content="I've completed analyzing your request.",
                metadata={"agent": "orchestrator", "synthesized": True}
            ))
            return state
        
        # Use GPT-5 to synthesize responses
        synthesis_prompt = """Synthesize the following agent responses into a coherent answer:

{responses}

Provide a unified, helpful response that combines the key information."""
        
        formatted_responses = "\n".join([
            f"**{agent}**: {response}" 
            for agent, response in responses.items()
        ])
        
        try:
            response = await asyncio.wait_for(
                self.model.ainvoke([
                    {"role": "system", "content": synthesis_prompt.format(responses=formatted_responses)},
                    {"role": "user", "content": state["messages"][-1].content}
                ]),
                timeout=180.0  # 3 minutes for synthesis of complex responses
            )
            
            state["messages"].append(AIMessage(
                content=response.content,
                metadata={
                    "agent": "orchestrator",
                    "synthesized": True,
                    "agents_used": list(responses.keys())
                }
            ))
        except Exception as e:
            logger.error(f"Synthesis failed: {e}")
            # Fallback: concatenate responses
            combined = "\n\n".join([
                f"From {agent}: {response}"
                for agent, response in responses.items()
            ])
            state["messages"].append(AIMessage(
                content=combined,
                metadata={"agent": "orchestrator", "fallback_synthesis": True}
            ))
        
        return state
    
    def _make_sync_wrapper(self, async_func):
        """Create a synchronous wrapper for async functions"""
        def sync_wrapper(state):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, async_func(state))
                return future.result()
        return sync_wrapper
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(GraphState)
        
        # Add nodes with sync wrappers for sync streaming
        workflow.add_node("orchestrator", self._make_sync_wrapper(self.process_request))
        
        # Add specialist agents with sync wrappers
        for agent_name, agent in self.agents.items():
            workflow.add_node(agent_name, self._make_sync_wrapper(agent))
        
        # Add synthesis node for multi-agent tasks
        workflow.add_node("synthesize", self._make_sync_wrapper(self.synthesize_multi_agent))
        
        # Routing from orchestrator
        workflow.add_conditional_edges(
            "orchestrator",
            self.determine_next,
            {
                **{agent_name: agent_name for agent_name in self.agents.keys()},
                "synthesize": "synthesize",
                "end": END
            }
        )
        
        # All agents route to END (not back to orchestrator to avoid loops)
        for agent_name in self.agents.keys():
            workflow.add_edge(agent_name, END)
        
        # Synthesis completes the flow
        workflow.add_edge("synthesize", END)
        
        # Set entry point
        workflow.set_entry_point("orchestrator")
        
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        logger.info("Direct orchestrator graph compiled successfully")
    
    async def stream(self, messages: List[Any], thread_id: str = None, user_id: str = None):
        """Stream responses through the graph"""
        config = {"configurable": {"thread_id": thread_id}} if thread_id else {}
        
        # Get existing state
        try:
            state_snapshot = self.graph.get_state(config)
            current_state = state_snapshot.values if state_snapshot else None
        except Exception as e:
            logger.warning(f"Could not get state for thread {thread_id}: {e}")
            current_state = None
        
        if current_state and current_state.get("messages"):
            logger.info(f"Found existing state with {len(current_state['messages'])} messages")
            # Append new message to existing state
            current_state["messages"].extend(messages)
            # Ensure user_id is in state
            if user_id:
                current_state["user_id"] = user_id
            # New user turn: ensure we continue the graph execution
            current_state["should_continue"] = True
            # Clear transient routing flags from prior runs
            if "routing_reason" in current_state:
                current_state.pop("routing_reason", None)
            # Keep current_agent unset until orchestrator selects one this turn
            current_state.pop("current_agent", None)
            # Ensure thread_id present in state for streaming callbacks
            if thread_id:
                current_state["thread_id"] = thread_id
            initial_state = current_state
        else:
            logger.info(f"No existing state found for thread {thread_id}, creating new state")
            initial_state = {"messages": messages}
            # Add user_id to new state
            if user_id:
                initial_state["user_id"] = user_id
            # New threads should continue by default
            initial_state["should_continue"] = True
            # Inject thread_id so nodes can access it (needed for token streaming)
            if thread_id:
                initial_state["thread_id"] = thread_id
    
        # Capture the HTTP/server event loop for thread-safe queue puts
        try:
            self._event_loop = asyncio.get_running_loop()
        except RuntimeError:
            # Not in an event loop; leave as None
            self._event_loop = None

        # Prepare token queue for this thread
        if thread_id and thread_id not in self._token_queues:
            self._token_queues[thread_id] = asyncio.Queue()

        try:
            # Stream through the graph (use sync stream since our checkpointer doesn't support async)
            for chunk in self.graph.stream(initial_state, config):
                # Attach thread id so downstream can correlate
                try:
                    for _, updates in chunk.items():
                        if isinstance(updates, dict):
                            updates.setdefault("thread_id", thread_id)
                except Exception:
                    pass
                yield chunk
        finally:
            # Do not delete the queue immediately; HTTP layer will read remaining tokens and then clean up
            pass

    def cleanup_token_queue(self, thread_id: str):
        if thread_id in self._token_queues:
            del self._token_queues[thread_id]