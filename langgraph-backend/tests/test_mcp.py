import pytest
import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock
from app.tools.mcp_client import MCPClient, MCPManager

@pytest.fixture
async def mock_mcp_client():
    """Create a mock MCP client"""
    client = MCPClient("/fake/path/server.py")
    
    mock_process = MagicMock()
    mock_process.returncode = None
    mock_process.stdin = MagicMock()
    mock_process.stdin.write = MagicMock()
    mock_process.stdin.drain = AsyncMock()
    mock_process.stdout = MagicMock()
    mock_process.stderr = MagicMock()
    
    client.process = mock_process
    
    return client

@pytest.mark.asyncio
async def test_mcp_client_initialization():
    """Test MCP client initialization"""
    client = MCPClient("/test/server.py")
    assert client.server_path == "/test/server.py"
    assert client.process is None
    assert client._message_id == 0

@pytest.mark.asyncio
async def test_mcp_client_get_next_id(mock_mcp_client):
    """Test message ID generation"""
    id1 = mock_mcp_client._get_next_id()
    id2 = mock_mcp_client._get_next_id()
    id3 = mock_mcp_client._get_next_id()
    
    assert id1 == 1
    assert id2 == 2
    assert id3 == 3

@pytest.mark.asyncio
async def test_mcp_client_send_request(mock_mcp_client):
    """Test sending requests to MCP server"""
    
    response_data = {"jsonrpc": "2.0", "result": {"success": True}, "id": 1}
    mock_mcp_client.process.stdout.readline = AsyncMock(
        return_value=json.dumps(response_data).encode() + b"\n"
    )
    
    request = {
        "jsonrpc": "2.0",
        "method": "test",
        "params": {},
        "id": 1
    }
    
    response = await mock_mcp_client._send_request(request)
    
    assert response["result"]["success"] == True
    mock_mcp_client.process.stdin.write.assert_called_once()

@pytest.mark.asyncio
async def test_mcp_client_list_tools(mock_mcp_client):
    """Test listing tools from MCP server"""
    
    tools_response = {
        "jsonrpc": "2.0",
        "result": {
            "tools": [
                {"name": "tool1", "description": "Test tool 1"},
                {"name": "tool2", "description": "Test tool 2"}
            ]
        },
        "id": 1
    }
    
    mock_mcp_client.process.stdout.readline = AsyncMock(
        return_value=json.dumps(tools_response).encode() + b"\n"
    )
    
    tools = await mock_mcp_client.list_tools()
    
    assert len(tools) == 2
    assert tools[0]["name"] == "tool1"
    assert tools[1]["name"] == "tool2"

@pytest.mark.asyncio
async def test_mcp_client_call_tool(mock_mcp_client):
    """Test calling a tool on MCP server"""
    
    tool_response = {
        "jsonrpc": "2.0",
        "result": {
            "output": "Tool executed successfully"
        },
        "id": 1
    }
    
    mock_mcp_client.process.stdout.readline = AsyncMock(
        return_value=json.dumps(tool_response).encode() + b"\n"
    )
    
    result = await mock_mcp_client.call_tool("test_tool", {"param": "value"})
    
    assert result["output"] == "Tool executed successfully"

@pytest.mark.asyncio
async def test_mcp_client_error_handling(mock_mcp_client):
    """Test MCP client error handling"""
    
    error_response = {
        "jsonrpc": "2.0",
        "error": {
            "code": -32601,
            "message": "Method not found"
        },
        "id": 1
    }
    
    mock_mcp_client.process.stdout.readline = AsyncMock(
        return_value=json.dumps(error_response).encode() + b"\n"
    )
    
    with pytest.raises(Exception) as exc_info:
        await mock_mcp_client.call_tool("nonexistent_tool", {})
    
    assert "Tool call failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_mcp_manager_initialization():
    """Test MCP manager initialization"""
    manager = MCPManager()
    assert manager.servers == {}
    assert manager._initialized == False
    assert "/python-tools" in manager.base_path

@pytest.mark.asyncio
async def test_mcp_manager_get_tools_for_agent():
    """Test getting tools for specific agent type"""
    manager = MCPManager()
    
    mock_client = MagicMock()
    mock_client.list_tools = AsyncMock(return_value=[
        {"name": "search_products", "description": "Search products"}
    ])
    
    manager.servers["products"] = mock_client
    manager._initialized = True
    
    tools = await manager.get_tools_for_agent("products")
    
    assert len(tools) == 1
    assert tools[0]["name"] == "search_products"

@pytest.mark.asyncio
async def test_mcp_manager_call_tool():
    """Test calling tool through manager"""
    manager = MCPManager()
    
    mock_client = MagicMock()
    mock_client.call_tool = AsyncMock(return_value={"result": "success"})
    
    manager.servers["products"] = mock_client
    manager._initialized = True
    
    result = await manager.call_tool("products", "search_products", {"query": "coffee"})
    
    assert result["result"] == "success"
    mock_client.call_tool.assert_called_once_with("search_products", {"query": "coffee"})

@pytest.mark.asyncio
async def test_mcp_manager_shutdown():
    """Test MCP manager shutdown"""
    manager = MCPManager()
    
    mock_client1 = MagicMock()
    mock_client1.disconnect = AsyncMock()
    mock_client2 = MagicMock()
    mock_client2.disconnect = AsyncMock()
    
    manager.servers = {
        "products": mock_client1,
        "pricing": mock_client2
    }
    manager._initialized = True
    
    await manager.shutdown()
    
    mock_client1.disconnect.assert_called_once()
    mock_client2.disconnect.assert_called_once()
    assert manager.servers == {}
    assert manager._initialized == False