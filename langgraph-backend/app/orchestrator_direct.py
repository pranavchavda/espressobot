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
from app.memory.memory_persistence import MemoryPersistenceNode
from langchain_core.messages import AIMessage, HumanMessage
import asyncio
import concurrent.futures
from langsmith.run_helpers import traceable

logger = logging.getLogger(__name__)

class DirectOrchestrator:
    """Micromanaging orchestrator that handles both routing and general conversation"""
    
    def __init__(self, checkpointer=None):
        self.agents: Dict[str, Any] = {}
        # Per-thread token queues for real-time streaming of orchestrator direct responses
        self._token_queues: Dict[str, asyncio.Queue] = {}
        # Event loop used by the HTTP layer; needed for thread-safe queue puts
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Initialize memory persistence for extracting memories from conversations
        self.memory_node = MemoryPersistenceNode()
        
        # Memory and checkpointing
        if not checkpointer:
            memory_config = MemoryConfig()
            self.checkpointer = memory_config.get_checkpointer()
            self.memory_config = memory_config
        else:
            self.checkpointer = checkpointer
            self.memory_config = MemoryConfig()
        
        # Use dynamic model configuration
        from app.config.agent_model_manager import agent_model_manager
        self.model = agent_model_manager.get_model_for_agent("orchestrator")
        logger.info(f"Initialized Direct Orchestrator with model: {type(self.model).__name__}")
        
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
    
    def _build_context_for_agent(self, messages: List) -> str:
        """Build a concise context summary for agent handoff"""
        context_parts = []
        
        # Include last 6 messages (3 exchanges) for context
        recent_messages = messages[-6:] if len(messages) > 6 else messages
        
        for msg in recent_messages:
            if isinstance(msg, HumanMessage):
                context_parts.append(f"User: {msg.content[:200]}")
            elif isinstance(msg, AIMessage):
                # Skip routing messages
                if not msg.metadata.get("routing"):
                    context_parts.append(f"Assistant: {msg.content[:200]}")
        
        return "\n".join(context_parts)
    
    def _extract_key_entities(self, messages: List) -> Dict[str, Any]:
        """Extract key entities mentioned in conversation"""
        entities = {
            "people": [],
            "products": [],
            "topics": [],
            "references": []
        }
        
        # TODO: Implement proper NER (Named Entity Recognition) using spaCy or similar
        # For now, just return empty entities rather than hardcoded test data
        # This should extract actual entities from the conversation dynamically
        
        return entities
    
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
    
    @traceable(name="orchestrator_process_request", run_type="chain")
    async def process_request(self, state: GraphState) -> GraphState:
        """Process request - either respond directly or route to agent"""
        try:
            # Initialize memory node if not already done
            if not self.memory_node._initialized:
                await self.memory_node.initialize()
                logger.info("Initialized memory persistence node")
            
            # Load memory context BEFORE processing the request
            state = await self.memory_node.load_memory_context(state)
            memory_context = state.get('memory_context', [])
            logger.info(f"Loaded memory context: {len(memory_context)} relevant memories")
            
            # Log the actual memories loaded for context
            for i, mem in enumerate(memory_context[:3], 1):  # Show first 3 memories
                logger.info(f"  Memory {i}: '{mem['content'][:80]}...' (similarity: {mem.get('similarity', 'N/A')})")
            
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
            
            # Add memory context to the routing prompt if available
            memory_context_str = ""
            if state.get("memory_context"):
                memory_items = []
                for mem in state["memory_context"][:5]:  # Include top 5 most relevant memories
                    memory_items.append(f"- {mem['content']} (importance: {mem.get('importance', 0.5):.1f})")
                if memory_items:
                    memory_context_str = f"\n\n## Relevant User Context from Previous Conversations:\n" + "\n".join(memory_items)
            
            enhanced_routing_prompt = routing_prompt + memory_context_str
            
            # Include conversation history for context
            conversation = [{"role": "system", "content": enhanced_routing_prompt}]
            
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
                    # Direct response from orchestrator - use the message from the decision
                    thread_id = state.get("thread_id") or state.get("configurable", {}).get("thread_id")
                    # Ensure queue exists for this thread
                    if thread_id and thread_id not in self._token_queues:
                        self._token_queues[thread_id] = asyncio.Queue()
                    q = self._token_queues.get(thread_id)

                    # Get the message from the decision
                    message_content = decision.get("message", "")
                    
                    # Check if we have a complete response from the routing decision
                    # The routing prompt asks for a full response in the message field
                    if message_content and len(message_content) > 20:  # Reasonable response length
                        # Use the message directly from routing decision - no second API call needed!
                        full_text = [message_content]
                        
                        # Stream the existing message to the queue if available
                        if q:
                            try:
                                # Stream in chunks for better UX
                                step = 20
                                for i in range(0, len(message_content), step):
                                    chunk = message_content[i:i+step]
                                    loop = getattr(self, "_event_loop", None)
                                    if loop is not None:
                                        import asyncio as _asyncio
                                        _asyncio.run_coroutine_threadsafe(
                                            q.put({"agent": "orchestrator", "delta": chunk}),
                                            loop,
                                        )
                                    else:
                                        await q.put({"agent": "orchestrator", "delta": chunk})
                                    await asyncio.sleep(0.01)  # Small delay for natural streaming feel
                            except Exception as e:
                                logger.debug(f"Failed to stream routing response: {e}")
                    else:
                        # Fallback: generate a new response if routing didn't provide one
                        # This should rarely happen with a proper routing prompt
                        response_conversation = [
                            {"role": "system", "content": "You are EspressoBot, a helpful AI assistant powered by GPT-5 for iDrinkCoffee.com. Be friendly, conversational, and helpful."}
                        ]
                        
                        # Add conversation history for context (last 20 messages to maintain context)
                        for msg in state["messages"][-20:]:
                            if isinstance(msg, HumanMessage):
                                response_conversation.append({"role": "user", "content": msg.content})
                            elif isinstance(msg, AIMessage):
                                response_conversation.append({"role": "assistant", "content": msg.content})
                        
                        # Add the current message if it's not already included
                        if not response_conversation[-1]["content"] == last_message.content:
                            response_conversation.append({"role": "user", "content": last_message.content})
                        
                        full_text = []
                        
                        # Check if model is GPT-5 (which may require org verification for streaming)
                        model_name = getattr(self.model, "model_name", "")
                        skip_streaming = "gpt-5" in model_name.lower()
                        
                        if skip_streaming:
                            # Skip streaming for GPT-5 models to avoid verification errors
                            logger.info(f"Skipping streaming for {model_name} model")
                            try:
                                response = await asyncio.wait_for(
                                    self.model.ainvoke(response_conversation),
                                    timeout=120.0
                                )
                                full_text = [response.content]
                                # Send full response as single chunk if queue available
                                if q:
                                    try:
                                        loop = getattr(self, "_event_loop", None)
                                        if loop is not None:
                                            import asyncio as _asyncio
                                            _asyncio.run_coroutine_threadsafe(
                                                q.put({"agent": "orchestrator", "delta": response.content}),
                                                loop,
                                            )
                                        else:
                                            await q.put({"agent": "orchestrator", "delta": response.content})
                                    except Exception as e:
                                        logger.debug(f"Failed to enqueue response: {e}")
                            except asyncio.TimeoutError:
                                logger.error("Model invoke timed out after 120 seconds")
                                full_text = ["I apologize, but I'm taking too long to respond. Please try again."]
                        else:
                            try:
                                # Stream tokens from the model with the proper conversation
                                async for chunk in self.model.astream(response_conversation):
                                    # Log the raw chunk for debugging
                                    logger.debug(f"Raw streaming chunk type: {type(chunk)}, chunk: {chunk}")
                                    
                                    # Extract token from chunk
                                    token = None
                                    
                                    # For AIMessageChunk, get the content directly
                                    if hasattr(chunk, "content"):
                                        content = chunk.content
                                        if content and isinstance(content, str):
                                            token = content
                                    
                                    # Only append non-empty string tokens
                                    if token and isinstance(token, str) and token.strip():
                                        logger.debug(f"Extracted token: {token}")
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
                                    elif hasattr(chunk, "text") and callable(chunk.text):
                                        # Don't send the method reference to the UI
                                        logger.debug(f"Skipping text method reference from chunk: {chunk}")
                            except Exception as e:
                                logger.warning(f"astream failed (likely org verification needed), falling back to non-streaming: {e}")
                                # Fall back to non-streaming invoke
                                try:
                                    response = await asyncio.wait_for(
                                        self.model.ainvoke(response_conversation),
                                        timeout=120.0
                                    )
                                    full_text = [response.content]
                                    # Send full response as single chunk if queue available
                                    if q:
                                        try:
                                            loop = getattr(self, "_event_loop", None)
                                            if loop is not None:
                                                import asyncio as _asyncio
                                                _asyncio.run_coroutine_threadsafe(
                                                    q.put({"agent": "orchestrator", "delta": response.content}),
                                                    loop,
                                                )
                                            else:
                                                await q.put({"agent": "orchestrator", "delta": response.content})
                                        except Exception as qe:
                                            logger.debug(f"Failed to enqueue full response: {qe}")
                                except Exception as invoke_error:
                                    logger.error(f"Both streaming and non-streaming failed: {invoke_error}")
                                    fallback_msg = decision.get("message", "I apologize, but I'm having trouble generating a response.") if isinstance(decision, dict) else "I apologize, but I'm having trouble generating a response."
                                    full_text = [fallback_msg]

                    # Ensure all items in full_text are strings
                    try:
                        final_text = "".join(str(item) for item in full_text) if full_text else (decision.get("message", "") if isinstance(decision, dict) else "")
                    except Exception as join_error:
                        logger.error(f"Error joining full_text: {join_error}, full_text contents: {full_text}")
                        final_text = "I apologize, but I encountered an error generating the response."
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
                        
                        # Build conversation context for the agent (A2A context passing)
                        context_summary = self._build_context_for_agent(state["messages"])
                        state["agent_context"] = {
                            "conversation_summary": context_summary,
                            "key_entities": self._extract_key_entities(state["messages"]),
                            "last_topic": decision.get("reason", ""),
                            "message_count": len(state["messages"]),
                            "memory_context": state.get("memory_context", [])  # Pass memory context to agent
                        }
                        
                        logger.info(f"Routing to {agent_name}: {decision.get('reason', '')}")
                        logger.info(f"Passing context with {len(context_summary)} chars to agent")
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
            
            # Extract and persist memories from the conversation
            if state.get("user_id"):
                try:
                    state = await self.memory_node.persist_conversation_memories(state)
                    logger.info(f"Extracted {state.get('metadata', {}).get('memories_extracted', 0)} memories")
                except Exception as e:
                    logger.error(f"Failed to persist memories: {e}")
            
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
    
    @traceable(name="orchestrator_synthesize", run_type="chain")
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
        
        # Extract and persist memories after synthesis
        if state.get("user_id"):
            try:
                state = await self.memory_node.persist_conversation_memories(state)
                logger.info(f"Extracted {state.get('metadata', {}).get('memories_extracted', 0)} memories after synthesis")
            except Exception as e:
                logger.error(f"Failed to persist memories after synthesis: {e}")
        
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
            chunk_count = 0
            for chunk in self.graph.stream(initial_state, config):
                chunk_count += 1
                logger.info(f"Streaming chunk {chunk_count}: {list(chunk.keys())}")
                # Attach thread id so downstream can correlate
                try:
                    for _, updates in chunk.items():
                        if isinstance(updates, dict):
                            updates.setdefault("thread_id", thread_id)
                except Exception:
                    pass
                yield chunk
            logger.info(f"Graph stream completed after {chunk_count} chunks")
        finally:
            # Do not delete the queue immediately; HTTP layer will read remaining tokens and then clean up
            logger.info("Stream generator finalizing")
            pass

    def cleanup_token_queue(self, thread_id: str):
        if thread_id in self._token_queues:
            del self._token_queues[thread_id]