"""
Example of state management and checkpointing in LangGraph.
Shows how to persist conversation state and recover from failures.
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import StateGraph, MessagesState, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.base import BaseCheckpointSaver
import json
import sqlite3
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Define custom state structure
class ConversationState(TypedDict):
    """Enhanced state for conversation management"""
    
    # Core conversation data
    messages: List[Dict[str, Any]]
    conversation_id: str
    user_id: str
    
    # Agent routing and history
    current_agent: Optional[str]
    agent_history: List[str]
    last_agent_response: Optional[str]
    
    # Context and memory
    context: Dict[str, Any]
    memory_results: List[Dict[str, Any]]
    
    # Tool execution tracking
    tool_calls: List[Dict[str, Any]]
    tool_results: Dict[str, Any]
    
    # Performance metrics
    token_count: int
    execution_time: float
    error_count: int
    
    # Checkpoint metadata
    checkpoint_id: Optional[str]
    last_checkpoint: Optional[str]


# Custom checkpoint manager with additional features
class EnhancedCheckpointManager:
    """Enhanced checkpoint management with recovery features"""
    
    def __init__(self, db_path: str = "checkpoints.db"):
        self.db_path = db_path
        self.saver = SqliteSaver.from_conn_string(db_path)
        self._init_db()
        
    def _init_db(self):
        """Initialize additional checkpoint tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create checkpoint metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoint_metadata (
                checkpoint_id TEXT PRIMARY KEY,
                thread_id TEXT NOT NULL,
                conversation_id TEXT,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                agent_state TEXT,
                token_count INTEGER,
                error_count INTEGER
            )
        """)
        
        # Create recovery log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovery_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checkpoint_id TEXT,
                recovery_reason TEXT,
                recovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN
            )
        """)
        
        conn.commit()
        conn.close()
        
    async def save_checkpoint(
        self,
        thread_id: str,
        state: ConversationState,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save checkpoint with metadata"""
        
        # Save to LangGraph checkpoint
        await self.saver.aput(thread_id, state)
        
        # Save metadata
        checkpoint_id = f"{thread_id}_{datetime.utcnow().isoformat()}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO checkpoint_metadata
            (checkpoint_id, thread_id, conversation_id, user_id, agent_state, token_count, error_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            checkpoint_id,
            thread_id,
            state.get("conversation_id"),
            state.get("user_id"),
            json.dumps(state.get("agent_history", [])),
            state.get("token_count", 0),
            state.get("error_count", 0)
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved checkpoint {checkpoint_id}")
        return checkpoint_id
        
    async def load_checkpoint(self, thread_id: str) -> Optional[ConversationState]:
        """Load the latest checkpoint for a thread"""
        
        checkpoint = await self.saver.aget(thread_id)
        
        if checkpoint:
            logger.info(f"Loaded checkpoint for thread {thread_id}")
            return checkpoint.get("state")
            
        return None
        
    async def recover_from_failure(
        self,
        thread_id: str,
        reason: str = "Unknown error"
    ) -> Optional[ConversationState]:
        """Recover from a failure using the last checkpoint"""
        
        logger.info(f"Attempting recovery for thread {thread_id}: {reason}")
        
        # Load last checkpoint
        state = await self.load_checkpoint(thread_id)
        
        if state:
            # Log recovery
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO recovery_log (checkpoint_id, recovery_reason, success)
                VALUES (?, ?, ?)
            """, (f"{thread_id}_recovery", reason, True))
            
            conn.commit()
            conn.close()
            
            # Increment error count
            state["error_count"] = state.get("error_count", 0) + 1
            
            logger.info(f"Successfully recovered thread {thread_id}")
            return state
        else:
            logger.error(f"No checkpoint found for thread {thread_id}")
            return None
            
    def list_checkpoints(self, conversation_id: str) -> List[Dict[str, Any]]:
        """List all checkpoints for a conversation"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT checkpoint_id, thread_id, created_at, token_count, error_count
            FROM checkpoint_metadata
            WHERE conversation_id = ?
            ORDER BY created_at DESC
        """, (conversation_id,))
        
        checkpoints = []
        for row in cursor.fetchall():
            checkpoints.append({
                "checkpoint_id": row[0],
                "thread_id": row[1],
                "created_at": row[2],
                "token_count": row[3],
                "error_count": row[4]
            })
            
        conn.close()
        return checkpoints


