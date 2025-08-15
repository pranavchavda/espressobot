from typing import List, Optional, Any, Dict, Annotated
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class GraphState(TypedDict):
    """State schema for the conversation graph"""
    
    messages: Annotated[List[BaseMessage], add_messages]
    
    conversation_id: Optional[str]
    
    user_id: Optional[str]
    
    current_agent: Optional[str]
    
    last_agent: Optional[str]
    
    context: Dict[str, Any]
    
    metadata: Dict[str, Any]
    
    error: Optional[str]
    
    should_continue: bool
    
    tools_output: Optional[Dict[str, Any]]
    
    memory: Optional[Dict[str, Any]]
    
    # New memory-related fields
    memory_context: Optional[List[Any]]  # Relevant memories for current conversation
    
    prompt_fragments: Optional[List[Any]]  # Relevant prompt fragments
    
    context_tier: Optional[str]  # Context tier: 'core', 'standard', 'full'
    
    memory_search_query: Optional[str]  # Last memory search query
    
    consolidated_context: bool  # Whether context was consolidated

    # Orchestrator multi-hop fields
    next_agent: Optional[str]  # Explicit next agent for forced handoff
    hop_count: int  # Number of hops taken in this run
    handoff_reason: Optional[str]  # Why the orchestrator/agent requested a handoff
    handoff_context: Optional[Dict[str, Any]]  # Structured context for the next agent
    
    # A2A orchestration tracking
    agents_used_this_turn: Optional[List[str]]  # Track which agents have been used in this turn
    planned_agents: Optional[List[str]]  # Planned sequence of agents for multi-agent tasks
    routing_reason: Optional[str]  # Reason for current routing decision
    thread_id: Optional[str]  # Thread ID for streaming
    agent_context: Optional[Dict[str, Any]]  # Context passed to agents

def create_initial_state(
    user_message: str,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None
) -> GraphState:
    """Create initial state for a new conversation"""
    
    from langchain_core.messages import HumanMessage
    
    return GraphState(
        messages=[HumanMessage(content=user_message)],
        conversation_id=conversation_id,
        user_id=user_id,
        current_agent=None,
        last_agent=None,
        context=context or {},
        metadata={},
        error=None,
        should_continue=True,
        tools_output=None,
        memory=None,
        memory_context=None,
        prompt_fragments=None,
        context_tier="standard",
        memory_search_query=None,
        consolidated_context=False,
        next_agent=None,
        hop_count=0,
        handoff_reason=None,
        handoff_context=None,
        agents_used_this_turn=[],
        planned_agents=None,
        routing_reason=None,
        thread_id=None,
        agent_context=None
    )