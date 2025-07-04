#!/usr/bin/env python3
"""
MCP Server for EspressoBot Python Tools
Uses stdio transport for local communication
"""

import asyncio
import json
import sys
import os
import importlib
import inspect
import traceback
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging
from datetime import datetime

# Add python-tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/mcp-server.log'), logging.StreamHandler()]
)
logger = logging.getLogger('mcp-server')

class MCPServer:
    """Stdio-based MCP server for Python tools"""
    
    def __init__(self):
        self.tools = {}
        self.tool_contexts = {}
        self.server_info = {
            "name": "espressobot-tools",
            "version": "1.0.0"
        }
        
    async def initialize(self):
        """Initialize server and discover tools"""
        logger.info("Initializing MCP server...")
        await self.discover_tools()
        await self.test_all_tools()
        logger.info(f"MCP server ready with {len(self.tools)} tools")
        
    async def discover_tools(self):
        """Discover and load all MCP tools"""
        tools_dir = Path(__file__).parent / "mcp_tools"
        if not tools_dir.exists():
            logger.warning(f"Tools directory not found: {tools_dir}")
            return
            
        # Import all tool modules
        for category_dir in tools_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith('_'):
                for tool_file in category_dir.glob("*.py"):
                    if tool_file.name.startswith('_'):
                        continue
                        
                    module_name = f"mcp_tools.{category_dir.name}.{tool_file.stem}"
                    try:
                        module = importlib.import_module(module_name)
                        
                        # Find tool classes in module
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and 
                                hasattr(obj, 'name') and 
                                hasattr(obj, 'execute') and
                                obj.__module__ == module.__name__):  # Avoid importing base class
                                tool_instance = obj()
                                self.tools[tool_instance.name] = tool_instance
                                
                                # Store tool context if available
                                if hasattr(tool_instance, 'context'):
                                    self.tool_contexts[tool_instance.name] = tool_instance.context
                                    
                                logger.info(f"Loaded tool: {tool_instance.name}")
                                
                    except Exception as e:
                        logger.error(f"Failed to load {module_name}: {e}")
                        
    async def test_all_tools(self):
        """Test all loaded tools"""
        logger.info("Testing all tools...")
        results = {}
        
        for tool_name, tool in self.tools.items():
            if hasattr(tool, 'test'):
                try:
                    result = await tool.test()
                    results[tool_name] = {"status": "passed", "result": result}
                    logger.info(f"✓ {tool_name} test passed")
                except Exception as e:
                    results[tool_name] = {"status": "failed", "error": str(e)}
                    logger.error(f"✗ {tool_name} test failed: {e}")
            else:
                results[tool_name] = {"status": "skipped", "reason": "no test method"}
                
        # Log summary
        passed = sum(1 for r in results.values() if r["status"] == "passed")
        failed = sum(1 for r in results.values() if r["status"] == "failed")
        skipped = sum(1 for r in results.values() if r["status"] == "skipped")
        
        logger.info(f"Test summary: {passed} passed, {failed} failed, {skipped} skipped")
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request"""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "protocolVersion": "2025-03-26",
                        "serverInfo": self.server_info,
                        "capabilities": {
                            "prompts": {},
                            "resources": {},
                            "tools": {}
                        }
                    }
                }
                
            elif method == "tools/list":
                tools_list = []
                for name, tool in self.tools.items():
                    tool_info = {
                        "name": name,
                        "description": getattr(tool, 'description', ''),
                        "inputSchema": getattr(tool, 'input_schema', {})
                    }
                    # Include context in description if available
                    if name in self.tool_contexts:
                        tool_info["description"] += f"\n\nContext:\n{self.tool_contexts[name]}"
                    tools_list.append(tool_info)
                    
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools_list}
                }
                
            elif method == "tools/call":
                logger.info(f"tools/call params: {params}")
                
                # Handle nested structure from some MCP clients
                if isinstance(params.get("name"), dict):
                    tool_name = params["name"]["name"]
                    tool_args = params["name"].get("arguments", {})
                else:
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})
                
                if tool_name not in self.tools:
                    raise ValueError(f"Unknown tool: {tool_name}")
                    
                tool = self.tools[tool_name]
                
                try:
                    result = await tool.execute(**tool_args)
                    logger.info(f"Tool {tool_name} returned {len(result) if isinstance(result, list) else 'non-list'} results")
                    
                    # Format result according to MCP protocol specification
                    # MCP expects result.content array with type/text items
                    formatted_result = {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result)
                            }
                        ]
                    }
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": formatted_result
                    }
                    logger.info(f"Sending MCP-formatted response: {json.dumps(response)[:200]}...")
                    return response
                except Exception as tool_error:
                    # Log the error but don't crash the server
                    logger.error(f"Tool {tool_name} execution failed: {str(tool_error)}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Return error response instead of crashing
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,  # Internal error
                            "message": f"Tool execution failed: {str(tool_error)}"
                        }
                    }
                
            elif method == "notifications/initialized":
                # Client is ready, just acknowledge
                logger.info("Client initialized")
                return None  # Notifications don't need responses
                
            else:
                raise ValueError(f"Unknown method: {method}")
                
        except Exception as e:
            import traceback
            logger.error(f"Error handling request: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            
    async def run(self):
        """Run the stdio server"""
        logger.info("Starting stdio server...")
        
        # Initialize server
        await self.initialize()
        
        # Send ready signal
        ready_msg = {"jsonrpc": "2.0", "method": "ready"}
        sys.stdout.write(json.dumps(ready_msg) + "\n")
        sys.stdout.flush()
        
        # Read requests from stdin
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                if not line:
                    break
                    
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                
                # Only send response if it's not None (notifications don't need responses)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON: {e}")
            except Exception as e:
                logger.error(f"Server error: {e}")
                
        logger.info("Server shutting down")
        
if __name__ == "__main__":
    server = MCPServer()
    asyncio.run(server.run())