# Example LangGraph workflow with checkpointing
class CheckpointedOrchestrator:
    """Orchestrator with automatic checkpointing"""
    
    def __init__(self, checkpoint_manager: EnhancedCheckpointManager):
        self.checkpoint_manager = checkpoint_manager
        self.graph = self._build_graph()
        
    def _build_graph(self):
        """Build the graph with checkpointing"""
        
        # Create graph with custom state
        graph = StateGraph(ConversationState)
        
        # Add nodes
        graph.add_node("save_checkpoint", self.save_checkpoint_node)
        graph.add_node("process_message", self.process_message_node)
        graph.add_node("handle_error", self.handle_error_node)
        
        # Add edges with error handling
        graph.add_edge("START", "save_checkpoint")
        graph.add_edge("save_checkpoint", "process_message")
        graph.add_conditional_edges(
            "process_message",
            self.check_for_errors,
            {
                "error": "handle_error",
                "success": END
            }
        )
        graph.add_edge("handle_error", "save_checkpoint")
        
        # Compile with checkpointing
        return graph.compile(
            checkpointer=self.checkpoint_manager.saver
        )
        
    async def save_checkpoint_node(self, state: ConversationState) -> ConversationState:
        """Node that saves checkpoints"""
        
        thread_id = f"{state['conversation_id']}_{state['user_id']}"
        
        # Save checkpoint
        checkpoint_id = await self.checkpoint_manager.save_checkpoint(
            thread_id,
            state
        )
        
        state["checkpoint_id"] = checkpoint_id
        state["last_checkpoint"] = datetime.utcnow().isoformat()
        
        return state
        
    async def process_message_node(self, state: ConversationState) -> ConversationState:
        """Node that processes messages"""
        
        # Simulate message processing
        last_message = state["messages"][-1]
        
        # Add to agent history
        state["agent_history"].append("process_message")
        
        # Simulate some processing
        response = f"Processed: {last_message['content']}"
        
        state["messages"].append({
            "role": "assistant",
            "content": response
        })
        
        # Update metrics
        state["token_count"] += len(response.split())
        
        return state
        
    async def handle_error_node(self, state: ConversationState) -> ConversationState:
        """Node that handles errors"""
        
        logger.error(f"Handling error in conversation {state['conversation_id']}")
        
        # Increment error count
        state["error_count"] += 1
        
        # Try to recover
        thread_id = f"{state['conversation_id']}_{state['user_id']}"
        recovered_state = await self.checkpoint_manager.recover_from_failure(
            thread_id,
            "Processing error"
        )
        
        if recovered_state:
            # Merge recovered state
            state.update(recovered_state)
            
        return state
        
    def check_for_errors(self, state: ConversationState) -> str:
        """Check if there were errors in processing"""
        
        # Simulate error detection
        if state.get("error_count", 0) > 3:
            return "error"
        return "success"
        
    async def run_with_recovery(
        self,
        initial_state: ConversationState,
        thread_id: str
    ) -> ConversationState:
        """Run the graph with automatic recovery"""
        
        try:
            # Try to run normally
            result = await self.graph.ainvoke(
                initial_state,
                config={"configurable": {"thread_id": thread_id}}
            )
            return result
            
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            
            # Attempt recovery
            recovered_state = await self.checkpoint_manager.recover_from_failure(
                thread_id,
                str(e)
            )
            
            if recovered_state:
                # Retry with recovered state
                return await self.graph.ainvoke(
                    recovered_state,
                    config={"configurable": {"thread_id": thread_id}}
                )
            else:
                raise


# Example usage
async def example_usage():
    """Example of using checkpointed orchestrator"""
    
    # Initialize checkpoint manager
    checkpoint_manager = EnhancedCheckpointManager("conversation_checkpoints.db")
    
    # Create orchestrator
    orchestrator = CheckpointedOrchestrator(checkpoint_manager)
    
    # Create initial state
    initial_state = ConversationState(
        messages=[
            {"role": "user", "content": "Find product ESP-001"}
        ],
        conversation_id="conv_123",
        user_id="user_456",
        current_agent=None,
        agent_history=[],
        last_agent_response=None,
        context={},
        memory_results=[],
        tool_calls=[],
        tool_results={},
        token_count=0,
        execution_time=0.0,
        error_count=0,
        checkpoint_id=None,
        last_checkpoint=None
    )
    
    # Run with automatic checkpointing and recovery
    thread_id = f"{initial_state['conversation_id']}_{initial_state['user_id']}"
    
    result = await orchestrator.run_with_recovery(
        initial_state,
        thread_id
    )
    
    print(f"Final state: {json.dumps(result, indent=2)}")
    
    # List checkpoints
    checkpoints = checkpoint_manager.list_checkpoints("conv_123")
    print(f"\nCheckpoints: {json.dumps(checkpoints, indent=2)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())