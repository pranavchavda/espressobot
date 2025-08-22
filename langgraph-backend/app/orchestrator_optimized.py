"""
Optimized Progressive Orchestrator - Addresses EspressoBot's architectural recommendations

Key improvements:
1. Dynamic context persistence with structured state management
2. LangGraph-style state machine with explicit node contracts
3. Structured error handling with retries and exponential backoff
4. Parallel agent execution for independent operations
5. Structured JSON logging for observability
6. Externalized configuration management

User → Orchestrator → Agent1 → Orchestrator → Agent2 → Orchestrator → User
"""
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, AsyncGenerator, Set, Union
from pathlib import Path

import asyncpg
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langsmith.run_helpers import traceable

# Create module logger first
logger = logging.getLogger(__name__)

# Import existing components with fallbacks
try:
    from app.context_manager.compressed_context_simple import CompressedContextManager, ExtractedContext
except ImportError:
    logger.warning("CompressedContextManager not available, using fallback")
    class ExtractedContext:
        def __init__(self):
            self.extractions = {}
        def to_context_string(self, max_tokens=1000):
            return ""
    class CompressedContextManager:
        def __init__(self):
            pass

try:
    from app.db.connection_pool import get_database_pool
except ImportError:
    logger.warning("Database pool not available")
    async def get_database_pool():
        return None

try:
    from app.utils.markdown_formatter import restore_markdown_formatting
except ImportError:
    def restore_markdown_formatting(text):
        return text

try:
    from app.config.agent_model_manager import AgentModelManager
except ImportError:
    logger.warning("AgentModelManager not available")
    class AgentModelManager:
        def __init__(self):
            pass

# ============================================================================
# 1. CONFIGURATION MANAGEMENT (Externalized)
# ============================================================================

@dataclass
class OrchestratorConfig:
    """Externalized configuration for orchestrator behavior"""
    # Context management
    max_context_tokens: int = 1000
    context_compression_threshold: int = 50000
    recent_messages_limit: int = 10
    
    # Agent execution
    max_agent_calls_per_request: int = 5
    agent_timeout_seconds: int = 60
    parallel_execution_threshold: int = 2
    
    # Error handling and retries
    max_retries: int = 3
    base_retry_delay: float = 1.0
    max_retry_delay: float = 30.0
    retry_exponential_base: float = 2.0
    
    # Persistence
    persist_conversations: bool = True
    persist_agent_state: bool = True
    state_storage_type: str = "postgres"  # postgres, sqlite, redis
    
    # Observability
    enable_structured_logging: bool = True
    log_level: str = "INFO"
    trace_all_operations: bool = True
    
    @classmethod
    def from_env(cls) -> 'OrchestratorConfig':
        """Load configuration from environment variables"""
        import os
        return cls(
            max_context_tokens=int(os.getenv('ORCHESTRATOR_MAX_CONTEXT_TOKENS', '1000')),
            context_compression_threshold=int(os.getenv('ORCHESTRATOR_COMPRESSION_THRESHOLD', '50000')),
            recent_messages_limit=int(os.getenv('ORCHESTRATOR_RECENT_MESSAGES_LIMIT', '10')),
            max_agent_calls_per_request=int(os.getenv('ORCHESTRATOR_MAX_AGENT_CALLS', '5')),
            agent_timeout_seconds=int(os.getenv('ORCHESTRATOR_AGENT_TIMEOUT', '60')),
            parallel_execution_threshold=int(os.getenv('ORCHESTRATOR_PARALLEL_THRESHOLD', '2')),
            max_retries=int(os.getenv('ORCHESTRATOR_MAX_RETRIES', '3')),
            base_retry_delay=float(os.getenv('ORCHESTRATOR_BASE_RETRY_DELAY', '1.0')),
            max_retry_delay=float(os.getenv('ORCHESTRATOR_MAX_RETRY_DELAY', '30.0')),
            retry_exponential_base=float(os.getenv('ORCHESTRATOR_RETRY_BASE', '2.0')),
            persist_conversations=os.getenv('ORCHESTRATOR_PERSIST_CONVERSATIONS', 'true').lower() == 'true',
            persist_agent_state=os.getenv('ORCHESTRATOR_PERSIST_AGENT_STATE', 'true').lower() == 'true',
            state_storage_type=os.getenv('ORCHESTRATOR_STATE_STORAGE', 'postgres'),
            enable_structured_logging=os.getenv('ORCHESTRATOR_STRUCTURED_LOGGING', 'true').lower() == 'true',
            log_level=os.getenv('ORCHESTRATOR_LOG_LEVEL', 'INFO'),
            trace_all_operations=os.getenv('ORCHESTRATOR_TRACE_ALL', 'true').lower() == 'true'
        )

