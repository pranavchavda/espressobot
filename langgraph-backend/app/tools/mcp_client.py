import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
import subprocess

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for interacting with MCP servers"""
    
    def __init__(self, server_path: str):
        self.server_path = server_path
        self.process: Optional[asyncio.subprocess.Process] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()
        self._message_id = 0
    
    async def connect(self):
        """Start the MCP server and establish connection"""
        try:
            # Get Python tools directory
            python_tools_dir = os.path.dirname(self.server_path)
            
            self.process = await asyncio.create_subprocess_exec(
                "python3", self.server_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONPATH": python_tools_dir}
            )
            
            logger.info(f"Started MCP server: {self.server_path}")
            
            await self._initialize()
            
        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.server_path}: {e}")
            raise
    
    async def _initialize(self):
        """Initialize the MCP connection"""
        request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {}
            },
            "id": self._get_next_id()
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            raise Exception(f"Failed to initialize MCP server: {response['error']}")
        
        logger.info(f"Initialized MCP server with capabilities: {response.get('result', {}).get('capabilities', {})}")
    
    async def _send_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP server and wait for response"""
        async with self._lock:
            if not self.process or self.process.returncode is not None:
                raise Exception("MCP server is not running")
            
            request_str = json.dumps(request) + "\n"
            self.process.stdin.write(request_str.encode())
            await self.process.stdin.drain()
            
            response_line = await self.process.stdout.readline()
            
            if not response_line:
                raise Exception("No response from MCP server")
            
            try:
                return json.loads(response_line.decode())
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse MCP response: {response_line}")
                raise
    
    def _get_next_id(self) -> int:
        """Get the next message ID"""
        self._message_id += 1
        return self._message_id
    
    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools from the MCP server"""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": self._get_next_id()
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            logger.error(f"Failed to list tools: {response['error']}")
            return []
        
        return response.get("result", {}).get("tools", [])
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on the MCP server"""
        logger.info(f"🔧 Calling tool: {tool_name}")
        logger.info(f"   Arguments: {json.dumps(arguments, indent=2)}")
        
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            },
            "id": self._get_next_id()
        }
        
        response = await self._send_request(request)
        
        if "error" in response:
            logger.error(f"❌ Tool call failed: {response['error']}")
            raise Exception(f"Tool call failed: {response['error']}")
        
        result = response.get("result", {})
        
        # Log the result (truncate if too long)
        result_str = json.dumps(result, indent=2)
        if len(result_str) > 500:
            result_str = result_str[:500] + "... (truncated)"
        logger.info(f"✅ Tool response: {result_str}")
        
        return result
    
    async def disconnect(self):
        """Disconnect from the MCP server"""
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            
            logger.info(f"Disconnected from MCP server: {self.server_path}")

class MCPManager:
    """Manager for multiple MCP server connections"""
    
    def __init__(self):
        self.servers: Dict[str, MCPClient] = {}
        self.base_path = os.getenv("MCP_TOOLS_PATH", "/home/pranav/espressobot/frontend/python-tools")
        self._initialized = False
    
    async def initialize(self):
        """Initialize all MCP server connections"""
        if self._initialized:
            return
        
        # Map to actual MCP server files in frontend/python-tools
        server_configs = {
            "products": "mcp-products-server.py",
            "pricing": "mcp-pricing-server.py",
            "inventory": "mcp-inventory-server.py",
            "sales": "mcp-sales-server.py",
            "features": "mcp-features-server.py",
            "media": "mcp-media-server.py",
            "integrations": "mcp-integrations-server.py",
            "product_management": "mcp-product-management-server.py",
            "utility": "mcp-utility-server.py",
            "graphql": "mcp-graphql-server.py",
            "orders": "mcp-orders-server.py"
        }
        
        for name, filename in server_configs.items():
            server_path = Path(self.base_path) / filename
            
            if not server_path.exists():
                logger.warning(f"MCP server not found: {server_path}")
                continue
            
            try:
                client = MCPClient(str(server_path))
                await client.connect()
                self.servers[name] = client
                logger.info(f"Connected to MCP server: {name}")
            except Exception as e:
                logger.error(f"Failed to connect to MCP server {name}: {e}")
        
        self._initialized = True
    
    async def get_tools_for_agent(self, agent_type: str) -> List[Dict[str, Any]]:
        """Get tools available for a specific agent type"""
        if not self._initialized:
            await self.initialize()
        
        if agent_type not in self.servers:
            logger.warning(f"No MCP server for agent type: {agent_type}")
            return []
        
        return await self.servers[agent_type].list_tools()
    
    async def call_tool(self, agent_type: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool through the appropriate MCP server"""
        logger.info(f"📋 MCP Manager routing tool call to {agent_type} agent")
        
        if not self._initialized:
            await self.initialize()
        
        if agent_type not in self.servers:
            logger.error(f"❌ No MCP server for agent type: {agent_type}")
            raise Exception(f"No MCP server for agent type: {agent_type}")
        
        return await self.servers[agent_type].call_tool(tool_name, arguments)
    
    async def shutdown(self):
        """Shutdown all MCP server connections"""
        for name, client in self.servers.items():
            try:
                await client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from {name}: {e}")
        
        self.servers.clear()
        self._initialized = False

_manager: Optional[MCPManager] = None

async def get_mcp_manager() -> MCPManager:
    """Get or create the global MCP manager"""
    global _manager
    
    if _manager is None:
        _manager = MCPManager()
        await _manager.initialize()
    
    return _manager