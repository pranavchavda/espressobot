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
        # Relay ensures only Orchestrator speaks to the user
        workflow.add_node("relay", self.relay_to_user)
        
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
        
        # After any agent runs, either go back to router for another hop or relay to user
        for agent_name in self.agents.keys():
            workflow.add_conditional_edges(
                agent_name,
                self.agent_handoff_condition,
                {
                    "router": "router",
                    "end": "relay"
                }
            )
        
        # Relay then ends the flow
        workflow.add_edge("relay", END)
        
        workflow.set_entry_point("router")
        
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        logger.info("Graph compiled successfully")
    
    def route_request(self, state: GraphState) -> GraphState:
        """Route the request to the appropriate agent"""
        try:
            # Honor explicit next_agent handoff if provided
            if state.get("next_agent") and state["next_agent"] in self.agents:
                forced = state["next_agent"]
                state["current_agent"] = forced
                # clear next_agent so router can decide on subsequent hops unless set again
                state["next_agent"] = None
                # Attach handoff context for the next agent if present
                try:
                    from langchain_core.messages import HumanMessage
                    reason = state.get("handoff_reason")
                    ctx = state.get("handoff_context") or {}
                    if reason or ctx:
                        summary = f"[Handoff from {state.get('last_agent') or 'orchestrator'}] {reason or ''}"
                        if ctx:
                            import json
                            # Keep context compact
                            ctx_json = json.dumps(ctx)[:1000]
                            summary += f"\nContext: {ctx_json}"
                        state["messages"].append(HumanMessage(content=summary, metadata={"type": "handoff_context"}))
                    # Clear after use
                    state["handoff_reason"] = None
                    state["handoff_context"] = None
                except Exception:
                    pass
                # default to continue unless agent stops it
                state["should_continue"] = True
                logger.info(f"Forced routing to next_agent: {forced}")
                return state
            
            # Trim message history to manage tokens
            if state["messages"] and len(state["messages"]) > self.memory_config.max_history_length:
                state["messages"] = self.memory_config.trim_messages(state["messages"])
                logger.info(f"Trimmed message history to {len(state['messages'])} messages")
            
            # Only route on the last HumanMessage to avoid looping on our own AI outputs
            last_message = None
            if state.get("messages"):
                from langchain_core.messages import HumanMessage
                for msg in reversed(state["messages"]):
                    if isinstance(msg, HumanMessage):
                        last_message = msg
                        break
            
            if not last_message:
                logger.info("Router: No human message found; ending conversation hop")
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

    def agent_handoff_condition(self, state: GraphState) -> str:
        """After an agent runs, decide whether to continue routing or end.
        Only continue if a follow-up handoff is explicitly requested via next_agent.
        """
        try:
            # Increment hop counter and guard against loops
            try:
                state["hop_count"] = int(state.get("hop_count", 0)) + 1
            except Exception:
                state["hop_count"] = 1
            decision = self._decide_route_or_relay(state)
            return decision
        except Exception:
            return "end"

    def _llm_decide_handoff(self, state: GraphState) -> Optional[dict]:
        """Use an LLM to decide whether to handoff to another agent or relay to the user.
        Returns a dict like {"action": "handoff", "agent": "media", "reason": "..."}
        or {"action": "relay", "reason": "..."}.
        """
        try:
            # Prepare inputs
            from langchain_core.messages import HumanMessage, AIMessage
            from app.config.llm_factory import llm_factory
            # Collect available agents summary
            agent_infos = []
            for name, agent in self.agents.items():
                desc = getattr(agent, "description", "") or ""
                agent_infos.append({"name": name, "description": desc})
            # Extract last human and last agent message
            messages = state.get("messages", []) or []
            last_human = None
            last_ai = None
            for msg in reversed(messages):
                if last_ai is None and isinstance(msg, AIMessage):
                    last_ai = msg
                if last_human is None and isinstance(msg, HumanMessage):
                    last_human = msg
                if last_ai and last_human:
                    break
            last_agent_name = state.get("last_agent")
            payload = {
                "available_agents": agent_infos,
                "last_human_message": (last_human.content if last_human else ""),
                "last_agent": last_agent_name,
                "last_agent_message": (last_ai.content if last_ai else ""),
            }
            system_prompt = (
                "You are the Orchestrator for a multi-agent e-commerce operations system. "
                "Decide the best next step after a specialist agent finishes: either handoff to the most capable next agent, or relay to the user. "
                "Use the available agent descriptions and the conversation context. If another specialist should act (has the right capabilities), choose handoff. "
                "If the next step requires user input/confirmation or no further action is needed now, choose relay. Return STRICT JSON only."
            )
            user_prompt = (
                "Decide the next step. Respond with a single JSON object only, no prose.\n\n"
                "JSON schema:\n"
                "{\n  \"action\": \"handoff\"|\"relay\",\n  \"agent\": <agent_name if action==handoff else omit>,\n  \"reason\": <short string>\n}\n\n"
                f"Input:\n{payload}"
            )
            model = llm_factory.create_llm(model_name="gpt-5", temperature=0.0, max_tokens=512)
            response = model.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
            content = response.content
            if isinstance(content, list):
                content = content[0].text if content else ""
            logger.debug(f"_llm_decide_handoff raw content: {content}")
            import json, re
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                match = re.search(r"\{[\s\S]*\}", content)
                if match:
                    return json.loads(match.group(0))
            return None
        except Exception as e:
            logger.debug(f"_llm_decide_handoff error: {e}")
            return None

    def _decide_route_or_relay(self, state: GraphState) -> str:
        """Orchestrator-level decision after an agent completes.
        Heuristic:
        - If next_agent is set -> route to router (will force that agent).
        - Else try an LLM-based decision to pick the best specialist or relay.
        - Else try to suggest a better specialist based on the user + agent messages.
        - If the last agent message appears to ask the user for info/confirmation -> relay to user.
        - Otherwise -> relay to user (safe default).
        """
        try:
            # Loop guard
            MAX_HOPS = 5
            if int(state.get("hop_count", 0)) >= MAX_HOPS:
                logger.info("Hop limit reached, handing over to user")
                return "end"
            
            # Agent requested an explicit handoff
            if state.get("next_agent"):
                return "router"
            
            # Inspect last AI message (agent output)
            from langchain_core.messages import AIMessage
            messages = state.get("messages", []) or []
            last_ai = None
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    last_ai = msg
                    break
            content = (last_ai.content or "").lower() if last_ai else ""
            
            # Try intelligent LLM-based handoff decision first (default enabled)
            use_llm = os.getenv("ORCH_USE_LLM_HANDOFF", "1").lower() not in ("0", "false", "no")
            if use_llm:
                try:
                    llm_decision = self._llm_decide_handoff(state)
                    if llm_decision and isinstance(llm_decision, dict):
                        action = llm_decision.get("action")
                        agent = llm_decision.get("agent")
                        reason = llm_decision.get("reason")
                        # Normalize and alias agent names from LLM
                        agent_norm = None
                        if isinstance(agent, str):
                            agent_norm = agent.strip().lower()
                            alias_map = {
                                "product_mgmt": "product_management",
                                "product management": "product_management",
                                "ga4": "ga4_analytics",
                                "google analytics": "ga4_analytics",
                                "analytics": "ga4_analytics",
                                "google workspace": "google_workspace",
                                "workspace": "google_workspace",
                            }
                            if agent_norm in alias_map:
                                agent_norm = alias_map[agent_norm]
                            if agent_norm not in self.agents:
                                import re as _re
                                simple = _re.sub(r"[^a-z0-9]", "", agent_norm)
                                for name in self.agents.keys():
                                    name_simple = _re.sub(r"[^a-z0-9]", "", name)
                                    if simple == name_simple or simple in name_simple or name_simple in simple:
                                        agent_norm = name
                                        break
                        if action == "handoff" and agent_norm and agent_norm in self.agents and agent_norm != state.get("last_agent"):
                            logger.info(f"LLM decided handoff to '{agent_norm}' – reason: {reason}")
                            state["next_agent"] = agent_norm
                            state["handoff_reason"] = reason or "LLM-decided handoff"
                            return "router"
                        if action == "relay":
                            # LLM requested to hand over to user
                            logger.info(f"LLM decided to relay to user – reason: {reason}")
                            return "end"
                except Exception as e:
                    logger.debug(f"LLM handoff decision failed: {e}")
            
            # Try to suggest a follow-up specialist based on capability/domain
            suggested = self._suggest_handoff(state)
            if suggested and suggested in self.agents and suggested != state.get("last_agent"):
                logger.info(f"Heuristic suggests handoff to '{suggested}'")
                state["next_agent"] = suggested
                state["handoff_reason"] = state.get("handoff_reason") or f"Follow-up required by {suggested} based on task domain"
                return "router"
            
            # Simple ask-user detectors
            ask_markers = [
                "please provide",
                "i need",
                "what is",
                "could you",
                "would you",
                "can you",
                "do you want",
                "should i",
                "please confirm",
                "confirm",
                "specify",
                "let me know",
                "provide",
                "choose",
                "select",
                "send",
                "share",
                "tell me"
            ]
            if content and any(marker in content for marker in ask_markers):
                logger.info("Detected agent asking user for input/confirmation – relaying to user")
                return "end"  # go to relay
            
            # Default to handover to user
            logger.info("Defaulting to relay to user (no handoff decided)")
            return "end"
        except Exception:
            return "end"

    def _suggest_handoff(self, state: GraphState) -> Optional[str]:
        """Suggest a next agent based on the last human request and the last agent's response.
        General-purpose heuristic using domain keywords and inability signals.
        Returns agent name or None.
        """
        try:
            from langchain_core.messages import HumanMessage, AIMessage
            messages = state.get("messages", []) or []
            last_human = None
            last_ai = None
            for msg in reversed(messages):
                if last_ai is None and isinstance(msg, AIMessage):
                    last_ai = msg
                if last_human is None and isinstance(msg, HumanMessage):
                    last_human = msg
                if last_ai and last_human:
                    break
            user_text = (last_human.content or "").lower() if last_human else ""
            agent_text = (last_ai.content or "").lower() if last_ai else ""
            
            # Signals that the agent couldn't act and is deferring
            inability_markers = [
                "i don't have a tool",
                "i dont have a tool",
                "i cannot",
                "i can't",
                "i cant",
                "not able to",
                "i can give steps",
                "instructions you can run",
                "you can run",
                "use the shopify admin",
                "rest admin api",
                "graphql admin api",
                "i don't have direct access",
                "i do not have direct access",
            ]
            deferring = any(m in agent_text for m in inability_markers)
            
            # Domain keyword buckets -> agents (only if present in self.agents)
            domain_map = {
                "media": ["image", "images", "photo", "media", "thumbnail", "gallery", "alt text", "featured image", "upload"],
                "pricing": ["price", "pricing", "cost", "margin", "discount", "map", "sale price", "promo"],
                "inventory": ["inventory", "stock", "quantity", "restock", "availability", "in stock"],
                "orders": ["order", "orders", "refund", "fulfillment", "shipment", "tracking"],
                "features": ["metafield", "metafields", "feature", "features", "description", "specs", "attributes", "tags"],
                "product_management": ["variant", "variants", "sku", "create product", "duplicate", "option", "bundle"],
                "graphql": ["graphql", "mutation", "query", "gid://", "node"],
                "integrations": ["integration", "webhook", "api key", "sync", "connector"],
                "utility": ["convert", "csv", "export", "import", "format"],
                "ga4_analytics": ["ga4", "analytics", "google analytics", "event", "conversion"],
                "google_workspace": ["gmail", "google sheets", "drive", "docs", "calendar", "workspace"],
                "sales": ["promotion", "sale", "campaign", "map", "deal", "coupon"],
            }
            # Compute scores per agent
            text = f"{user_text}\n{agent_text}"
            scores = {}
            for agent, kws in domain_map.items():
                if agent in self.agents:
                    s = sum(1 for kw in kws if kw in text)
                    scores[agent] = s
            # Prefer agents with non-zero scores
            if scores:
                # Sort by score desc
                ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
                best, best_score = ranked[0]
                if best_score > 0 and best != state.get("last_agent"):
                    # Prepare context and suggest best specialist
                    ctx = {"basis": "keyword_match", "score": best_score}
                    if deferring:
                        ctx["deferring"] = True
                    state["handoff_context"] = ctx
                    state["handoff_reason"] = state.get("handoff_reason") or "Specialist with appropriate tools required"
                    return best
            return None
        except Exception:
            return None

    def relay_to_user(self, state: GraphState) -> GraphState:
        """Relay the latest agent message to the user in the Orchestrator voice.
        Ensures the frontend only ever sees messages from 'Orchestrator'.
        """
        try:
            from langchain_core.messages import AIMessage
            messages = state.get("messages", []) or []
            last_agent = state.get("last_agent")
            # Find the last AI message (agent response)
            last_ai = None
            for msg in reversed(messages):
                if isinstance(msg, AIMessage):
                    last_ai = msg
                    break
            relay_content = last_ai.content if last_ai and getattr(last_ai, "content", None) else ""
            if not relay_content:
                relay_content = ""
            # Wrap with Orchestrator voice so it's clear who is speaking
            source = last_agent if last_agent else "a specialist"
            orchestrator_prefix = f"I’m coordinating this for you (via {source})."
            # Keep content verbatim but clearly attributed to Orchestrator
            final_content = f"{orchestrator_prefix}\n\n{relay_content}" if relay_content else orchestrator_prefix
            # Append Orchestrator message
            messages.append(AIMessage(
                content=final_content,
                metadata={"agent": "orchestrator", "relay_from": last_agent}
            ))
            state["messages"] = messages
            state["current_agent"] = "orchestrator"
            state["last_agent"] = "orchestrator"
            state["next_agent"] = None
            state["should_continue"] = False
            return state
        except Exception as e:
            logger.error(f"Error in relay_to_user: {e}")
            return state
    
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
                        # Only relay orchestrated output to the client
                        if node_name == "relay" and isinstance(node_output, dict) and "messages" in node_output:
                            messages = node_output.get("messages", [])
                            if messages:
                                last_message = messages[-1]
                                from langchain_core.messages import AIMessage
                                if isinstance(last_message, AIMessage):
                                    content = last_message.content
                                    if content:
                                        yield {
                                            "type": "token",
                                            "content": content,
                                            "agent": "Orchestrator"
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