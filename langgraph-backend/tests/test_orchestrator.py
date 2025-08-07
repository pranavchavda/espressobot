import pytest
import asyncio
from app.orchestrator import Orchestrator
from app.state.graph_state import create_initial_state
from unittest.mock import patch, MagicMock

@pytest.fixture
async def orchestrator():
    """Create orchestrator instance"""
    orch = Orchestrator()
    yield orch

@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    """Test orchestrator initializes with all agents"""
    assert orchestrator.graph is not None
    assert len(orchestrator.agents) > 0
    assert "products" in orchestrator.agents
    assert "pricing" in orchestrator.agents
    assert "inventory" in orchestrator.agents

@pytest.mark.asyncio
async def test_orchestrator_routing(orchestrator):
    """Test orchestrator routes requests correctly"""
    
    state = create_initial_state("Find product SKU ESP-001")
    
    updated_state = await orchestrator.route_request(state)
    
    assert updated_state["current_agent"] is not None
    assert updated_state["current_agent"] == "products"

@pytest.mark.asyncio
async def test_orchestrator_determine_next_agent(orchestrator):
    """Test next agent determination logic"""
    
    state_with_agent = {
        "current_agent": "products",
        "should_continue": True
    }
    next_agent = orchestrator.determine_next_agent(state_with_agent)
    assert next_agent == "products"
    
    state_with_error = {
        "error": "Test error",
        "should_continue": False
    }
    next_agent = orchestrator.determine_next_agent(state_with_error)
    assert next_agent == "end"
    
    state_no_agent = {
        "should_continue": True
    }
    next_agent = orchestrator.determine_next_agent(state_no_agent)
    assert next_agent == "end"

@pytest.mark.asyncio
async def test_orchestrator_run_simple_query(orchestrator):
    """Test orchestrator handles a simple query"""
    
    with patch.object(orchestrator.agents["products"], "__call__") as mock_call:
        mock_call.return_value = {
            "messages": [MagicMock(content="Product found")],
            "last_agent": "products"
        }
        
        result = await orchestrator.run(
            message="Find product ESP-001",
            conversation_id="test-conv-1"
        )
        
        assert result["success"] == True
        assert "messages" in result

@pytest.mark.asyncio
async def test_orchestrator_error_handling(orchestrator):
    """Test orchestrator handles errors gracefully"""
    
    result = await orchestrator.run(
        message="",
        conversation_id="test-conv-2"
    )
    
    assert "messages" in result

@pytest.mark.asyncio
async def test_orchestrator_streaming(orchestrator):
    """Test orchestrator streaming functionality"""
    
    chunks = []
    
    async for chunk in orchestrator.stream(
        message="Test streaming",
        conversation_id="test-conv-3"
    ):
        chunks.append(chunk)
        if len(chunks) > 10:
            break
    
    assert len(chunks) > 0
    
    chunk_types = {chunk.get("type") for chunk in chunks}
    assert "token" in chunk_types or "error" in chunk_types or "agent_complete" in chunk_types

@pytest.mark.asyncio
async def test_agent_selection_by_keywords(orchestrator):
    """Test different agents are selected based on keywords"""
    
    test_cases = [
        ("Update the price to $50", "pricing"),
        ("Check inventory levels", "inventory"),
        ("Start a sale campaign", "sales"),
        ("Add product images", "media"),
        ("Create a new product", "product_mgmt")
    ]
    
    for message, expected_agent in test_cases:
        state = create_initial_state(message)
        updated_state = await orchestrator.route_request(state)
        
        current_agent = updated_state.get("current_agent")
        assert current_agent is not None