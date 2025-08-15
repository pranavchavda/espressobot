"""
Custom Async Orchestrator - Simple, async-native orchestration without LangGraph
Implements the pattern: User → Orchestrator → Agent1 → Orchestrator → Agent2 → Orchestrator → User
"""
from typing import Dict, Any, List, Optional, Set, AsyncGenerator
import logging
import json
import asyncio
import os
from datetime import datetime
from dataclasses import dataclass
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.memory.memory_persistence import MemoryPersistenceNode
from langsmith.run_helpers import traceable
import asyncpg

logger = logging.getLogger(__name__)

@dataclass
class RoutingDecision:
    """Represents a routing decision from the orchestrator"""
    action: str  # "route" or "respond"
    agent_name: Optional[str] = None
    message: Optional[str] = None
    needs_more_agents: bool = False
    reasoning: Optional[str] = None

class CustomOrchestrator:
    """Simple async orchestrator that coordinates between agents"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.memory_node = MemoryPersistenceNode()
        
        # Get database URL for conversation persistence
        self.database_url = os.getenv("DATABASE_URL")
        if not self.database_url:
            logger.warning("DATABASE_URL not set - conversations won't be persisted")
        
        # Initialize model
        from app.config.agent_model_manager import agent_model_manager
        self.model = agent_model_manager.get_model_for_agent("orchestrator")
        logger.info(f"Initialized Custom Orchestrator with model: {type(self.model).__name__}")
        
        # Initialize all agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all specialist agents"""
        from app.agents.products_custom import ProductsAgentCustom  # Use new custom agent
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
            ProductsAgentCustom,  # Using new custom agent
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
    
    async def _load_memory_context(self, user_id: str, query: str) -> List[Dict[str, Any]]:
        """Load relevant memories for the user and query"""
        try:
            from app.memory.postgres_memory_manager_v2 import SimpleMemoryManager
            
            memory_manager = SimpleMemoryManager()
            
            # Search for relevant memories
            search_results = await memory_manager.search_memories(
                user_id=user_id,
                query=query,
                limit=5
            )
            
            # Format memories for context
            memory_context = []
            for result in search_results:
                memory = result.memory  # Extract memory from SearchResult
                memory_context.append({
                    "content": memory.content,
                    "category": memory.category,
                    "importance": memory.importance_score,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None
                })
            
            if memory_context:
                logger.info(f"Loaded {len(memory_context)} relevant memories for user {user_id}")
            
            return memory_context
            
        except Exception as e:
            logger.warning(f"Failed to load memory context: {e}")
            return []
    
    async def _ensure_conversation_exists(self, thread_id: str, user_id: str):
        """Ensure conversation exists in database for sidebar display"""
        if not self.database_url:
            return
        
        try:
            conn = await asyncpg.connect(self.database_url)
            try:
                # Create tables if they don't exist
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_metadata (
                        thread_id TEXT PRIMARY KEY,
                        title TEXT,
                        auto_generated BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Also create a simple checkpoints table to make conversations appear
                # This mimics what LangGraph would have done
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS checkpoints (
                        thread_id TEXT,
                        checkpoint_id TEXT,
                        checkpoint JSONB,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (thread_id, checkpoint_id)
                    )
                """)
                
                # Check if conversation exists
                exists = await conn.fetchval("""
                    SELECT EXISTS(
                        SELECT 1 FROM checkpoints 
                        WHERE thread_id = $1
                        LIMIT 1
                    )
                """, thread_id)
                
                if not exists:
                    # Create initial checkpoint with empty messages
                    checkpoint_data = {
                        "channel_values": {
                            "messages": []
                        },
                        "initialized": True
                    }
                    await conn.execute("""
                        INSERT INTO checkpoints (thread_id, checkpoint_id, checkpoint, metadata)
                        VALUES ($1, $2, $3, $4)
                    """, thread_id, "init", json.dumps(checkpoint_data), json.dumps({"user_id": user_id}))
                    
                    logger.info(f"Created conversation record for thread_id: {thread_id}")
                
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error ensuring conversation exists: {e}")
    
    async def _save_messages(self, thread_id: str, user_message: str, assistant_response: str):
        """Save conversation messages to database"""
        if not self.database_url:
            return
        
        try:
            conn = await asyncpg.connect(self.database_url)
            try:
                # Get current checkpoint
                row = await conn.fetchrow("""
                    SELECT checkpoint 
                    FROM checkpoints 
                    WHERE thread_id = $1 
                    LIMIT 1
                """, thread_id)
                
                if row:
                    checkpoint = json.loads(row['checkpoint'])
                    messages = checkpoint.get("channel_values", {}).get("messages", [])
                    
                    # Add new messages
                    messages.append({
                        "type": "human",
                        "content": user_message
                    })
                    messages.append({
                        "type": "ai", 
                        "content": assistant_response
                    })
                    
                    # Update checkpoint with new messages
                    checkpoint["channel_values"]["messages"] = messages
                    
                    # Create new checkpoint - use a unique checkpoint_id for each save
                    import time
                    checkpoint_id = f"checkpoint-{int(time.time())}"
                    await conn.execute("""
                        INSERT INTO checkpoints (thread_id, checkpoint_id, checkpoint, metadata)
                        VALUES ($1, $2, $3, $4)
                    """, thread_id, checkpoint_id, json.dumps(checkpoint), json.dumps({"updated_at": datetime.utcnow().isoformat()}))
                    
                    logger.info(f"Saved messages for thread_id: {thread_id}")
                
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Error saving messages: {e}")
    
    @traceable(name="get_routing_decision")
    async def get_routing_decision(self, message: str, state: Dict[str, Any]) -> RoutingDecision:
        """Get LLM's decision on routing"""
        agents_used = state.get("agents_used_this_turn", [])
        agent_results = state.get("agent_results", {})
        
        # Build context from previous agent results
        context = ""
        if agent_results:
            context = "\n\nPrevious agent results this turn:\n"
            for agent_name, result in agent_results.items():
                # Show more of the result (up to 2000 chars) so routing can see what was actually retrieved
                if len(result) > 2000:
                    context += f"- {agent_name}: {result[:2000]}... [truncated, full result available]\n"
                else:
                    context += f"- {agent_name}: {result}\n"
        
        # Add memory context if available
        memory_context = state.get("memory_context", [])
        memory_text = ""
        if memory_context:
            memory_text = "\n\nRelevant user context from memory:\n"
            for memory in memory_context[:3]:  # Top 3 memories
                memory_text += f"- [{memory['category']}] {memory['content']}\n"
        
        routing_prompt = f"""You are an intelligent orchestrator managing specialized agents for an e-commerce system.
{memory_text}

Available agents and their capabilities:
- products: Product search, details, comparisons
- pricing: Price updates, bulk pricing, open box pricing
- inventory: Stock levels, availability checks, inventory updates
- sales: Sales analytics, MAP sales management, reports
- orders: Order data, analytics, summaries
- features: Product features, specifications, variant management
- media: Product images, media management
- integrations: External system integrations (SkuVault, Yotpo, etc.)
- product_mgmt: Product creation, updates, status changes
- utility: General utilities, redirects, memory operations
- graphql: Direct GraphQL API access
- google_workspace: Google Sheets, Docs, Drive operations
- ga4_analytics: Website traffic, visitor analytics, Google Analytics data

User request: {message}

Agents already used this turn: {agents_used}
{context}

Analyze the request and determine:
1. If you have enough information to respond directly (all needed agents have been called)
2. If you need to route to another agent for more information

IMPORTANT RULES:
- For compound requests (e.g., "sales AND traffic"), route to each needed agent sequentially
- Each agent provides part of the answer; orchestrator synthesizes the final response
- Use intelligence-based routing, not keyword matching
- NEVER route to the same agent twice in one turn - if an agent is in "Agents already used", you have its results
- If you have results from all needed agents, you MUST respond with action="respond"
- CAREFULLY EVALUATE agent results - if an agent returned actual data (emails, sales figures, etc.), consider that task COMPLETE
- Don't re-route just because an agent asked for clarification - if it provided data, use what you have
- If an agent says "I can fetch X with parameters Y", that means it HASN'T fetched the data yet

Respond with JSON:
{{
  "action": "route" or "respond",
  "agent_name": "agent_name" (if routing),
  "message": "response to user" (if responding),
  "reasoning": "brief explanation of decision"
}}"""

        try:
            response = await self.model.ainvoke(routing_prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                decision_data = json.loads(json_match.group())
                return RoutingDecision(
                    action=decision_data.get("action", "respond"),
                    agent_name=decision_data.get("agent_name"),
                    message=decision_data.get("message"),
                    reasoning=decision_data.get("reasoning")
                )
        except Exception as e:
            logger.error(f"Error parsing routing decision: {e}")
        
        # Fallback to direct response
        return RoutingDecision(
            action="respond",
            message="I'll help you with that request.",
            reasoning="Failed to parse routing, providing direct response"
        )
    
    @traceable(name="process_agent")
    async def process_agent(self, agent_name: str, state: Dict[str, Any]) -> str:
        """Process a single agent and return its result"""
        if agent_name not in self.agents:
            logger.error(f"Agent {agent_name} not found")
            return f"Error: Agent {agent_name} not available"
        
        agent = self.agents[agent_name]
        logger.info(f"🎯 Routing to {agent_name} agent")
        
        try:
            # Call agent with state
            result = await agent(state)
            
            # Extract response from agent - agents return updated state with messages
            if isinstance(result, dict) and "messages" in result:
                messages = result.get("messages", [])
                # Find the last AI message added by this agent
                for msg in reversed(messages):
                    if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                        if hasattr(msg, 'content') and msg.content:
                            # Check if this is from the current agent
                            metadata = getattr(msg, 'metadata', {})
                            # Only accept messages explicitly from this agent
                            if metadata.get('agent') == agent_name:
                                logger.info(f"✅ Got response from {agent_name}: {msg.content[:100]}...")
                                return msg.content
                
                # If no AI message found, look for any content
                for msg in reversed(messages):
                    if hasattr(msg, 'content') and msg.content:
                        logger.info(f"✅ Got response from {agent_name} (fallback): {msg.content[:100]}...")
                        return msg.content
            
            # Fallback
            logger.warning(f"No proper response from {agent_name}, using fallback")
            return f"Processed request with {agent_name} agent"
            
        except Exception as e:
            logger.error(f"Error calling {agent_name} agent: {e}")
            return f"Error processing request with {agent_name} agent"
    
    @traceable(name="synthesize_response")
    async def synthesize_response(self, state: Dict[str, Any]) -> str:
        """Synthesize final response from all agent results"""
        agent_results = state.get("agent_results", {})
        
        if not agent_results:
            return "I've processed your request."
        
        if len(agent_results) == 1:
            # Single agent response, return it directly
            return next(iter(agent_results.values()))
        
        # Multiple agent responses, synthesize them
        synthesis_prompt = f"""Synthesize these agent responses into a cohesive answer for the user:

{json.dumps(agent_results, indent=2)}

Create a natural, unified response that combines all the information."""

        try:
            response = await self.model.ainvoke(synthesis_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Error synthesizing response: {e}")
            # Fallback: concatenate results
            return "\n\n".join([f"{agent}: {result}" for agent, result in agent_results.items()])
    
    @traceable(name="orchestrate")
    async def orchestrate(self, message: str, thread_id: str = "default", user_id: str = "1"):
        """Main orchestration loop - yields tokens for streaming"""
        # Ensure conversation exists in database
        await self._ensure_conversation_exists(thread_id, user_id)
        
        # Load relevant memories for this conversation
        memory_context = await self._load_memory_context(user_id, message)
        
        # Initialize state
        state = {
            "messages": [HumanMessage(content=message)],
            "user_request": message,
            "thread_id": thread_id,
            "user_id": user_id,
            "agents_used_this_turn": [],
            "agent_results": {},
            "context": {},
            "memory_context": memory_context
        }
        
        max_agents = 5  # Prevent infinite loops
        agents_called = 0
        final_response = ""  # Track the final response for saving
        
        try:
            while agents_called < max_agents:
                # Get routing decision
                routing = await self.get_routing_decision(message, state)
                logger.info(f"Routing decision: {routing.action} - {routing.agent_name or 'direct response'}")
                
                if routing.action == "respond":
                    # Orchestrator has enough info, synthesize and respond
                    if routing.message and len(routing.message) > 20:
                        # Use the direct response from routing
                        final_response = routing.message
                    else:
                        # Synthesize from agent results
                        final_response = await self.synthesize_response(state)
                    
                    # Stream the response
                    for token in final_response.split():
                        yield token + " "
                    
                    # Save messages to database
                    await self._save_messages(thread_id, message, final_response)
                    
                    # Extract memories after conversation
                    state["messages"].append(AIMessage(content=final_response))
                    asyncio.create_task(self._extract_memories(state))
                    break
                
                elif routing.action == "route" and routing.agent_name:
                    # Check if agent was already called
                    if routing.agent_name in state["agents_used_this_turn"]:
                        logger.warning(f"Agent {routing.agent_name} already called this turn, forcing response")
                        # Force a response since the LLM is confused
                        final_response = await self.synthesize_response(state)
                        for token in final_response.split():
                            yield token + " "
                        await self._save_messages(thread_id, message, final_response)
                        state["messages"].append(AIMessage(content=final_response))
                        asyncio.create_task(self._extract_memories(state))
                        break
                    
                    # Route to agent
                    agent_result = await self.process_agent(routing.agent_name, state)
                    
                    # Update state
                    state["agents_used_this_turn"].append(routing.agent_name)
                    state["agent_results"][routing.agent_name] = agent_result
                    state["context"][routing.agent_name] = agent_result
                    
                    agents_called += 1
                    
                    # Continue loop to check if more agents are needed
                    continue
                else:
                    # Unexpected state
                    logger.warning(f"Unexpected routing state: {routing}")
                    yield "I encountered an issue processing your request. Please try again."
                    break
        
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            yield f"An error occurred: {str(e)}"
    
    async def _extract_memories(self, state: Dict[str, Any]):
        """Extract memories from the conversation"""
        try:
            # Extract memories from the conversation
            user_id = state.get("user_id", "1")
            messages = state.get("messages", [])
            
            if not messages:
                return
            
            # Use the memory persistence node to extract memories
            from app.memory.memory_persistence import MemoryExtractionService
            from app.memory.postgres_memory_manager_v2 import SimpleMemoryManager
            
            extraction_service = MemoryExtractionService()
            memory_manager = SimpleMemoryManager()
            
            # Extract memories from conversation
            extracted_memories = await extraction_service.extract_memories_from_conversation(
                messages=messages,
                user_id=user_id
            )
            
            # Save extracted memories
            for memory in extracted_memories:
                try:
                    # Store the memory using the correct method
                    memory_id = await memory_manager.store_memory(memory)
                    if memory_id:
                        logger.info(f"Saved memory #{memory_id}: {memory.content[:50]}...")
                except Exception as e:
                    logger.warning(f"Failed to save memory: {e}")
            
            if extracted_memories:
                logger.info(f"Extracted and saved {len(extracted_memories)} memories for user {user_id}")
            
        except Exception as e:
            logger.error(f"Memory extraction failed: {e}")

# Singleton instance
orchestrator = CustomOrchestrator()

async def get_orchestrator() -> CustomOrchestrator:
    """Get the orchestrator instance"""
    return orchestrator