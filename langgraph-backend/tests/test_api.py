import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio
from app.main import app
from app.database.session import init_db
from unittest.mock import patch, AsyncMock

@pytest.fixture
async def async_client():
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def client():
    """Create sync test client"""
    return TestClient(app)

@pytest.mark.asyncio
async def test_root_endpoint(async_client):
    """Test root endpoint"""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "EspressoBot LangGraph Backend"
    assert data["status"] == "operational"

@pytest.mark.asyncio
async def test_health_endpoint(async_client):
    """Test health check endpoint"""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

@pytest.mark.asyncio
async def test_chat_message_endpoint(async_client):
    """Test chat message endpoint"""
    
    with patch("app.api.chat.get_orchestrator") as mock_get_orch:
        mock_orch = AsyncMock()
        mock_orch.run = AsyncMock(return_value={
            "success": True,
            "messages": [],
            "last_agent": "products"
        })
        mock_get_orch.return_value = mock_orch
        
        response = await async_client.post(
            "/api/agent/message",
            json={
                "message": "Test message",
                "conversation_id": "test-123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "messages" in data

@pytest.mark.asyncio
async def test_list_agents_endpoint(async_client):
    """Test list agents endpoint"""
    
    with patch("app.api.chat.get_orchestrator") as mock_get_orch:
        mock_orch = AsyncMock()
        mock_orch.agents = {
            "products": AsyncMock(name="products", description="Products agent"),
            "pricing": AsyncMock(name="pricing", description="Pricing agent")
        }
        mock_get_orch.return_value = mock_orch
        
        response = await async_client.get("/api/agent/agents")
        
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 2

def test_chat_sse_endpoint(client):
    """Test SSE chat endpoint"""
    
    with patch("app.api.chat.get_orchestrator") as mock_get_orch:
        mock_orch = AsyncMock()
        
        async def mock_stream(*args, **kwargs):
            yield {"type": "token", "content": "Test", "agent": "products"}
            yield {"type": "agent_complete", "agent": "products"}
        
        mock_orch.stream = mock_stream
        mock_get_orch.return_value = mock_orch
        
        response = client.post(
            "/api/agent/sse",
            json={
                "message": "Test SSE",
                "conversation_id": "sse-test"
            },
            headers={"Accept": "text/event-stream"}
        )
        
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_database_initialization():
    """Test database initialization"""
    
    with patch("app.database.session.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.begin = AsyncMock(return_value=mock_conn)
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock()
        mock_conn.run_sync = AsyncMock()
        
        await init_db()
        
        mock_conn.run_sync.assert_called_once()

@pytest.mark.asyncio
async def test_conversation_endpoints(async_client):
    """Test conversation management endpoints"""
    
    with patch("app.api.conversations.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db
        
        response = await async_client.get("/api/conversations/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_auth_register_endpoint(async_client):
    """Test user registration endpoint"""
    
    with patch("app.api.auth.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_get_db.return_value = mock_db
        
        response = await async_client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "name": "Test User"
            }
        )
        
        assert response.status_code in [200, 422]

@pytest.mark.asyncio
async def test_memory_endpoints(async_client):
    """Test memory management endpoints"""
    
    with patch("app.api.memory.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db
        
        response = await async_client.get("/api/memory/")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_dashboard_stats_endpoint(async_client):
    """Test dashboard statistics endpoint"""
    
    with patch("app.api.dashboard.get_db") as mock_get_db:
        mock_db = AsyncMock()
        mock_result = AsyncMock()
        mock_result.scalar.return_value = 10
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_get_db.return_value = mock_db
        
        response = await async_client.get("/api/dashboard/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_conversations" in data