# ============================================================================
# 2. STRUCTURED LOGGING (JSON-based observability)
# ============================================================================

class StructuredLogger:
    """JSON-based structured logger for better observability"""
    
    def __init__(self, name: str, config: OrchestratorConfig):
        self.logger = logging.getLogger(name)
        self.config = config
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup structured JSON logging"""
        if self.config.enable_structured_logging:
            # Add JSON formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(getattr(logging, self.config.log_level.upper()))
    
    def log_event(self, event_type: str, **kwargs):
        """Log structured event with JSON metadata"""
        event_data = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        if self.config.enable_structured_logging:
            self.logger.info(json.dumps(event_data))
        else:
            self.logger.info(f"{event_type}: {kwargs}")
    
    def log_agent_call(self, agent_name: str, task: str, duration: float, success: bool, **kwargs):
        """Log agent call with performance metrics"""
        self.log_event(
            "agent_call",
            agent=agent_name,
            task=task[:100],  # Truncate for readability
            duration_seconds=duration,
            success=success,
            **kwargs
        )
    
    def log_state_transition(self, from_state: str, to_state: str, trigger: str, **kwargs):
        """Log state machine transitions"""
        self.log_event(
            "state_transition",
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            **kwargs
        )
    
    def log_error(self, error_type: str, error_message: str, retry_count: int = 0, **kwargs):
        """Log structured error information"""
        self.log_event(
            "error",
            error_type=error_type,
            error_message=error_message,
            retry_count=retry_count,
            **kwargs
        )

# ============================================================================
# 3. STATE MACHINE DEFINITIONS (LangGraph-style)
# ============================================================================

class OrchestratorState(Enum):
    """State machine states for orchestrator workflow"""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING_SINGLE = "executing_single"
    EXECUTING_PARALLEL = "executing_parallel"
    SYNTHESIZING = "synthesizing"
    RESPONDING = "responding"
    ERROR_HANDLING = "error_handling"
    COMPLETED = "completed"

@dataclass
class ExecutionNode:
    """Defines a node in the execution graph with explicit input/output contracts"""
    node_id: str
    agent_name: str
    task: str
    input_contract: Dict[str, Any]
    output_contract: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    parallel_group: Optional[str] = None
    timeout_seconds: Optional[int] = None
    retry_config: Optional[Dict[str, Any]] = None

@dataclass
class OrchestratorWorkflowState:
    """Enhanced state management with explicit transitions"""
    # Core state
    current_state: OrchestratorState = OrchestratorState.INITIALIZING
    thread_id: str = ""
    user_id: str = ""
    user_message: str = ""
    
    # Execution tracking
    execution_graph: List[ExecutionNode] = field(default_factory=list)
    completed_nodes: Set[str] = field(default_factory=set)
    failed_nodes: Set[str] = field(default_factory=set)
    node_results: Dict[str, Any] = field(default_factory=dict)
    
    # Context and memory
    compressed_context: Optional[ExtractedContext] = None
    recent_messages: List[Any] = field(default_factory=list)
    
    # Error handling
    error_count: int = 0
    last_error: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    
    # Performance tracking
    start_time: float = 0.0
    agent_call_count: int = 0
    total_tokens_used: int = 0
    
    # Final output
    final_response: str = ""
    response_agent: str = "orchestrator"

# ============================================================================
# 4. ERROR HANDLING WITH RETRIES
# ============================================================================

class OrchestratorError(Exception):
    """Base exception for orchestrator errors"""
    def __init__(self, message: str, error_type: str = "general", retryable: bool = True):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable

class AgentTimeoutError(OrchestratorError):
    """Agent execution timeout"""
    def __init__(self, agent_name: str, timeout: int):
        super().__init__(f"Agent {agent_name} timed out after {timeout} seconds", "timeout", True)

class AgentExecutionError(OrchestratorError):
    """Agent execution failure"""
    def __init__(self, agent_name: str, error: str):
        super().__init__(f"Agent {agent_name} failed: {error}", "execution", True)

class RetryHandler:
    """Handles retries with exponential backoff"""
    
    def __init__(self, config: OrchestratorConfig, logger: StructuredLogger):
        self.config = config
        self.logger = logger
    
    async def execute_with_retry(self, operation_name: str, operation_func, *args, **kwargs):
        """Execute operation with exponential backoff retry"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = time.time()
                result = await operation_func(*args, **kwargs)
                duration = time.time() - start_time
                
                self.logger.log_event(
                    "operation_success",
                    operation=operation_name,
                    attempt=attempt + 1,
                    duration_seconds=duration
                )
                return result
                
            except Exception as e:
                last_exception = e
                duration = time.time() - start_time
                
                # Determine if error is retryable
                retryable = isinstance(e, OrchestratorError) and e.retryable
                if not retryable or attempt >= self.config.max_retries:
                    self.logger.log_error(
                        error_type=type(e).__name__,
                        error_message=str(e),
                        retry_count=attempt,
                        operation=operation_name,
                        duration_seconds=duration,
                        final_attempt=True
                    )
                    raise
                
                # Calculate delay for next attempt
                delay = min(
                    self.config.base_retry_delay * (self.config.retry_exponential_base ** attempt),
                    self.config.max_retry_delay
                )
                
                self.logger.log_error(
                    error_type=type(e).__name__,
                    error_message=str(e),
                    retry_count=attempt,
                    operation=operation_name,
                    duration_seconds=duration,
                    retry_delay_seconds=delay,
                    final_attempt=False
                )
                
                await asyncio.sleep(delay)
        
        # Should never reach here, but just in case
        raise last_exception

