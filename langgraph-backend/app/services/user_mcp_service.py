"""
User MCP Server Management Service
Handles discovery, testing, and management of user-configured MCP servers
"""

import logging
import asyncio
import json
import subprocess
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database.models import (
    UserMCPServer, 
    MCPServerTool,
    MCPServerStatus,
    MCPServerType
)

logger = logging.getLogger(__name__)


class UserMCPService:
    """Service for managing user MCP servers"""
    
    def __init__(self):
        self.active_connections: Dict[int, Any] = {}  # server_id -> connection
        self.tool_cache: Dict[int, List[Dict]] = {}  # server_id -> tools
    
    async def test_mcp_server(
        self,
        db: AsyncSession,
        server_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Test an MCP server connection and discover tools
        
        Returns:
            {
                "success": bool,
                "status": str,
                "tools": [...],
                "error": str or None
            }
        """
        server_type = server_config.get('server_type', 'stdio')
        # Normalize Enum to its string value when passed from DB
        try:
            from app.database.models import MCPServerType
            if isinstance(server_type, MCPServerType):
                server_type = server_type.value
        except Exception:
            pass
        
        try:
            if server_type == 'stdio':
                return await self._test_stdio_server(server_config)
            elif server_type == 'sse':
                return await self._test_sse_server(server_config)
            elif server_type == 'http':
                return await self._test_http_server(server_config)
            else:
                return {
                    "success": False,
                    "status": "failed",
                    "error": f"Unsupported server type: {server_type}"
                }
        except Exception as e:
            logger.error(f"Error testing MCP server: {e}")
            return {
                "success": False,
                "status": "failed",
                "error": str(e)
            }
    
    async def _test_stdio_server(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test STDIO-based MCP server"""
        connection_config = config['connection_config']
        command = connection_config.get('command')
        args = connection_config.get('args', [])
        env = connection_config.get('env', {})
        
        try:
            # Start the MCP server process
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, **env}
            )
            
            # Send initialization request
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "0.1.0",
                    "capabilities": {}
                },
                "id": 1
            }
            
            process.stdin.write(json.dumps(init_request).encode() + b'\n')
            await process.stdin.drain()
            
            # Read response with timeout
            try:
                response_line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=5.0
                )
                response = json.loads(response_line.decode())
                
                if 'result' in response:
                    # Get available tools
                    tools_request = {
                        "jsonrpc": "2.0",
                        "method": "tools/list",
                        "params": {},
                        "id": 2
                    }
                    
                    process.stdin.write(json.dumps(tools_request).encode() + b'\n')
                    await process.stdin.drain()
                    
                    tools_response_line = await asyncio.wait_for(
                        process.stdout.readline(),
                        timeout=5.0
                    )
                    tools_response = json.loads(tools_response_line.decode())
                    
                    # Clean up
                    process.terminate()
                    await process.wait()
                    
                    if 'result' in tools_response:
                        tools = tools_response['result'].get('tools', [])
                        return {
                            "success": True,
                            "status": "connected",
                            "tools": tools,
                            "error": None
                        }
                
            except asyncio.TimeoutError:
                process.terminate()
                await process.wait()
                return {
                    "success": False,
                    "status": "timeout",
                    "error": "Server did not respond within timeout"
                }
            
        except Exception as e:
            return {
                "success": False,
                "status": "failed",
                "error": str(e)
            }
    
    async def _test_sse_server(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test SSE-based MCP server"""
        import aiohttp
        
        connection_config = config['connection_config']
        url = connection_config.get('url')
        headers = connection_config.get('headers', {})
        
        try:
            async with aiohttp.ClientSession() as session:
                # Connect to SSE endpoint
                async with session.get(
                    f"{url}/tools",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        tools_data = await response.json()
                        return {
                            "success": True,
                            "status": "connected",
                            "tools": tools_data.get('tools', []),
                            "error": None
                        }
                    else:
                        return {
                            "success": False,
                            "status": "failed",
                            "error": f"Server returned status {response.status}"
                        }
                        
        except Exception as e:
            return {
                "success": False,
                "status": "failed",
                "error": str(e)
            }
    
    async def _test_http_server(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Test HTTP-based MCP server"""
        import aiohttp
        
        connection_config = config['connection_config']
        base_url = connection_config.get('base_url')
        auth_config = config.get('auth_config', {})
        
        headers = {
            'Content-Type': 'application/json'
        }
        if auth_config and auth_config.get('type') == 'bearer':
            headers['Authorization'] = f"Bearer {auth_config.get('token')}"
        elif auth_config and auth_config.get('type') == 'api_key':
            headers[auth_config.get('key_name', 'X-API-Key')] = auth_config.get('key_value')
        
        try:
            async with aiohttp.ClientSession() as session:
                # Send MCP initialization request using JSON-RPC
                init_request = {
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "0.1.0",
                        "capabilities": {}
                    },
                    "id": 1
                }
                
                async with session.post(
                    base_url,
                    json=init_request,
                    headers=headers
                ) as response:
                    if response.status != 200:
                        # Try simpler test - just check if endpoint exists
                        async with session.get(base_url, headers=headers) as test_response:
                            if test_response.status == 200:
                                # Server exists but may not support MCP protocol
                                return {
                                    "success": True,
                                    "status": "connected",
                                    "tools": [],
                                    "error": None,
                                    "warning": "Server responds but MCP protocol not confirmed"
                                }
                        return {
                            "success": False,
                            "status": "failed",
                            "error": f"Server returned status {response.status}"
                        }
                    
                    init_response = await response.json()
                    
                    if 'result' in init_response:
                        # Try to get tools
                        tools_request = {
                            "jsonrpc": "2.0",
                            "method": "tools/list",
                            "params": {},
                            "id": 2
                        }
                        
                        async with session.post(
                            base_url,
                            json=tools_request,
                            headers=headers
                        ) as tools_response:
                            if tools_response.status == 200:
                                tools_data = await tools_response.json()
                                tools = tools_data.get('result', {}).get('tools', [])
                            else:
                                tools = []
                        
                        return {
                            "success": True,
                            "status": "connected",
                            "tools": tools,
                            "error": None
                        }
                    else:
                        return {
                            "success": False,
                            "status": "failed",
                            "error": "Invalid initialization response"
                        }
                    
        except aiohttp.ClientError as e:
            return {
                "success": False,
                "status": "failed",
                "error": f"Connection error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "status": "failed",
                "error": str(e)
            }
    
    async def save_mcp_server(
        self,
        db: AsyncSession,
        user_id: int,
        server_data: Dict[str, Any]
    ) -> UserMCPServer:
        """Save a new MCP server configuration"""
        
        # Test the server first
        test_result = await self.test_mcp_server(db, server_data)
        
        # Create server record
        server = UserMCPServer(
            user_id=user_id,
            name=server_data['name'],
            display_name=server_data['display_name'],
            description=server_data.get('description'),
            server_type=MCPServerType[server_data.get('server_type', 'STDIO').upper()],
            connection_config=server_data['connection_config'],
            requires_auth=server_data.get('requires_auth', False),
            auth_config=server_data.get('auth_config'),
            status=MCPServerStatus.CONNECTED if test_result['success'] else MCPServerStatus.FAILED,
            last_error=test_result.get('error'),
            available_tools=test_result.get('tools', []),
            tool_count=len(test_result.get('tools', []))
        )
        
        if test_result['success']:
            server.last_connected = datetime.utcnow()
        
        db.add(server)
        await db.flush()
        
        # Save discovered tools
        if test_result['success'] and test_result.get('tools'):
            for tool_data in test_result['tools']:
                tool = MCPServerTool(
                    server_id=server.id,
                    name=tool_data.get('name'),
                    display_name=tool_data.get('displayName', tool_data.get('name')),
                    description=tool_data.get('description'),
                    input_schema=tool_data.get('inputSchema'),
                    category=self._categorize_tool(tool_data),
                    tags=self._extract_tags(tool_data)
                )
                db.add(tool)
        
        await db.commit()
        await db.refresh(server)
        
        logger.info(f"Saved MCP server {server.name} for user {user_id}")
        
        return server
    
    async def execute_tool(
        self,
        db: AsyncSession,
        server_id: int,
        tool_name: str,
        input_data: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """Execute a tool on a user's MCP server"""
        
        # Get server configuration
        result = await db.execute(
            select(UserMCPServer).where(
                UserMCPServer.id == server_id,
                UserMCPServer.is_active == True
            )
        )
        server = result.scalar_one_or_none()
        
        if not server:
            return {
                "success": False,
                "error": "Server not found or inactive"
            }
        
        # Check permissions if not owner
        if server.user_id != user_id:
            # Check if shared with this user
            # Implementation would check MCPServerShare table
            pass
        
        start_time = datetime.utcnow()
        
        try:
            # Execute based on server type
            if server.server_type == MCPServerType.STDIO:
                result = await self._execute_stdio_tool(
                    server.connection_config,
                    tool_name,
                    input_data
                )
            elif server.server_type == MCPServerType.HTTP:
                result = await self._execute_http_tool(
                    server.connection_config,
                    tool_name,
                    input_data
                )
            else:
                result = {
                    "success": False,
                    "error": f"Unsupported server type: {server.server_type}"
                }
            
            # Log the execution (TODO: Add MCPServerLog model)
            response_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # TODO: Uncomment when MCPServerLog is added to models.py
            # log_entry = MCPServerLog(
            #     server_id=server_id,
            #     user_id=user_id,
            #     tool_name=tool_name,
            #     input_data=input_data,
            #     output_data=result.get('output'),
            #     response_time=response_time,
            #     success=result.get('success', False),
            #     error_message=result.get('error')
            # )
            # db.add(log_entry)
            
            # Update usage statistics
            server.usage_count += 1
            server.last_used = datetime.utcnow()
            
            await db.commit()
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name} on server {server_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_tool_with_config(
        self,
        server_config: Dict[str, Any],
        tool_name: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool without requiring a DB session using provided server config."""
        try:
            server_type = server_config.get('server_type', 'stdio')
            # Normalize Enum to string if present
            try:
                from app.database.models import MCPServerType
                if isinstance(server_type, MCPServerType):
                    server_type = server_type.value
            except Exception:
                pass

            if server_type == 'stdio':
                return await self._execute_stdio_tool(server_config.get('connection_config', {}), tool_name, input_data)
            elif server_type == 'http':
                return await self._execute_http_tool(server_config.get('connection_config', {}), tool_name, input_data)
            else:
                return {
                    "success": False,
                    "error": f"Unsupported server type: {server_type}"
                }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name} with config: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_stdio_tool(
        self,
        connection_config: Dict,
        tool_name: str,
        input_data: Dict
    ) -> Dict[str, Any]:
        """Execute tool on STDIO server via JSON-RPC."""
        command = connection_config.get('command')
        args = connection_config.get('args', [])
        env = connection_config.get('env', {})

        try:
            process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**os.environ, **env}
            )

            # Initialize
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {"protocolVersion": "0.1.0", "capabilities": {}},
                "id": 1,
            }
            process.stdin.write(json.dumps(init_request).encode() + b"\n")
            await process.stdin.drain()
            _ = await asyncio.wait_for(process.stdout.readline(), timeout=5.0)

            # Call tool
            call_request = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": input_data},
                "id": 2,
            }
            process.stdin.write(json.dumps(call_request).encode() + b"\n")
            await process.stdin.drain()
            call_resp_line = await asyncio.wait_for(process.stdout.readline(), timeout=20.0)

            # Clean up
            try:
                process.terminate()
                await process.wait()
            except Exception:
                pass

            call_resp = json.loads(call_resp_line.decode())
            if 'error' in call_resp:
                return {"success": False, "error": call_resp['error']}

            return {"success": True, "output": call_resp}

        except asyncio.TimeoutError:
            try:
                process.terminate()
                await process.wait()
            except Exception:
                pass
            return {"success": False, "error": "STDIO MCP call timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_http_tool(
        self,
        connection_config: Dict,
        tool_name: str,
        input_data: Dict
    ) -> Dict[str, Any]:
        """Execute tool on HTTP MCP server using JSON-RPC."""
        import aiohttp

        base_url = connection_config.get('base_url')
        auth = connection_config.get('auth', {})

        headers = {"Content-Type": "application/json"}
        if auth.get('type') == 'bearer':
            headers['Authorization'] = f"Bearer {auth.get('token')}"

        rpc_call = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": input_data},
            "id": 1,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(base_url, json=rpc_call, headers=headers) as response:
                if response.status != 200:
                    return {"success": False, "error": f"HTTP {response.status}: {await response.text()}"}
                data = await response.json()
                if 'error' in data:
                    return {"success": False, "error": data['error']}
                return {"success": True, "output": data}
    
    def _categorize_tool(self, tool_data: Dict) -> str:
        """Categorize a tool based on its metadata"""
        name = tool_data.get('name', '').lower()
        description = tool_data.get('description', '').lower()
        
        if 'data' in name or 'query' in name or 'fetch' in name:
            return 'data'
        elif 'api' in name or 'request' in name:
            return 'api'
        elif 'transform' in name or 'process' in name:
            return 'processing'
        else:
            return 'utility'
    
    def _extract_tags(self, tool_data: Dict) -> List[str]:
        """Extract tags from tool metadata"""
        tags = []
        
        # Add tags based on tool characteristics
        if tool_data.get('requiresAuth'):
            tags.append('auth-required')
        
        # Extract from description
        description = tool_data.get('description', '')
        keywords = ['async', 'batch', 'real-time', 'cached']
        for keyword in keywords:
            if keyword in description.lower():
                tags.append(keyword)
        
        return tags
    
    async def get_server_by_name(self, db: AsyncSession, server_name: str, user_id: int = 1) -> Optional[Dict[str, Any]]:
        """Get server configuration by name"""
        try:
            from app.database.models import UserMCPServer
            from sqlalchemy import select
            
            result = await db.execute(
                select(UserMCPServer).where(
                    UserMCPServer.name == server_name,
                    UserMCPServer.user_id == user_id,
                    UserMCPServer.is_active == True
                )
            )
            server = result.scalar_one_or_none()
            
            if not server:
                return None
            
            return {
                'id': server.id,
                'name': server.name,
                'description': server.description,
                'server_type': server.server_type,
                'connection_config': server.connection_config,
                'is_active': server.is_active
            }
            
        except Exception as e:
            logger.error(f"Error getting server by name '{server_name}': {e}")
            return None
    
    async def get_user_servers(
        self,
        db: AsyncSession,
        user_id: int,
        include_shared: bool = True
    ) -> List[UserMCPServer]:
        """Get all MCP servers available to a user"""
        
        # Get user's own servers
        result = await db.execute(
            select(UserMCPServer).where(
                UserMCPServer.user_id == user_id,
                UserMCPServer.is_active == True
            )
        )
        servers = list(result.scalars().all())
        
        if include_shared:
            # TODO: Add shared servers from MCPServerShare table
            pass
        
        return servers


# Singleton instance
_user_mcp_service: Optional[UserMCPService] = None

def get_user_mcp_service() -> UserMCPService:
    """Get or create the user MCP service singleton"""
    global _user_mcp_service
    if _user_mcp_service is None:
        _user_mcp_service = UserMCPService()
    return _user_mcp_service
