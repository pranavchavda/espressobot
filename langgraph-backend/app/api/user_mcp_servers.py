"""
API endpoints for user MCP server management
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json

from app.database.session import get_db
from app.database.models import UserMCPServer, MCPServerTool, MCPServerStatus
from app.services.user_mcp_service import get_user_mcp_service

router = APIRouter(prefix="/api/user-mcp-servers", tags=["user-mcp-servers"])


# Request/Response models
class AddMCPServerRequest(BaseModel):
    name: str = Field(..., description="Unique name for this server")
    display_name: str = Field(..., description="Display name")
    description: Optional[str] = None
    server_type: str = Field("stdio", description="Server type: stdio, sse, http")
    connection_config: Dict[str, Any] = Field(..., description="Connection configuration")
    requires_auth: bool = False
    auth_config: Optional[Dict[str, Any]] = None
    rate_limit: Optional[Dict[str, Any]] = None


class TestMCPServerRequest(BaseModel):
    server_type: str
    connection_config: Dict[str, Any]
    auth_config: Optional[Dict[str, Any]] = None


class ExecuteToolRequest(BaseModel):
    tool_name: str
    input_data: Dict[str, Any]


@router.get("/")
async def list_user_servers(
    db: AsyncSession = Depends(get_db),
    include_shared: bool = True,
    # current_user = Depends(get_current_user)
):
    """List all MCP servers available to the current user"""
    user_id = 1  # TODO: Get from auth
    
    service = get_user_mcp_service()
    servers = await service.get_user_servers(db, user_id, include_shared)
    
    return [
        {
            "id": server.id,
            "name": server.name,
            "display_name": server.display_name,
            "description": server.description,
            "server_type": server.server_type.value,
            "status": server.status.value,
            "tool_count": server.tool_count,
            "usage_count": server.usage_count,
            "last_connected": server.last_connected.isoformat() if server.last_connected else None,
            "is_active": server.is_active,
            "is_public": server.is_public
        }
        for server in servers
    ]


@router.get("/{server_id}")
async def get_server_details(
    server_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific MCP server"""
    result = await db.execute(
        select(UserMCPServer).where(UserMCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Get tools
    tools_result = await db.execute(
        select(MCPServerTool).where(MCPServerTool.server_id == server_id)
    )
    tools = tools_result.scalars().all()
    
    return {
        "id": server.id,
        "name": server.name,
        "display_name": server.display_name,
        "description": server.description,
        "server_type": server.server_type.value,
        "connection_config": server.connection_config,
        "status": server.status.value,
        "tools": [
            {
                "id": tool.id,
                "name": tool.name,
                "display_name": tool.display_name,
                "description": tool.description,
                "category": tool.category,
                "tags": tool.tags,
                "usage_count": tool.usage_count,
                "success_rate": (
                    tool.success_count / (tool.success_count + tool.failure_count)
                    if (tool.success_count + tool.failure_count) > 0
                    else 0
                )
            }
            for tool in tools
        ],
        "usage_stats": {
            "total_uses": server.usage_count,
            "last_used": server.last_used.isoformat() if server.last_used else None,
            "error_count": server.error_count
        },
        "rate_limit": server.rate_limit,
        "created_at": server.created_at.isoformat()
    }


@router.post("/test")
async def test_mcp_server(
    request: TestMCPServerRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test an MCP server connection before saving"""
    service = get_user_mcp_service()
    
    result = await service.test_mcp_server(db, {
        "server_type": request.server_type,
        "connection_config": request.connection_config,
        "auth_config": request.auth_config
    })
    
    return result


@router.post("/")
async def add_mcp_server(
    request: AddMCPServerRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add a new MCP server"""
    user_id = 1  # TODO: Get from auth
    
    # Check if name already exists for this user
    existing = await db.execute(
        select(UserMCPServer).where(
            UserMCPServer.user_id == user_id,
            UserMCPServer.name == request.name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Server name '{request.name}' already exists")
    
    service = get_user_mcp_service()
    
    server = await service.save_mcp_server(
        db,
        user_id,
        request.dict()
    )
    
    return {
        "id": server.id,
        "name": server.name,
        "status": server.status.value,
        "tool_count": server.tool_count,
        "message": f"MCP server '{server.name}' added successfully"
    }


@router.post("/import-claude")
async def import_claude_config(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Import MCP servers from Claude Desktop config file"""
    user_id = 1  # TODO: Get from auth
    
    content = await file.read()
    try:
        config = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    
    if 'mcpServers' not in config:
        raise HTTPException(status_code=400, detail="No MCP servers found in config")
    
    service = get_user_mcp_service()
    imported = []
    failed = []
    
    for name, server_config in config['mcpServers'].items():
        try:
            # Convert Claude format to our format
            server_data = {
                "name": name,
                "display_name": name.replace('-', ' ').title(),
                "description": f"Imported from Claude Desktop",
                "server_type": "stdio",  # Claude uses stdio
                "connection_config": {
                    "command": server_config.get('command'),
                    "args": server_config.get('args', []),
                    "env": server_config.get('env', {})
                }
            }
            
            server = await service.save_mcp_server(db, user_id, server_data)
            imported.append(server.name)
            
        except Exception as e:
            failed.append({"name": name, "error": str(e)})
    
    return {
        "imported": imported,
        "failed": failed,
        "message": f"Imported {len(imported)} servers, {len(failed)} failed"
    }


@router.put("/{server_id}")
async def update_mcp_server(
    server_id: int,
    request: AddMCPServerRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update an MCP server configuration"""
    result = await db.execute(
        select(UserMCPServer).where(UserMCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    # Test new configuration
    service = get_user_mcp_service()
    test_result = await service.test_mcp_server(db, request.dict())
    
    # Update server
    server.display_name = request.display_name
    server.description = request.description
    server.connection_config = request.connection_config
    server.auth_config = request.auth_config
    server.rate_limit = request.rate_limit
    server.status = MCPServerStatus.CONNECTED if test_result['success'] else MCPServerStatus.FAILED
    server.last_error = test_result.get('error')
    server.updated_at = datetime.utcnow()
    
    if test_result['success']:
        server.last_connected = datetime.utcnow()
        server.available_tools = test_result.get('tools', [])
        server.tool_count = len(test_result.get('tools', []))
    
    await db.commit()
    
    return {
        "id": server.id,
        "status": server.status.value,
        "message": "Server updated successfully"
    }


@router.delete("/{server_id}")
async def delete_mcp_server(
    server_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete an MCP server (soft delete)"""
    result = await db.execute(
        select(UserMCPServer).where(UserMCPServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    server.is_active = False
    server.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": f"Server '{server.name}' deactivated"}


@router.post("/{server_id}/tools/{tool_name}/execute")
async def execute_tool(
    server_id: int,
    tool_name: str,
    request: ExecuteToolRequest,
    db: AsyncSession = Depends(get_db)
):
    """Execute a tool on an MCP server"""
    user_id = 1  # TODO: Get from auth
    
    service = get_user_mcp_service()
    result = await service.execute_tool(
        db,
        server_id,
        tool_name,
        request.input_data,
        user_id
    )
    
    if not result['success']:
        raise HTTPException(status_code=500, detail=result.get('error'))
    
    return result


# @router.get("/{server_id}/logs")
# async def get_server_logs(
#     server_id: int,
#     limit: int = 100,
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get execution logs for an MCP server"""
#     # TODO: Add MCPServerLog model to models.py
#     return []


@router.post("/{server_id}/share")
async def share_mcp_server(
    server_id: int,
    share_with_user_id: Optional[int] = None,
    make_public: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Share an MCP server with another user or make it public"""
    # Implementation for sharing
    pass


@router.get("/marketplace/popular")
async def get_popular_servers(
    db: AsyncSession = Depends(get_db),
    limit: int = 10
):
    """Get popular public MCP servers from the marketplace"""
    result = await db.execute(
        select(UserMCPServer)
        .where(UserMCPServer.is_public == True)
        .order_by(UserMCPServer.usage_count.desc())
        .limit(limit)
    )
    servers = result.scalars().all()
    
    return [
        {
            "id": server.id,
            "display_name": server.display_name,
            "description": server.description,
            "tool_count": server.tool_count,
            "usage_count": server.usage_count,
            "creator": "Anonymous"  # Would get from user relationship
        }
        for server in servers
    ]