# ============================================================================
# 5. DYNAMIC CONTEXT PERSISTENCE
# ============================================================================

class StatePersistenceManager:
    """Manages persistent state storage with pluggable backends"""
    
    def __init__(self, config: OrchestratorConfig, logger: StructuredLogger):
        self.config = config
        self.logger = logger
        self.backend = self._create_backend()
    
    def _create_backend(self):
        """Create appropriate storage backend"""
        if self.config.state_storage_type == "postgres":
            return PostgresStateBackend(self.config, self.logger)
        elif self.config.state_storage_type == "sqlite":
            return SQLiteStateBackend(self.config, self.logger)
        elif self.config.state_storage_type == "redis":
            return RedisStateBackend(self.config, self.logger)
        else:
            return InMemoryStateBackend(self.config, self.logger)
    
    async def save_workflow_state(self, state: OrchestratorWorkflowState):
        """Save workflow state to persistent storage"""
        if self.config.persist_agent_state:
            await self.backend.save_workflow_state(state)
    
    async def load_workflow_state(self, thread_id: str) -> Optional[OrchestratorWorkflowState]:
        """Load workflow state from persistent storage"""
        if self.config.persist_agent_state:
            return await self.backend.load_workflow_state(thread_id)
        return None
    
    async def save_conversation_memory(self, thread_id: str, messages: List[Any], context: Optional[ExtractedContext]):
        """Save conversation memory"""
        if self.config.persist_conversations:
            await self.backend.save_conversation_memory(thread_id, messages, context)
    
    async def load_conversation_memory(self, thread_id: str) -> tuple[List[Any], Optional[ExtractedContext]]:
        """Load conversation memory"""
        if self.config.persist_conversations:
            return await self.backend.load_conversation_memory(thread_id)
        return [], None

