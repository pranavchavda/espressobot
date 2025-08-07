import pytest
import asyncio
from app.agents.products import ProductsAgent
from app.agents.base import BaseAgent
from app.state.graph_state import GraphState, create_initial_state
from langchain_core.messages import HumanMessage, AIMessage

@pytest.fixture
def products_agent():
    return ProductsAgent()

@pytest.mark.asyncio
async def test_products_agent_initialization(products_agent):
    """Test ProductsAgent initializes correctly"""
    assert products_agent.name == "products"
    assert "product search" in products_agent.description.lower()
    assert isinstance(products_agent, BaseAgent)

@pytest.mark.asyncio
async def test_products_agent_keywords(products_agent):
    """Test ProductsAgent responds to appropriate keywords"""
    keywords = products_agent._get_keywords()
    assert "product" in keywords
    assert "sku" in keywords
    assert "espresso" in keywords

@pytest.mark.asyncio
async def test_products_agent_should_handle(products_agent):
    """Test ProductsAgent correctly identifies when to handle requests"""
    
    state_with_product_query = {
        "messages": [HumanMessage(content="Find product SKU ESP-001")]
    }
    assert products_agent.should_handle(state_with_product_query) == True
    
    state_with_coffee_query = {
        "messages": [HumanMessage(content="Show me espresso machines")]
    }
    assert products_agent.should_handle(state_with_coffee_query) == True
    
    state_without_keywords = {
        "messages": [HumanMessage(content="What's the weather today?")]
    }
    assert products_agent.should_handle(state_without_keywords) == False

@pytest.mark.asyncio
async def test_base_agent_process_state():
    """Test base agent state processing"""
    
    class TestAgent(BaseAgent):
        def _get_system_prompt(self) -> str:
            return "Test system prompt"
        
        def _get_keywords(self):
            return ["test"]
        
        def _get_tools(self):
            return []
    
    agent = TestAgent(name="test", description="Test agent")
    
    initial_state = create_initial_state("Test message")
    
    result = await agent(initial_state)
    
    assert "messages" in result
    assert "last_agent" in result
    assert result["last_agent"] == "test"

@pytest.mark.asyncio
async def test_agent_error_handling():
    """Test agent error handling"""
    
    class ErrorAgent(BaseAgent):
        def _get_system_prompt(self) -> str:
            return "Error test"
        
        def _get_keywords(self):
            return ["error"]
        
        def _get_tools(self):
            return []
        
        async def _process_messages(self, messages):
            raise Exception("Test error")
    
    agent = ErrorAgent(name="error", description="Error agent")
    
    state = create_initial_state("Trigger error")
    
    result = await agent(state)
    
    assert "messages" in result
    last_message = result["messages"][-1]
    assert isinstance(last_message, AIMessage)
    assert "error" in last_message.content.lower()
    assert last_message.metadata.get("error") == True