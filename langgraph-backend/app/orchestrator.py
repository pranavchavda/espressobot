"""
Progressive Orchestrator - Implements the original vision
User → Orchestrator → Agent1 → Orchestrator → Agent2 → Orchestrator → User
Now with token-efficient compressed context using LangExtract
And full message persistence for conversation continuity
"""
from typing import Dict, Any, List, Optional, AsyncGenerator
import logging
import json
import asyncio
import os
from datetime import datetime
from dataclasses import dataclass, field
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langsmith.run_helpers import traceable
import asyncpg
from app.context_manager.compressed_context_simple import CompressedContextManager, ExtractedContext

logger = logging.getLogger(__name__)
# Set logging level to DEBUG for testing
logger.setLevel(logging.DEBUG)
# Also add console handler to ensure logs are visible
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

@dataclass
class ConversationMemory:
    """Stores important findings from the conversation with compressed context"""
    # Legacy fields for compatibility
    products: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # product_id -> details
    searches_performed: List[Dict[str, Any]] = field(default_factory=list)
    operations_completed: List[Dict[str, Any]] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)  # entity_type -> values
    agent_attempts: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)  # agent -> attempts
    
    # New compressed context from LangExtract
    compressed_context: Optional[ExtractedContext] = None
    recent_messages: List[Any] = field(default_factory=list)  # Keep last few messages for immediate context
    
    def remember_product(self, product_id: str, details: Dict[str, Any]):
        """Remember a product's details"""
        self.products[product_id] = details
        logger.info(f"📝 Remembered product: {product_id} -> {details.get('title', 'Unknown')}")
    
    def remember_search(self, query: str, results: Any):
        """Remember a search that was performed"""
        self.searches_performed.append({
            "query": query,
            "results": results,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def remember_operation(self, operation: str, details: Dict[str, Any]):
        """Remember an operation that was completed"""
        self.operations_completed.append({
            "operation": operation,
            "details": details,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_product_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a product by name from memory"""
        name_lower = name.lower()
        # Check compressed context first - look through all extractions
        if self.compressed_context and self.compressed_context.extractions:
            for class_name, items in self.compressed_context.extractions.items():
                # Look for product-related extraction classes
                if 'product' in class_name.lower():
                    for item in items:
                        text = item.get('text', '')
                        attrs = item.get('attributes', {})
                        if name_lower in text.lower() or name_lower in str(attrs).lower():
                            # Try to extract product info
                            product_id = attrs.get('product_id') or attrs.get('id')
                            title = attrs.get('title') or attrs.get('product_name') or text[:100]
                            if product_id:
                                return {"id": product_id, "title": title, **attrs}
        # Fallback to legacy memory
        for product_id, details in self.products.items():
            if name_lower in details.get('title', '').lower():
                return {"id": product_id, **details}
        return None
    
    def get_compressed_context_string(self, max_tokens: int = 1000) -> str:
        """Get compressed context as a string for the orchestrator"""
        if self.compressed_context:
            return self.compressed_context.to_context_string(max_tokens)
        # Fallback to legacy format
        return self._build_legacy_context()
    
    def _build_legacy_context(self) -> str:
        """Build context from legacy fields"""
        parts = []
        if self.products:
            parts.append("Known products:")
            for pid, details in list(self.products.items())[:5]:
                parts.append(f"  - {pid}: {details.get('title', 'Unknown')}")
        if self.operations_completed:
            parts.append("\nCompleted operations:")
            for op in self.operations_completed[-5:]:
                parts.append(f"  - {op['operation']}: {op['details'].get('response', '')[:100]}")
        return "\n".join(parts) if parts else "No prior context"
    
    def add_recent_message(self, message: Any):
        """Add a message to recent history (keep last 3 for token efficiency)"""
        self.recent_messages.append(message)
        if len(self.recent_messages) > 3:
            self.recent_messages = self.recent_messages[-3:]

@dataclass
class AgentCall:
    """Represents a single agent call with its context"""
    agent_name: str
    task: str
    context: Dict[str, Any]
    attempt_number: int = 1

class ProgressiveOrchestrator:
    """Orchestrator that maintains control between agent calls with compressed context and message persistence"""
    
    def __init__(self):
        self.agents: Dict[str, Any] = {}
        self.conversation_memory: Dict[str, ConversationMemory] = {}  # thread_id -> memory
        self._final_response = None  # Store orchestrator's direct response
        
        # Initialize compressed context manager with fast model
        # Using gpt-4.1-mini as requested (gpt-5 models not yet supported by langextract)
        self.context_manager = CompressedContextManager(model_id="gpt-4.1-mini")
        
        # Get database URL for persistence
        self.database_url = os.getenv("DATABASE_URL")
        
        # Initialize model
        from app.config.agent_model_manager import agent_model_manager
        self.model = agent_model_manager.get_model_for_agent("orchestrator")
        
        # Initialize memory manager for injection and extraction
        self.memory_manager = None
        try:
            from app.memory.postgres_memory_manager_v2 import SimpleMemoryManager
            self.memory_manager = SimpleMemoryManager()
            logger.info("Memory manager initialized for injection and extraction")
        except Exception as e:
            logger.warning(f"Memory manager initialization failed: {e}")
        
        logger.info(f"Initialized Progressive Orchestrator with compressed context and message persistence")
        
        # Initialize all agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all specialist agents"""
        # Use simple MCP agent without LangGraph to avoid async issues
        from app.agents.products_native_mcp_simple import ProductsAgentNativeMCPSimple
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
            ProductsAgentNativeMCPSimple,
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
                logger.info(f"Initialized {agent.name} agent")
            except Exception as e:
                logger.error(f"Failed to initialize {AgentClass.__name__}: {e}")
    
    def _get_memory(self, thread_id: str) -> ConversationMemory:
        """Get or create conversation memory for thread"""
        if thread_id not in self.conversation_memory:
            logger.info(f"Creating new memory for thread {thread_id}")
            self.conversation_memory[thread_id] = ConversationMemory()
        else:
            memory = self.conversation_memory[thread_id]
            logger.info(f"Found existing memory for thread {thread_id}: {len(memory.recent_messages)} messages, compressed_context={memory.compressed_context is not None}")
        return self.conversation_memory[thread_id]
    
    @traceable(name="plan_next_action")
    async def plan_next_action(self, 
                               user_request: str, 
                               memory: ConversationMemory,
                               last_agent_result: Optional[Dict[str, Any]] = None) -> Optional[AgentCall]:
        """Decide what to do next based on current state using compressed context"""
        
        # Inject relevant memories from database
        memory_context = ""
        if self.memory_manager:
            try:
                # Search for memories relevant to the user request
                search_results = await self.memory_manager.search_memories(
                    user_id="1",  # Default user for now
                    query=user_request,
                    limit=3
                )
                
                if search_results:
                    memory_lines = []
                    for result in search_results:
                        mem = result.memory
                        memory_lines.append(f"- {mem.content} (importance: {mem.importance_score:.1f})")
                    memory_context = "Relevant memories:\n" + "\n".join(memory_lines) + "\n\n"
                    logger.info(f"Injected {len(search_results)} relevant memories")
            except Exception as e:
                logger.warning(f"Failed to retrieve memories: {e}")
        
        # Use compressed context if available, otherwise fall back to legacy
        if memory.compressed_context:
            known_context = memory.get_compressed_context_string(max_tokens=500)
            logger.info(f"Using compressed context ({len(known_context)} chars)")
        else:
            known_context = self._build_known_context(memory)
        
        # Build recent conversation history for context
        recent_conversation = ""
        if memory.recent_messages:
            logger.debug(f"Building context from {len(memory.recent_messages)} recent messages")
            # Log the actual size of messages
            for i, msg in enumerate(memory.recent_messages):
                if hasattr(msg, 'content'):
                    msg_content = str(msg.content)
                    logger.warning(f"Message {i} size: {len(msg_content)} chars")
                    if len(msg_content) > 10000:
                        logger.error(f"HUGE MESSAGE FOUND! First 500 chars: {msg_content[:500]}")
            
            recent_conversation = "Recent conversation:\n"
            # Only include last 2 messages (1 exchange) to reduce tokens
            for msg in memory.recent_messages[-2:]:
                if hasattr(msg, 'content'):
                    role = "User" if isinstance(msg, HumanMessage) else "Assistant"
                    # Truncate very long messages more aggressively
                    content = msg.content[:300] + "..." if len(msg.content) > 300 else msg.content
                    recent_conversation += f"{role}: {content}\n"
                    logger.debug(f"Added {role} message to context: {content[:100]}...")
        else:
            logger.warning(f"No recent messages in memory for planning!")
        
        # Build context about last attempt if any
        last_attempt_context = ""
        if last_agent_result:
            last_attempt_context = f"""
Last agent call:
- Agent: {last_agent_result.get('agent', 'unknown')}
- Task: {last_agent_result.get('task', 'unknown')}
- Result: {last_agent_result.get('result', 'No result')[:500]}
"""
        
        # Log the context being used for debugging
        logger.info(f"Planning with context - Recent messages: {len(memory.recent_messages)}, Has compressed context: {memory.compressed_context is not None}")
        if recent_conversation:
            logger.debug(f"Recent conversation preview: {recent_conversation[:200]}...")
        
        planning_prompt = f"""You are an intelligent orchestrator managing specialized agents.

SYSTEM CONTEXT:
- Current date: 2025-08-15
- Default timezone: Eastern Time (when user specifies "Eastern Time", acknowledge and use it)

Current user request: {user_request}

{memory_context}{recent_conversation}

What we already know from this conversation:
{known_context}

{last_attempt_context}

Available agents:
- products: Product searches and information
- pricing: Price updates and management
- inventory: Stock levels and tracking
- sales: Sales analytics and reports
- orders: Order data and analytics
- features: Product features and specifications
- media: Product images and media
- integrations: External systems (SkuVault, Yotpo, etc.)
- product_mgmt: Product creation and updates
- graphql: Direct GraphQL queries
- google_workspace: Gmail, Calendar, Drive, Tasks
- ga4_analytics: Website traffic and analytics

IMPORTANT: Do NOT use the utility agent for memory operations. I handle memory directly.

Based on the user request and what we know so far, determine the next action.

CRITICAL RULES:
1. NEVER make up or hallucinate ANY information - if you don't have it, fetch it
2. Check what information you already have in context before calling agents
3. Only call agents when you need information that's NOT in your context
4. Be smart about context - use what you have, fetch what you don't

SMART CONTEXT USAGE:
- If the context already contains the exact information the user is asking for → respond directly
- If the context has partial information → call agent for only the missing details
- If you have no relevant information in context → call the appropriate agent

For product-related questions:
- Check if compressed_context contains the needed product details (prices, compare_at_price, inventory, etc.)
- If yes → use that information directly (it's recent and accurate)
- If no → call products agent with specific product IDs to get only what's missing
- When calling products agent, be specific: "get pricing details for [product_id]" not "get all details"

IMPORTANT: For simple queries like "find [product name]", if this is the FIRST action and we have no prior context:
- Call the products agent to search for it
- Do NOT respond directly without searching first

For follow-up questions and conversational interactions:
- First check: Do I have this exact information in my compressed context?
- If yes: Use it directly (saves time and tokens)
- If no: Call the appropriate agent for ONLY the missing information
- The context understands references like "it", "the item", "these" from conversation flow

CONVERSATIONAL PATTERNS to handle directly (respond without calling agents):
- User pointing out errors in previous responses: Acknowledge the error and explain/correct
- User providing clarifying information (timezone, preferences): Acknowledge and note for future use
- User asking for clarification about previous responses: Explain using context
- User giving feedback or corrections: Thank them and incorporate the feedback
- Simple acknowledgments, questions about what just happened: Respond directly using conversation context

If we have all necessary information to answer the user, respond with:
{{
  "action": "respond",
  "message": "The complete response to provide to the user, including all details from agent results"
}}

If we need to call an agent for more information, respond with:
{{
  "action": "call_agent",
  "agent": "agent_name",
  "task": "Specific task for the agent",
  "context": {{
    "key": "Any specific context the agent needs",
    "previous_attempts": "What we tried before if relevant"
  }}
}}

Think step by step:
1. What does the user want? (Check if they're referring to something from the recent conversation)
2. What information do we already have from the conversation history?
3. What information do we still need?
4. Can I answer the user completely with current information?
5. If not, which agent can provide the missing information?

IMPORTANT: If the user says things like "the second one", "that", "it", "the second review", etc., look at the recent conversation to understand what they're referring to.

For example:
- If you just listed emails and user says "open the second one" → Open the second email from the list
- If you showed reviews and user says "the second review" → They mean the second item you just showed
- If user refers to "it" or "that" → Look at what was just discussed
- If you showed products WITH prices and user asks "do they have compare prices?" → Check context first, only call agent if compare_at_price not in context
- If user asks "what's in stock?" → Check if inventory data is in context, if not then call products agent

The user is continuing the conversation, not starting a new topic. Use the context!

SMART APPROACH: Check context first → Use what you have → Fetch only what's missing

Respond with JSON."""

        try:
            # DEBUG: Check prompt size
            logger.warning(f"Planning prompt size: {len(planning_prompt)} chars")
            if len(planning_prompt) > 50000:
                logger.error(f"HUGE PROMPT DETECTED! First 1000 chars: {planning_prompt[:1000]}")
            
            # Add timeout for GPT-5 model invocation (GPT-5 is a thinking model and needs time)
            logger.info(f"Invoking GPT-5 thinking model for planning decision...")
            try:
                response = await asyncio.wait_for(self.model.ainvoke(planning_prompt), timeout=60)
                logger.info(f"GPT-5 thinking complete - responded successfully")
            except asyncio.TimeoutError:
                logger.error(f"GPT-5 model invocation timed out after 60 seconds")
                # Fallback to a simple decision if model times out
                return AgentCall(
                    agent_name="products",
                    task=user_request,
                    context={"timeout": True, "fallback": True}
                )
            
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group())
                
                if decision.get("action") == "call_agent":
                    return AgentCall(
                        agent_name=decision.get("agent", "products"),
                        task=decision.get("task", ""),
                        context=decision.get("context", {})
                    )
                elif decision.get("action") == "respond":
                    # Store the response message for later use
                    self._final_response = decision.get("message", "")
                    return None
                else:
                    # Unknown action, stop
                    logger.warning(f"Unknown action: {decision.get('action')}")
                    return None
            
        except Exception as e:
            logger.error(f"Error planning next action: {e}")
        
        # Default fallback
        return None
    
    @traceable(name="call_agent")
    async def call_agent(self, agent_call: AgentCall, memory: ConversationMemory, 
                        user_id: str, thread_id: str) -> Dict[str, Any]:
        """Call a single agent with specific context"""
        
        agent_name = agent_call.agent_name
        if agent_name not in self.agents:
            return {
                "agent": agent_name,
                "task": agent_call.task,
                "success": False,
                "result": f"Agent {agent_name} not found"
            }
        
        agent = self.agents[agent_name]
        logger.info(f"🎯 Calling {agent_name} with task: {agent_call.task}")
        
        # Build state for agent with orchestrator's context
        state = {
            "messages": [
                SystemMessage(content=f"""You are being called by the orchestrator with a specific task.

Task: {agent_call.task}

Context from orchestrator:
{json.dumps(agent_call.context, indent=2)}

Complete this specific task. Be direct and factual in your response."""),
                HumanMessage(content=agent_call.task)
            ],
            "user_id": user_id,
            "thread_id": thread_id,
            "orchestrator_context": agent_call.context
        }
        
        try:
            # Call the agent with longer timeout for complex queries
            logger.info(f"Calling agent {agent_name} with timeout of 60 seconds")
            result = await asyncio.wait_for(agent(state), timeout=60)
            
            # Extract response
            if isinstance(result, dict) and "messages" in result:
                messages = result.get("messages", [])
                logger.debug(f"Agent {agent_name} returned {len(messages)} messages")
                for msg in reversed(messages):
                    if hasattr(msg, '__class__') and msg.__class__.__name__ == 'AIMessage':
                        if hasattr(msg, 'content') and msg.content:
                            metadata = getattr(msg, 'metadata', {})
                            logger.debug(f"Message metadata: {metadata}, looking for agent={agent_name}")
                            if metadata.get('agent') == agent_name:
                                agent_response = msg.content
                                logger.info(f"✅ Got response from {agent_name}: {len(agent_response)} chars")
                                
                                # Track in memory
                                if agent_name not in memory.agent_attempts:
                                    memory.agent_attempts[agent_name] = []
                                memory.agent_attempts[agent_name].append({
                                    "task": agent_call.task,
                                    "response": agent_response,
                                    "attempt": agent_call.attempt_number
                                })
                                
                                # Parse and remember important findings
                                self._extract_findings(agent_name, agent_response, memory)
                                
                                return {
                                    "agent": agent_name,
                                    "task": agent_call.task,
                                    "success": True,
                                    "result": agent_response
                                }
            
            logger.warning(f"❌ No proper response from {agent_name} - messages not found or metadata mismatch")
            return {
                "agent": agent_name,
                "task": agent_call.task,
                "success": False,
                "result": "No response from agent"
            }
            
        except asyncio.TimeoutError:
            logger.error(f"Agent {agent_name} timed out after 60 seconds")
            return {
                "agent": agent_name,
                "task": agent_call.task,
                "success": False,
                "result": "Agent timed out after 60 seconds"
            }
        except Exception as e:
            logger.error(f"Error calling {agent_name}: {e}")
            return {
                "agent": agent_name,
                "task": agent_call.task,
                "success": False,
                "result": f"Error: {str(e)}"
            }
    
    def _extract_findings(self, agent_name: str, response: str, memory: ConversationMemory):
        """Extract and remember important findings from agent response"""
        response_lower = response.lower()
        
        # Extract product IDs and details
        if "gid://shopify/product/" in response_lower:
            import re
            import json
            
            # First try to parse as JSON if it looks like JSON
            if response.strip().startswith('[{') or response.strip().startswith('{'):
                try:
                    # Try to find and parse JSON data
                    json_match = re.search(r'(\[?\{.*\}\]?)', response, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group(1))
                        # Handle both single product and array of products
                        products = data if isinstance(data, list) else [data]
                        for product in products[:10]:  # Limit to first 10 products
                            if isinstance(product, dict):
                                product_id = product.get('id', '')
                                title = product.get('title', 'Unknown')[:100]  # Limit title length
                                if product_id and 'shopify/Product' in product_id:
                                    memory.remember_product(product_id, {"title": title, "found_by": agent_name})
                        return  # Successfully parsed JSON, done
                except (json.JSONDecodeError, TypeError):
                    pass  # Fall back to regex extraction
            
            # Fallback: Extract with regex
            product_ids = re.findall(r'gid://shopify/Product/\d+', response, re.IGNORECASE)
            for product_id in product_ids[:10]:  # Limit to first 10
                # Try to extract associated product name
                lines = response.split('\n')
                for i, line in enumerate(lines):
                    if product_id in line:
                        # Look for product title nearby
                        title = "Unknown"
                        for j in range(max(0, i-2), min(len(lines), i+3)):
                            if 'title' in lines[j].lower() or '-' in lines[j]:
                                # Extract title but limit length to prevent huge strings
                                title = lines[j].strip()[:100]
                                break
                        memory.remember_product(product_id, {"title": title, "found_by": agent_name})
                        break  # Only store once per product ID
        
        # Track searches
        if agent_name == "products" and ("found" in response_lower or "search" in response_lower):
            memory.remember_search(response[:100], response)
        
        # Track operations
        if "success" in response_lower or "completed" in response_lower:
            memory.remember_operation(agent_name, {"response": response[:200]})
    
    def _build_known_context(self, memory: ConversationMemory) -> str:
        """Build a summary of what we know so far"""
        parts = []
        
        if memory.products:
            parts.append("Known products:")
            for product_id, details in memory.products.items():
                parts.append(f"  - {product_id}: {details.get('title', 'Unknown')}")
        
        if memory.operations_completed:
            parts.append("\nCompleted operations:")
            for op in memory.operations_completed[-5:]:  # Last 5 operations
                parts.append(f"  - {op['operation']}: {op['details'].get('response', '')[:100]}")
        
        if memory.searches_performed:
            parts.append("\nSearches performed:")
            for search in memory.searches_performed[-3:]:  # Last 3 searches
                parts.append(f"  - {search['query'][:50]}")
        
        return "\n".join(parts) if parts else "No prior context"
    
    @traceable(name="synthesize_final_response")
    async def synthesize_final_response(self, 
                                       user_request: str,
                                       memory: ConversationMemory,
                                       all_results: List[Dict[str, Any]]) -> str:
        """Create final response from all agent results"""
        
        if not all_results:
            # No agent results; synthesize a helpful response using available context
            try:
                # Build recent conversation snippets
                recent_snippets: List[str] = []
                if getattr(memory, "recent_messages", None):
                    for msg in memory.recent_messages[-4:]:
                        try:
                            role = msg.__class__.__name__.replace("Message", "")
                            recent_snippets.append(f"{role}: {getattr(msg, 'content', '')}")
                        except Exception:
                            pass
                recent_context = "\n".join(recent_snippets)

                # Build compressed context string or legacy known context
                if memory.compressed_context:
                    context_str = memory.compressed_context.to_context_string(max_tokens=800)
                else:
                    context_str = self._build_known_context(memory)

                fallback_prompt = f"""Create a helpful, concise conversational reply for the user using the available context.

User request:
{user_request}

Recent conversation:
{recent_context}

Compressed context:
{context_str}

Guidelines:
- Answer directly using the context above when possible.
- If key information is missing, ask 1-2 specific clarifying questions.
- Keep it friendly, actionable, and avoid generic apologies.

Response:"""

                logger.info("Synthesizing response without agent results using compressed/recent context")
                response = await self.model.ainvoke(fallback_prompt)
                return response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.error(f"Error synthesizing fallback response without agent results: {e}")
                # Last-resort concise clarifying response
                return (
                    "I want to help, but I need a bit more detail. Could you clarify what you'd like me to do next "
                    "(e.g., search products, check inventory, analyze pricing, or summarize the last steps)?"
                )
        
        # Build summary of what was done
        actions_summary = []
        for result in all_results:
            if result.get("success"):
                actions_summary.append(f"- {result['agent']}: {result['task']}")
        
        synthesis_prompt = f"""Create a natural, helpful response to the user's request based on the agent results.

User request: {user_request}

Actions taken:
{chr(10).join(actions_summary)}

Agent results:
{json.dumps(all_results, indent=2)[:3000]}

Create a clear, concise response that:
1. Directly addresses what the user asked for
2. Includes specific details from the agent results
3. Mentions any important IDs or links if relevant
4. Is friendly and conversational

Response:"""

        try:
            response = await self.model.ainvoke(synthesis_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"Error synthesizing response: {e}")
            # Fallback to simple concatenation
            parts = []
            for result in all_results:
                if result.get("success"):
                    parts.append(result.get("result", ""))
            return "\n\n".join(parts)
    
    async def _save_conversation_to_db(self, thread_id: str, user_message: str, assistant_response: str):
        """Save conversation to database so it appears in sidebar"""
        logger.debug(f"Attempting to save conversation {thread_id} to database")
        
        if not self.database_url:
            logger.warning("No DATABASE_URL configured, skipping conversation save")
            return
            
        try:
            logger.debug(f"Connecting to database...")
            conn = await asyncpg.connect(self.database_url)
            try:
                # Check if this is a new conversation (no existing title)
                existing = await conn.fetchrow(
                    "SELECT title FROM conversation_metadata WHERE thread_id = $1",
                    thread_id
                )
                
                if existing and existing['title']:
                    # Already has a title, just update timestamp
                    await conn.execute(
                        """
                        UPDATE conversation_metadata 
                        SET updated_at = CURRENT_TIMESTAMP
                        WHERE thread_id = $1
                        """,
                        thread_id
                    )
                else:
                    # Generate a proper title for new conversation using TitleGenerator
                    try:
                        from app.api.title_generator import get_title_generator
                        generator = get_title_generator()
                        generated_title = await asyncio.wait_for(
                            generator.generate_title(user_message),
                            timeout=5.0
                        )
                        title = generated_title
                        logger.info(f"📝 Generated title: {title}")
                    except asyncio.TimeoutError:
                        logger.warning("Title generation timed out, using fallback")
                        title = user_message[:50] + "..." if len(user_message) > 50 else user_message
                    except Exception as e:
                        logger.warning(f"Title generation failed: {e}, using fallback")
                        title = user_message[:50] + "..." if len(user_message) > 50 else user_message
                    
                    # Save with generated or fallback title
                    await conn.execute(
                        """
                        INSERT INTO conversation_metadata (thread_id, title, auto_generated, updated_at)
                        VALUES ($1, $2, TRUE, CURRENT_TIMESTAMP)
                        ON CONFLICT (thread_id) 
                        DO UPDATE SET 
                            title = EXCLUDED.title,
                            auto_generated = TRUE,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        thread_id,
                        title
                    )
                logger.info(f"✅ Successfully saved conversation {thread_id} to database")
            finally:
                await conn.close()
                logger.debug(f"Database connection closed")
        except Exception as e:
            logger.error(f"❌ Failed to save conversation to database: {e}", exc_info=True)
    
    async def _save_messages_to_db(self, thread_id: str, user_message: str, assistant_response: str):
        """Save individual messages to database for conversation history"""
        if not self.database_url:
            return
            
        try:
            conn = await asyncpg.connect(self.database_url)
            try:
                # Create messages table if it doesn't exist
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS progressive_messages (
                        id SERIAL PRIMARY KEY,
                        thread_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata JSONB DEFAULT '{}'::jsonb
                    );
                    CREATE INDEX IF NOT EXISTS idx_progressive_messages_thread_id 
                    ON progressive_messages(thread_id);
                """)
                
                # Save user message
                await conn.execute("""
                    INSERT INTO progressive_messages (thread_id, role, content, created_at)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                """, thread_id, "user", user_message)
                
                # Save assistant response
                await conn.execute("""
                    INSERT INTO progressive_messages (thread_id, role, content, created_at)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                """, thread_id, "assistant", assistant_response)
                
                logger.info(f"✅ Saved messages for thread {thread_id}")
                
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Failed to save messages: {e}")
    
    async def _load_messages_from_db(self, thread_id: str) -> List[Any]:
        """Load previous messages for a thread from database"""
        if not self.database_url:
            return []
            
        try:
            conn = await asyncpg.connect(self.database_url)
            try:
                rows = await conn.fetch("""
                    SELECT role, content, created_at 
                    FROM progressive_messages 
                    WHERE thread_id = $1
                    ORDER BY created_at DESC
                    LIMIT 6
                """, thread_id)
                
                # Reverse to get chronological order (we selected DESC for most recent)
                rows = list(reversed(rows)) if rows else []
                
                messages = []
                for row in rows:
                    if row['role'] == 'user':
                        messages.append(HumanMessage(content=row['content']))
                    elif row['role'] == 'assistant':
                        messages.append(AIMessage(content=row['content']))
                
                if messages:
                    logger.info(f"📚 Loaded {len(messages)} historical messages for thread {thread_id}")
                
                return messages
                
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"Failed to load messages: {e}")
            return []
    
    @traceable(name="orchestrate_progressive")
    async def orchestrate(self, message: str, thread_id: str = "default", user_id: str = "1"):
        """Main orchestration loop - progressive agent calling with compressed context and message persistence"""
        
        # Get or create memory for this thread
        memory = self._get_memory(thread_id)
        
        # Load historical messages if this is an existing conversation
        if not memory.recent_messages:
            historical_messages = await self._load_messages_from_db(thread_id)
            if historical_messages:
                memory.recent_messages = historical_messages[-3:]  # Keep only last 3 for token efficiency
                logger.info(f"📚 Restored conversation context with {len(memory.recent_messages)} recent messages")
        
        # Add user message to recent history
        memory.add_recent_message(HumanMessage(content=message))
        
        # Reset final response for this orchestration
        self._final_response = None
        
        # Track all results
        all_results = []
        max_agents = 5  # Allow up to 5 agent calls for complex tasks
        agents_called = 0
        agent_results_dict = {}  # For compression
        same_agent_retries = 0  # Track consecutive retries of same agent
        last_agent_called = None
        
        # Main orchestration loop
        while agents_called < max_agents:
            # Plan next action
            last_result = all_results[-1] if all_results else None
            agent_call = await self.plan_next_action(message, memory, last_result)
            
            if not agent_call:
                # Orchestrator has enough info or decided to respond directly
                logger.info("Orchestrator has sufficient information, creating response")
                break
            
            # Check if we're retrying the same agent too many times
            if agent_call.agent_name == last_agent_called:
                same_agent_retries += 1
                if same_agent_retries >= 4:  # Allow up to 4 retries for same agent
                    logger.warning(f"Agent {agent_call.agent_name} failed {same_agent_retries} times, stopping retries")
                    break
            else:
                same_agent_retries = 0
                last_agent_called = agent_call.agent_name
            
            # Call the agent
            result = await self.call_agent(agent_call, memory, user_id, thread_id)
            all_results.append(result)
            agents_called += 1
            
            # Track for compression
            if result.get("success"):
                agent_results_dict[result["agent"]] = result.get("result", "")
            
            # Check if the agent succeeded
            if not result.get("success"):
                # Agent failed, track the failure
                logger.warning(f"Agent {agent_call.agent_name} failed: {result.get('result', 'unknown error')}")
                # Don't retry infinitely - treat failure as a result and let orchestrator decide
                # The orchestrator will see the failure in all_results and can decide what to do
                if agents_called >= 3:
                    logger.error(f"Tried {agents_called} agents, stopping to avoid infinite loop")
                    break
        
        # Determine final response
        if self._final_response:
            # Orchestrator decided to respond directly without calling agents
            # or after getting sufficient info from agents
            final_response = self._final_response
            logger.info("Using orchestrator's direct response")
        else:
            # Synthesize from agent results
            final_response = await self.synthesize_final_response(message, memory, all_results)
        
        # Add assistant response to recent history
        memory.add_recent_message(AIMessage(content=final_response))
        
        # Compress this turn's context using LangExtract
        try:
            logger.info(f"Compressing turn context with {len(agent_results_dict)} agent results")
            compressed = await self.context_manager.compress_turn(
                thread_id=thread_id,
                messages=memory.recent_messages,
                agent_results=agent_results_dict
            )
            memory.compressed_context = compressed
            
            # Log the compressed context for debugging
            if compressed:
                logger.info(f"📊 Compressed context: {compressed.extraction_count} items in {len(compressed.extraction_classes)} categories")
                logger.debug(f"Compressed context classes: {compressed.extraction_classes}")
                if compressed.extractions:
                    # Show sample of what was extracted
                    for class_name in list(compressed.extraction_classes)[:3]:
                        items = compressed.extractions.get(class_name, [])
                        logger.debug(f"  {class_name}: {len(items)} items")
            else:
                logger.warning("❌ Compressed context is None!")
            
            # Clear old context periodically to prevent unbounded growth
            if agents_called > 0 and agents_called % 10 == 0:
                self.context_manager.clear_old_context(thread_id)
                
        except Exception as e:
            logger.error(f"Failed to compress context: {e}", exc_info=True)
        
        # Log what we learned this turn
        if memory.compressed_context:
            logger.info(f"Turn complete. Compressed context has {memory.compressed_context.extraction_count} extractions")
        else:
            logger.info(f"Turn complete. Products found: {len(memory.products)}, Operations: {len(memory.operations_completed)}")
        
        # Extract and save memories BEFORE returning response
        # This ensures memory extraction happens even if response streaming fails
        if self.memory_manager:
            logger.info(f"Starting memory extraction for user {user_id}")
        else:
            logger.warning("Memory manager is None, skipping memory extraction")
            
        if self.memory_manager:
            try:
                from app.memory.memory_persistence import MemoryExtractionService
                
                extraction_service = MemoryExtractionService()
                logger.info("Memory extraction service initialized")
                
                # Build conversation for extraction using proper message objects
                messages_for_extraction = []
                
                # Add recent history if available
                if memory.recent_messages:
                    # Add last 2 exchanges from history
                    messages_for_extraction.extend(memory.recent_messages[-4:])
                
                # Add current exchange
                messages_for_extraction.append(HumanMessage(content=message))
                messages_for_extraction.append(AIMessage(content=final_response))
                
                logger.info(f"Extracting from {len(messages_for_extraction)} messages. Latest: User: {message[:100]}... Assistant: {final_response[:100]}...")
                
                # Extract memories
                logger.info(f"Extracting memories from {len(messages_for_extraction)} messages")
                extracted_memories = await extraction_service.extract_memories_from_conversation(
                    messages=messages_for_extraction,
                    user_id="1"  # Default user for now
                )
                logger.info(f"Extracted {len(extracted_memories)} memories")
                
                # Save extracted memories
                saved_count = 0
                for mem in extracted_memories:
                    logger.info(f"Attempting to save memory: {mem.content[:50]}...")
                    try:
                        memory_id = await self.memory_manager.store_memory(mem)
                        if memory_id:
                            saved_count += 1
                            logger.info(f"💾 Saved memory #{memory_id}: {mem.content[:50]}...")
                    except Exception as e:
                        logger.warning(f"Failed to save memory: {e}")
                
                if saved_count > 0:
                    logger.info(f"✅ Extracted and saved {saved_count} memories from conversation")
                    
            except Exception as e:
                logger.error(f"Memory extraction failed: {e}")
        
        # Save conversation metadata to database (for sidebar) AFTER memory extraction
        await self._save_conversation_to_db(thread_id, message, final_response)
        
        # Save individual messages for history
        await self._save_messages_to_db(thread_id, message, final_response)
        
        # Return response as generator for streaming
        for token in final_response.split():
            yield token + " "

# Singleton instance
orchestrator = ProgressiveOrchestrator()

async def get_orchestrator() -> ProgressiveOrchestrator:
    """Get the orchestrator instance"""
    return orchestrator