class PostgresStateBackend:
    """PostgreSQL-based state persistence"""
    
    def __init__(self, config: OrchestratorConfig, logger: StructuredLogger):
        self.config = config
        self.logger = logger
    
    async def save_workflow_state(self, state: OrchestratorWorkflowState):
        """Save to PostgreSQL"""
        try:
            pool = await get_database_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO orchestrator_workflow_states 
                    (thread_id, state_data, updated_at)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (thread_id) 
                    DO UPDATE SET state_data = $2, updated_at = $3
                """, state.thread_id, json.dumps(state.__dict__, default=str), datetime.utcnow())
                
        except Exception as e:
            self.logger.log_error("state_persistence", f"Failed to save workflow state: {e}")
    
    async def load_workflow_state(self, thread_id: str) -> Optional[OrchestratorWorkflowState]:
        """Load from PostgreSQL"""
        try:
            pool = await get_database_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT state_data FROM orchestrator_workflow_states WHERE thread_id = $1",
                    thread_id
                )
                if row:
                    # Reconstruct state object
                    # This would need proper deserialization logic
                    pass
        except Exception as e:
            self.logger.log_error("state_persistence", f"Failed to load workflow state: {e}")
        return None
    
    async def save_conversation_memory(self, thread_id: str, messages: List[Any], context: Optional[ExtractedContext]):
        """Save conversation memory to PostgreSQL"""
        pass  # Implementation would go here
    
    async def load_conversation_memory(self, thread_id: str) -> tuple[List[Any], Optional[ExtractedContext]]:
        """Load conversation memory from PostgreSQL"""
        return [], None  # Implementation would go here

class SQLiteStateBackend:
    """SQLite-based state persistence for lightweight deployments"""
    pass  # Implementation would go here

class RedisStateBackend:
    """Redis-based state persistence for high-performance deployments"""
    pass  # Implementation would go here

class InMemoryStateBackend:
    """In-memory state persistence (fallback)"""
    def __init__(self, config: OrchestratorConfig, logger: StructuredLogger):
        self.states = {}
        self.conversations = {}
    
    async def save_workflow_state(self, state: OrchestratorWorkflowState):
        self.states[state.thread_id] = state
    
    async def load_workflow_state(self, thread_id: str) -> Optional[OrchestratorWorkflowState]:
        return self.states.get(thread_id)
    
    async def save_conversation_memory(self, thread_id: str, messages: List[Any], context: Optional[ExtractedContext]):
        self.conversations[thread_id] = (messages, context)
    
    async def load_conversation_memory(self, thread_id: str) -> tuple[List[Any], Optional[ExtractedContext]]:
        return self.conversations.get(thread_id, ([], None))

# ============================================================================
# 6. OPTIMIZED ORCHESTRATOR IMPLEMENTATION
# ============================================================================

class OptimizedProgressiveOrchestrator:
    """
    Optimized orchestrator implementing EspressoBot's architectural recommendations
    """
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        self.config = config or OrchestratorConfig.from_env()
        self.logger = StructuredLogger("OptimizedOrchestrator", self.config)
        self.retry_handler = RetryHandler(self.config, self.logger)
        self.state_manager = StatePersistenceManager(self.config, self.logger)
        
        # Agent management
        self.agents = {}
        self.agent_model_manager = AgentModelManager()
        
        # Context management
        self.context_manager = CompressedContextManager()
        
        # Workflow states
        self.active_workflows: Dict[str, OrchestratorWorkflowState] = {}
        
        # Initialize agents
        self._initialize_agents()
        
        self.logger.log_event("orchestrator_initialized", config=self.config.__dict__)
    
    def _initialize_agents(self):
        """Initialize all available agents using the existing agent system"""
        self.logger.log_event("agents_initialization_started")
        
        # Import all the existing static agents (same as original orchestrator)
        from app.agents.products_native_mcp import ProductsAgentNativeMCP
        from app.agents.pricing_native_mcp import PricingAgentNativeMCP
        from app.agents.media_native_mcp import MediaAgentNativeMCP
        from app.agents.inventory_native_mcp import InventoryAgentNativeMCP
        from app.agents.sales_native_mcp import SalesAgentNativeMCP
        from app.agents.integrations_native_mcp import IntegrationsAgentNativeMCP
        from app.agents.product_mgmt_native_mcp import ProductManagementAgentNativeMCP
        from app.agents.utility_native_mcp import UtilityAgentNativeMCP
        from app.agents.graphql_native_mcp import GraphQLAgentNativeMCP
        from app.agents.orders_native_mcp import OrdersAgentNativeMCP
        from app.agents.google_workspace_native_mcp import GoogleWorkspaceAgentNativeMCP
        from app.agents.ga4_analytics_native_mcp import GA4AnalyticsAgentNativeMCP
        from app.agents.bash_agent import BashAgent
        
        static_agent_classes = [
            ProductsAgentNativeMCP,
            PricingAgentNativeMCP,
            MediaAgentNativeMCP,
            InventoryAgentNativeMCP,
            SalesAgentNativeMCP,
            IntegrationsAgentNativeMCP,
            ProductManagementAgentNativeMCP,
            UtilityAgentNativeMCP,
            GraphQLAgentNativeMCP,
            OrdersAgentNativeMCP,
            GoogleWorkspaceAgentNativeMCP,
            GA4AnalyticsAgentNativeMCP,
            BashAgent
        ]
        
        for AgentClass in static_agent_classes:
            try:
                agent = AgentClass()
                self.agents[agent.name] = agent
                self.logger.log_event("agent_initialized", agent_name=agent.name, agent_type="static")
            except Exception as e:
                self.logger.log_error("agent_initialization", f"Failed to initialize {AgentClass.__name__}: {e}")
        
        # Also initialize dynamic agents in background (same as original)
        asyncio.create_task(self._initialize_dynamic_agents_async())
    
    async def _initialize_dynamic_agents_async(self):
        """Initialize dynamic agents from database (same as original orchestrator)"""
        try:
            self.logger.log_event("loading_dynamic_agents_started")
            
            from app.database.session import AsyncSessionLocal
            from app.agents.dynamic_agent import DynamicAgentFactory
            
            async with AsyncSessionLocal() as db:
                # Get all active dynamic agents
                available_agents = await DynamicAgentFactory.list_available_agents(db)
                self.logger.log_event("dynamic_agents_found", count=len(available_agents))
                
                # Load each dynamic agent
                for agent_info in available_agents:
                    agent_name = agent_info['name']
                    try:
                        agent = await DynamicAgentFactory.create_from_database(db, agent_name)
                        
                        if agent:
                            # Add to orchestrator's agent registry
                            self.agents[agent.name] = agent
                            self.logger.log_event("dynamic_agent_initialized", 
                                                agent_name=agent.name, 
                                                description=agent_info.get('description', 'No description'))
                        else:
                            self.logger.log_error("dynamic_agent_creation_failed", f"Failed to create dynamic agent: {agent_name}")
                    
                    except Exception as e:
                        self.logger.log_error("dynamic_agent_error", f"Error loading dynamic agent {agent_name}: {e}")
                        continue
            
            total_agents = len(self.agents)
            static_count = len([a for a in self.agents.values() if not hasattr(a, 'config')])
            dynamic_count = total_agents - static_count
            self.logger.log_event("agent_initialization_complete", 
                                static_count=static_count, 
                                dynamic_count=dynamic_count, 
                                total_count=total_agents)
            
        except Exception as e:
            self.logger.log_error("dynamic_agent_initialization", f"Failed to initialize dynamic agents: {e}")
    
    @traceable(name="orchestrate_optimized")
    async def orchestrate(self, message: str, thread_id: str = "default", user_id: str = "1") -> AsyncGenerator[str, None]:
        """
        Main orchestration loop with optimized architecture
        """
        workflow_state = OrchestratorWorkflowState(
            thread_id=thread_id,
            user_id=user_id,
            user_message=message,
            start_time=time.time()
        )
        
        self.active_workflows[thread_id] = workflow_state
        self.logger.log_event("orchestration_started", thread_id=thread_id, user_message=message[:100])
        
        try:
            # Load existing state if available
            existing_state = await self.state_manager.load_workflow_state(thread_id)
            if existing_state:
                workflow_state = existing_state
                workflow_state.user_message = message
                self.logger.log_event("workflow_state_loaded", thread_id=thread_id)
            
            # Load conversation memory
            messages, context = await self.state_manager.load_conversation_memory(thread_id)
            workflow_state.recent_messages = messages[-self.config.recent_messages_limit:]
            workflow_state.compressed_context = context
            
            # Add current user message
            workflow_state.recent_messages.append(HumanMessage(content=message))
            
            # Execute state machine
            async for token in self._execute_state_machine(workflow_state):
                yield token
                
        except Exception as e:
            self.logger.log_error("orchestration_error", str(e), thread_id=thread_id)
            error_response = f"I encountered an error: {str(e)}. Please try again."
            yield error_response
        
        finally:
            # Save final state
            await self.state_manager.save_workflow_state(workflow_state)
            await self.state_manager.save_conversation_memory(
                thread_id, 
                workflow_state.recent_messages,
                workflow_state.compressed_context
            )
            
            # Cleanup
            if thread_id in self.active_workflows:
                del self.active_workflows[thread_id]
            
            duration = time.time() - workflow_state.start_time
            self.logger.log_event(
                "orchestration_completed",
                thread_id=thread_id,
                duration_seconds=duration,
                agent_calls=workflow_state.agent_call_count,
                tokens_used=workflow_state.total_tokens_used
            )
    
    async def _execute_state_machine(self, state: OrchestratorWorkflowState) -> AsyncGenerator[str, None]:
        """Execute the optimized state machine"""
        
        while state.current_state != OrchestratorState.COMPLETED:
            self.logger.log_state_transition(
                state.current_state.value,
                "pending",
                "state_machine_step",
                thread_id=state.thread_id
            )
            
            if state.current_state == OrchestratorState.INITIALIZING:
                await self._state_initializing(state)
                
            elif state.current_state == OrchestratorState.PLANNING:
                await self._state_planning(state)
                
            elif state.current_state == OrchestratorState.EXECUTING_SINGLE:
                async for token in self._state_executing_single(state):
                    yield token
                    
            elif state.current_state == OrchestratorState.EXECUTING_PARALLEL:
                async for token in self._state_executing_parallel(state):
                    yield token
                    
            elif state.current_state == OrchestratorState.SYNTHESIZING:
                await self._state_synthesizing(state)
                
            elif state.current_state == OrchestratorState.RESPONDING:
                async for token in self._state_responding(state):
                    yield token
                state.current_state = OrchestratorState.COMPLETED
                
            elif state.current_state == OrchestratorState.ERROR_HANDLING:
                await self._state_error_handling(state)
                
            else:
                # Unknown state, exit
                self.logger.log_error("state_machine", f"Unknown state: {state.current_state}")
                break
    
    async def _state_initializing(self, state: OrchestratorWorkflowState):
        """Initialize workflow state"""
        state.current_state = OrchestratorState.PLANNING
        self.logger.log_state_transition("initializing", "planning", "initialization_complete", thread_id=state.thread_id)
    
    async def _state_planning(self, state: OrchestratorWorkflowState):
        """Plan execution graph based on user request"""
        try:
            # Use improved planning logic with dependency analysis
            execution_graph = await self.retry_handler.execute_with_retry(
                "planning",
                self._create_execution_graph,
                state
            )
            
            state.execution_graph = execution_graph
            
            # Determine execution strategy
            if len(execution_graph) == 0:
                # Direct response - set response from routing decision if available
                if not state.final_response:
                    # Get the routing decision to extract direct response
                    routing_decision = await self.retry_handler.execute_with_retry(
                        "routing_for_direct_response",
                        self._intelligent_routing,
                        state.user_message
                    )
                    state.final_response = routing_decision.get("direct_response", "Hello! How can I help you today?")
                state.current_state = OrchestratorState.RESPONDING
            elif len(execution_graph) == 1:
                # Single agent execution
                state.current_state = OrchestratorState.EXECUTING_SINGLE
            else:
                # Check if parallel execution is beneficial
                parallel_groups = self._analyze_parallelism(execution_graph)
                if len(parallel_groups) > 1:
                    state.current_state = OrchestratorState.EXECUTING_PARALLEL
                else:
                    state.current_state = OrchestratorState.EXECUTING_SINGLE
            
            self.logger.log_event(
                "planning_completed",
                thread_id=state.thread_id,
                execution_nodes=len(execution_graph),
                next_state=state.current_state.value
            )
            
        except Exception as e:
            state.last_error = {"type": "planning_error", "message": str(e)}
            state.current_state = OrchestratorState.ERROR_HANDLING
    
    async def _create_execution_graph(self, state: OrchestratorWorkflowState) -> List[ExecutionNode]:
        """Create optimized execution graph using LLM intelligence for routing"""
        # Use LLM to intelligently route the request
        routing_decision = await self._intelligent_routing(state.user_message)
        
        if not routing_decision or not routing_decision.get("agents"):
            return []  # Direct response
        
        execution_nodes = []
        for agent_spec in routing_decision["agents"]:
            node = ExecutionNode(
                node_id=f"{agent_spec['name']}_{len(execution_nodes)}",
                agent_name=agent_spec["name"],
                task=state.user_message,
                input_contract={"request": state.user_message},
                output_contract={"result": "string"}
            )
            execution_nodes.append(node)
        
        return execution_nodes
    
    async def _intelligent_routing(self, user_message: str) -> Dict[str, Any]:
        """Use LLM intelligence to route user requests to appropriate agents"""
        # Get available agents
        available_agents = list(self.agents.keys())
        
        # Create routing prompt
        routing_prompt = f"""
