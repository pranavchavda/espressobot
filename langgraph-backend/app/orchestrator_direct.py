"""
Direct Orchestrator - Handles routing and general conversation with GPT-5
This version uses a custom, async-native orchestration loop instead of LangGraph.
"""
from typing import Dict, Any, List, Optional
import logging
import json
import re
import asyncio
from app.state.graph_state import GraphState
from app.memory.memory_config import MemoryConfig
from app.memory.memory_persistence import get_memory_node
from langchain_core.messages import AIMessage, HumanMessage
from langsmith.run_helpers import traceable

logger = logging.getLogger(__name__)

class DirectOrchestrator:
    """A custom, async-native orchestrator that handles routing and agent execution."""

    def __init__(self, checkpointer=None):
        self.agents: Dict[str, Any] = {}
        self._token_queues: Dict[str, asyncio.Queue] = {}
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None

        # Get the singleton memory node instance
        self.memory_node = get_memory_node()
        self.memory_config = MemoryConfig()

        from app.config.agent_model_manager import agent_model_manager
        self.model = agent_model_manager.get_model_for_agent("orchestrator")
        logger.info(f"Initialized Direct Orchestrator with model: {type(self.model).__name__}")

        self._initialize_agents()

    def get_token_queue(self, thread_id: Optional[str]) -> Optional[asyncio.Queue]:
        """Return the token queue for a thread if present."""
        if not thread_id:
            return None
        return self._token_queues.get(thread_id)

    def _initialize_agents(self):
        """Initialize all specialist agents."""
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

        agent_classes = [
            ProductsAgentNativeMCPFinal, PricingAgentNativeMCP, InventoryAgentNativeMCP,
            SalesAgentNativeMCP, FeaturesAgentNativeMCP, MediaAgentNativeMCP,
            IntegrationsAgentNativeMCP, ProductManagementAgentNativeMCP, UtilityAgentNativeMCP,
            GraphQLAgentNativeMCP, OrdersAgentNativeMCP, GoogleWorkspaceAgentNativeMCP,
            GA4AnalyticsAgentNativeMCP
        ]
        for AgentClass in agent_classes:
            try:
                agent = AgentClass()
                self.agents[agent.name] = agent
                logger.info(f"Initialized {agent.name} agent: {agent.description}")
            except Exception as e:
                logger.error(f"Failed to initialize {AgentClass.__name__}: {e}")

        asyncio.create_task(self._load_dynamic_agents())

    async def _load_dynamic_agents(self):
        """Load dynamic agents from the database."""
        await asyncio.sleep(2.0) # Delay to prevent startup conflicts
        try:
            from app.database.session import get_db
            from app.agents.dynamic_agent import DynamicAgentFactory
            async for db in get_db():
                try:
                    available_agents = await DynamicAgentFactory.list_available_agents(db)
                    logger.info(f"Found {len(available_agents)} dynamic agents to load.")
                    for agent_info in available_agents:
                        agent_name = agent_info['name']
                        try:
                            agent = await DynamicAgentFactory.create_from_database(db, agent_name)
                            if agent:
                                self.agents[agent.name] = agent
                                logger.info(f"✅ Loaded dynamic agent: {agent.name}")
                        except Exception as e:
                            logger.error(f"❌ Failed to load dynamic agent {agent_name}: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error in dynamic agent loading loop: {e}")
                    break
        except Exception as e:
            logger.error(f"Failed to load dynamic agents: {e}")

    def _get_routing_prompt(self) -> str:
        """Generate the routing and conversation prompt."""
        agent_descriptions = [f"- **{name}**: {agent.description}" for name, agent in self.agents.items()]
        return f"""You are EspressoBot, a helpful AI assistant...
[...Same detailed prompt as before, including rules for multi-agent, etc...]
## Response Format:
Return a JSON object with ONE of these structures:
For direct response:
{{"action": "respond", "message": "Your friendly response here"}}
For routing:
{{"action": "route", "agent": "agent_name", "reason": "Brief explanation..."}}
For multi-agent tasks (A2A):
{{"action": "multi_agent", "agents": ["agent1", "agent2"], "reason": "Why multiple agents needed"}}"""

    def _parse_decision(self, content: str) -> Dict[str, Any]:
        """Parse the LLM's decision from its response."""
        try:
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            logger.warning(f"LLM response did not contain valid JSON. Raw: {content[:200]}")
            return {"action": "respond", "message": "I understand. Let me help with that."}
        except Exception as e:
            logger.warning(f"Failed to parse decision: {e}")
            return {"action": "respond", "message": "I see. How can I assist you further?"}

    @traceable(name="orchestrator_get_routing", run_type="chain")
    async def _get_routing_decision(self, state: GraphState) -> Dict[str, Any]:
        """Invoke the LLM to get a routing decision."""
        routing_prompt = self._get_routing_prompt()
        conversation = [{"role": "system", "content": routing_prompt}]
        for msg in state["messages"][-10:]:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            conversation.append({"role": role, "content": msg.content})

        try:
            response = await asyncio.wait_for(self.model.ainvoke(conversation), timeout=120.0)
            return self._parse_decision(response.content)
        except asyncio.TimeoutError:
            logger.error("Orchestrator routing decision timed out.")
            return {"action": "respond", "message": "I apologize for the delay. Could you please repeat your question?"}

    @traceable(name="orchestrator_synthesis", run_type="chain")
    async def _synthesize_final_response(self, state: GraphState) -> str:
        """Synthesize a final user-facing response based on all agent work."""
        agent_messages = [msg for msg in state["messages"] if isinstance(msg, AIMessage) and msg.metadata.get("agent") != "orchestrator"]
        if not agent_messages:
            return "The request has been processed."

        user_request = next((msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)), "")
        synthesis_prompt = f"""Synthesize the results from the agent(s) into a single, helpful response for the user.
User's original request: "{user_request}"
Agent results:
{chr(10).join([f"- {msg.metadata.get('agent')}: {msg.content}" for msg in agent_messages])}
Provide a concise, natural response that directly answers the user's request based on the agent results. Do not mention the agents."""

        try:
            response = await asyncio.wait_for(self.model.ainvoke(synthesis_prompt), timeout=60.0)
            return response.content
        except Exception as e:
            logger.error(f"Failed to synthesize final response: {e}")
            return agent_messages[-1].content # Fallback to the last agent's raw response

    @traceable(name="orchestrator_run", run_type="chain")
    async def run_orchestration(self, state: GraphState) -> GraphState:
        """The main async-native orchestration logic, now with integrated memory."""
        # 1. Initialize and load memory context
        if not self.memory_node._initialized:
            await self.memory_node.initialize()
        state = await self.memory_node.load_memory_context(state)

        # 2. Get routing decision from LLM
        decision = await self._get_routing_decision(state)
        logger.info(f"Orchestrator decision: {decision}")

        # 3. Handle direct responses
        if decision.get("action") == "respond":
            message_content = decision.get("message", "How can I help you?")
            state["messages"].append(AIMessage(content=message_content, metadata={"agent": "orchestrator"}))
        else:
            # 4. Execute agent sequence
            agent_names = decision.get("agents") or ([decision.get("agent")] if decision.get("agent") else [])
            if not agent_names:
                state["messages"].append(AIMessage(content="I'm not sure how to handle that request. Could you please rephrase?", metadata={"agent": "orchestrator"}))
            else:
                for agent_name in agent_names:
                    agent = self.agents.get(agent_name)
                    if not agent:
                        logger.warning(f"Agent '{agent_name}' not found. Skipping.")
                        continue
                    
                    logger.info(f"🚀 Routing to agent: {agent_name}")
                    try:
                        state = await agent(state)
                        logger.info(f"✅ Completed agent: {agent_name}")
                    except Exception as e:
                        logger.error(f"❌ Agent '{agent_name}' failed: {e}")
                        state["messages"].append(AIMessage(content=f"An error occurred while running the {agent_name} agent.", metadata={"agent": "orchestrator", "error": True}))
                        # Persist memories even on failure to learn from the error context
                        await self.memory_node.persist_conversation_memories(state)
                        return state

                # 5. Synthesize final response
                final_response = await self._synthesize_final_response(state)
                state["messages"].append(AIMessage(content=final_response, metadata={"agent": "orchestrator", "synthesized": True}))

        # 6. Persist memories from the conversation at the end of the turn
        await self.memory_node.persist_conversation_memories(state)
        
        return state

    async def stream(self, messages: List[Any], thread_id: str = None, user_id: str = None):
        """Entry point for streaming responses. Replaces the LangGraph stream."""
        initial_state = GraphState(messages=messages, user_id=user_id, thread_id=thread_id)

        # Run the entire orchestration
        final_state = await self.run_orchestration(initial_state)

        # Yield the final, complete state.
        # The 'streaming' is now of the final result, not intermediate steps.
        # For token-level streaming, the logic would need to be integrated
        # into the `run_orchestration` method, specifically for direct responses.
        yield {"orchestrator": final_state}
        logger.info("Orchestration stream completed.")

    def cleanup_token_queue(self, thread_id: str):
        if thread_id in self._token_queues:
            del self._token_queues[thread_id]