You are an intelligent routing system for EspressoBot, an e-commerce management platform.

Available agents:
{', '.join(available_agents)}

Agent descriptions:
- products: Search and get product information
- pricing: Update prices, costs, discounts
- inventory: Manage stock, quantities, policies
- sales: Handle sales operations, MAP pricing
- features: Manage product features and metafields
- media: Handle images, videos, product media
- integrations: External services, reviews, emails
- product_management: Create, update, modify products
- utility: General calculations, research
- graphql: Direct Shopify API access
- orders: Order analytics, sales data
- google_workspace: Gmail, Calendar, Drive
- ga4_analytics: Website traffic, user behavior
- bash: System commands and operations

User request: "{user_message}"

Based on the user's request, determine which agent(s) should handle this task. Consider:
1. What is the user trying to accomplish?
2. What data or operations are needed?
3. Which agent(s) have the appropriate capabilities?

If the request is a simple greeting or doesn't require specific agent capabilities, return no agents for direct response.

Return JSON format:
{{
    "reasoning": "Brief explanation of your decision",
    "agents": [
        {{"name": "agent_name", "reason": "why this agent is needed"}}
    ],
    "direct_response": "response text if no agents needed"
}}
"""

        try:
            # Use the orchestrator's LLM configuration
            from app.config.llm_factory import LLMFactory
            llm_factory = LLMFactory()
            llm = llm_factory.create_llm("openai/gpt-4o-mini")  # Fast model for routing
            
            response = await llm.ainvoke(routing_prompt)
            
            # Parse JSON response
            import json
            try:
                result = json.loads(response.content.strip())
                return result
            except json.JSONDecodeError:
                # Fallback: try to extract agents from response text
                content = response.content.lower()
                fallback_agents = []
                for agent in available_agents:
                    if agent in content:
                        fallback_agents.append({"name": agent, "reason": "detected in response"})
                
                return {
                    "reasoning": "Fallback parsing",
                    "agents": fallback_agents[:2],  # Limit to 2 agents max
                    "direct_response": None
                }
        
        except Exception as e:
            self.logger.log_error("intelligent_routing", str(e))
            # Even on error, use LLM to generate a response
            try:
                from app.config.llm_factory import LLMFactory
                llm_factory = LLMFactory()
                llm = llm_factory.create_llm("openai/gpt-4o-mini")
                fallback_response = await llm.ainvoke(f"The user said: '{user_message}'. Respond appropriately as EspressoBot, an e-commerce management assistant.")
                return {"reasoning": "Error occurred, fallback response", "agents": [], "direct_response": fallback_response.content}
            except:
                return {"reasoning": "Error occurred", "agents": [], "direct_response": "I'm having some technical difficulties, but I'm here to help! What can I assist you with?"}
    
    def _analyze_parallelism(self, execution_graph: List[ExecutionNode]) -> List[List[str]]:
        """Analyze which nodes can be executed in parallel"""
        # Simple implementation - nodes without dependencies can run in parallel
        parallel_groups = []
        independent_nodes = []
        
        for node in execution_graph:
            if not node.dependencies:
                independent_nodes.append(node.node_id)
        
        if len(independent_nodes) >= self.config.parallel_execution_threshold:
            parallel_groups.append(independent_nodes)
        
        return parallel_groups
    
    async def _state_executing_single(self, state: OrchestratorWorkflowState) -> AsyncGenerator[str, None]:
        """Execute single agent with streaming"""
        if not state.execution_graph:
            state.current_state = OrchestratorState.RESPONDING
            return
        
        node = state.execution_graph[0]
        
        try:
            result = await self.retry_handler.execute_with_retry(
                f"execute_agent_{node.agent_name}",
                self._execute_agent_node,
                node,
                state
            )
            
            state.node_results[node.node_id] = result
            state.completed_nodes.add(node.node_id)
            state.agent_call_count += 1
            
            # Stream partial results if available
            if result.get("streaming_content"):
                for token in result["streaming_content"]:
                    yield token
            
            self.logger.log_agent_call(
                agent_name=node.agent_name,
                task=node.task,
                duration=result.get("duration", 0),
                success=True,
                thread_id=state.thread_id
            )
            
            # For single agent execution, set final response directly
            if len(state.execution_graph) == 1:
                # Extract the actual agent response from the result
                agent_response = result.get("result", "")
                if hasattr(agent_response, 'content'):
                    state.final_response = agent_response.content
                elif isinstance(agent_response, str):
                    state.final_response = agent_response
                else:
                    state.final_response = str(agent_response)
                state.current_state = OrchestratorState.RESPONDING
            else:
                state.current_state = OrchestratorState.SYNTHESIZING
            
        except Exception as e:
            state.failed_nodes.add(node.node_id)
            state.last_error = {"node": node.node_id, "error": str(e)}
            state.current_state = OrchestratorState.ERROR_HANDLING
    
    async def _state_executing_parallel(self, state: OrchestratorWorkflowState) -> AsyncGenerator[str, None]:
        """Execute multiple agents in parallel"""
        
        # Group nodes by parallel execution groups
        parallel_groups = self._analyze_parallelism(state.execution_graph)
        
        for group_nodes in parallel_groups:
            tasks = []
            for node_id in group_nodes:
                node = next(n for n in state.execution_graph if n.node_id == node_id)
                task = self._execute_agent_node(node, state)
                tasks.append((node, task))
            
            # Execute in parallel with timeout
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*[task for _, task in tasks], return_exceptions=True),
                    timeout=self.config.agent_timeout_seconds
                )
                
                # Process results
                for (node, _), result in zip(tasks, results):
                    if isinstance(result, Exception):
                        state.failed_nodes.add(node.node_id)
                        self.logger.log_error("parallel_execution", str(result), node=node.node_id)
                    else:
                        state.node_results[node.node_id] = result
                        state.completed_nodes.add(node.node_id)
                        state.agent_call_count += 1
                        
                        # Stream partial results
                        if result.get("streaming_content"):
                            for token in result["streaming_content"]:
                                yield token
                
                self.logger.log_event(
                    "parallel_execution_completed",
                    thread_id=state.thread_id,
                    successful_nodes=len(state.completed_nodes),
                    failed_nodes=len(state.failed_nodes)
                )
                
            except asyncio.TimeoutError:
                self.logger.log_error("parallel_execution", "Parallel execution timed out")
                state.current_state = OrchestratorState.ERROR_HANDLING
                return
        
        state.current_state = OrchestratorState.SYNTHESIZING
    
    async def _execute_agent_node(self, node: ExecutionNode, state: OrchestratorWorkflowState) -> Dict[str, Any]:
        """Execute a single agent node with timeout and error handling"""
        
        if node.agent_name not in self.agents:
            raise AgentExecutionError(node.agent_name, "Agent not found")
        
        agent = self.agents[node.agent_name]
        start_time = time.time()
        
        try:
            # Build agent context
            agent_state = {
                "messages": [
                    SystemMessage(content=f"Task: {node.task}"),
                    HumanMessage(content=node.task)
                ],
                "user_id": state.user_id,
                "thread_id": state.thread_id,
                "context": node.input_contract
            }
            
            # Execute with timeout
            timeout = node.timeout_seconds or self.config.agent_timeout_seconds
            result = await asyncio.wait_for(
                agent(agent_state),
                timeout=timeout
            )
            
            duration = time.time() - start_time
            
            return {
                "result": result,
                "duration": duration,
                "node_id": node.node_id,
                "agent_name": node.agent_name,
                "success": True
            }
            
        except asyncio.TimeoutError:
            raise AgentTimeoutError(node.agent_name, timeout)
        except Exception as e:
            raise AgentExecutionError(node.agent_name, str(e))
    
    async def _state_synthesizing(self, state: OrchestratorWorkflowState):
        """Synthesize results from multiple agents"""
        try:
            # Combine all agent results into coherent response
            synthesis_result = await self.retry_handler.execute_with_retry(
                "synthesis",
                self._synthesize_agent_results,
                state
            )
            
            state.final_response = synthesis_result
            state.current_state = OrchestratorState.RESPONDING
            
            self.logger.log_event(
                "synthesis_completed",
                thread_id=state.thread_id,
                response_length=len(state.final_response)
            )
            
        except Exception as e:
            state.last_error = {"type": "synthesis_error", "message": str(e)}
            state.current_state = OrchestratorState.ERROR_HANDLING
    
    async def _synthesize_agent_results(self, state: OrchestratorWorkflowState) -> str:
        """Synthesize multiple agent results into coherent response"""
        if not state.node_results:
            return "I don't have specific information to answer your question."
        
        # Simple synthesis for now - would be enhanced with LLM-based synthesis
        results = []
        for node_id, result in state.node_results.items():
            if result.get("result"):
                results.append(str(result["result"]))
        
        return "\\n\\n".join(results) if results else "No results available."
    
    async def _state_responding(self, state: OrchestratorWorkflowState) -> AsyncGenerator[str, None]:
        """Stream final response to user"""
        response = state.final_response or "I apologize, but I couldn't generate a response."
        
        # Add response to conversation memory
        state.recent_messages.append(AIMessage(content=response))
        
        # Stream response character by character for better UX
        for char in response:
            yield char
            await asyncio.sleep(0.001)  # Small delay for streaming effect
    
    async def _state_error_handling(self, state: OrchestratorWorkflowState):
        """Handle errors with appropriate recovery strategies"""
        if state.retry_count < self.config.max_retries:
            state.retry_count += 1
            
            # Determine recovery strategy based on error type
            if state.last_error and "timeout" in state.last_error.get("type", ""):
                # For timeouts, try reducing scope
                state.current_state = OrchestratorState.PLANNING
            else:
                # For other errors, try direct response
                state.final_response = f"I encountered an issue: {state.last_error.get('message', 'Unknown error')}. Let me try a different approach."
                state.current_state = OrchestratorState.RESPONDING
            
            self.logger.log_event(
                "error_recovery_attempted",
                thread_id=state.thread_id,
                retry_count=state.retry_count,
                error_type=state.last_error.get("type"),
                recovery_strategy=state.current_state.value
            )
        else:
            # Max retries exceeded, provide error response
            state.final_response = "I'm experiencing technical difficulties. Please try your request again later."
            state.current_state = OrchestratorState.RESPONDING
            
            self.logger.log_error(
                "max_retries_exceeded",
                "Maximum retry attempts reached",
                thread_id=state.thread_id,
                retry_count=state.retry_count
            )

# ============================================================================
# 7. FACTORY AND SINGLETON
# ============================================================================

_orchestrator_instance = None

async def get_optimized_orchestrator() -> OptimizedProgressiveOrchestrator:
    """Get singleton orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        config = OrchestratorConfig.from_env()
        _orchestrator_instance = OptimizedProgressiveOrchestrator(config)
    return _orchestrator_instance