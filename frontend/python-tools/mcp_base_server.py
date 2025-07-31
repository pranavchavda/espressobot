#!/usr/bin/env python3
"""
Enhanced MCP Base Server with Resources and Prompts support
Reduces token usage by offloading context to on-demand resources
"""

import asyncio
import json
import sys
import os
import logging
import traceback
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('/tmp/mcp-server.log'), logging.StreamHandler()]
)
logger = logging.getLogger('mcp-base-server')


class MCPResource:
    """Resource definition for MCP server"""
    def __init__(self, name: str, uri: str, description: str = "", mime_type: str = "text/plain"):
        self.name = name
        self.uri = uri
        self.description = description
        self.mime_type = mime_type
        self._getter = None
    
    def getter(self, func: Callable):
        """Decorator to set the getter function"""
        self._getter = func
        return func
    
    async def get_content(self) -> Dict[str, Any]:
        """Get the resource content"""
        if self._getter:
            content = await self._getter() if asyncio.iscoroutinefunction(self._getter) else self._getter()
            return {
                "uri": self.uri,
                "mimeType": self.mime_type,
                "text": content if isinstance(content, str) else json.dumps(content)
            }
        return None


class MCPPrompt:
    """Prompt definition for MCP server"""
    def __init__(self, name: str, description: str = "", arguments: List[Dict] = None):
        self.name = name
        self.description = description
        self.arguments = arguments or []
        self._handler = None
    
    def handler(self, func: Callable):
        """Decorator to set the handler function"""
        self._handler = func
        return func
    
    async def get_messages(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get the prompt messages"""
        if self._handler:
            result = await self._handler(**arguments) if asyncio.iscoroutinefunction(self._handler) else self._handler(**arguments)
            if isinstance(result, str):
                return [{"role": "user", "content": result}]
            return result
        return []


class EnhancedMCPServer:
    """Enhanced MCP server with resources and prompts support"""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.tools = {}
        self.resources = {}
        self.prompts = {}
        self.server_info = {
            "name": name,
            "version": version
        }
        
    def add_tool(self, tool):
        """Add a tool to the server"""
        self.tools[tool.name] = tool
        logger.info(f"Added tool: {tool.name}")
        
    def add_resource(self, resource: MCPResource):
        """Add a resource to the server"""
        self.resources[resource.uri] = resource
        logger.info(f"Added resource: {resource.uri}")
        
    def add_prompt(self, prompt: MCPPrompt):
        """Add a prompt to the server"""
        self.prompts[prompt.name] = prompt
        logger.info(f"Added prompt: {prompt.name}")
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request with resources and prompts support"""
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
                            "prompts": {"listChanged": True} if self.prompts else {},
                            "resources": {"list": True, "listChanged": True} if self.resources else {},
                            "tools": {}
                        }
                    }
                }
                
            elif method == "tools/list":
                tools_list = []
                for name, tool in self.tools.items():
                    tools_list.append({
                        "name": name,
                        "description": getattr(tool, 'description', ''),
                        "inputSchema": getattr(tool, 'input_schema', {})
                    })
                    
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": tools_list}
                }
                
            elif method == "resources/list":
                resources_list = []
                for uri, resource in self.resources.items():
                    resources_list.append({
                        "uri": uri,
                        "name": resource.name,
                        "description": resource.description,
                        "mimeType": resource.mime_type
                    })
                    
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resources": resources_list}
                }
                
            elif method == "resources/read":
                uri = params.get("uri")
                if uri not in self.resources:
                    raise ValueError(f"Unknown resource: {uri}")
                    
                resource = self.resources[uri]
                content = await resource.get_content()
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"contents": [content]}
                }
                
            elif method == "prompts/list":
                prompts_list = []
                for name, prompt in self.prompts.items():
                    prompts_list.append({
                        "name": name,
                        "description": prompt.description,
                        "arguments": prompt.arguments
                    })
                    
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"prompts": prompts_list}
                }
                
            elif method == "prompts/get":
                name = params.get("name")
                arguments = params.get("arguments", {})
                
                if name not in self.prompts:
                    raise ValueError(f"Unknown prompt: {name}")
                    
                prompt = self.prompts[name]
                messages = await prompt.get_messages(arguments)
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"messages": messages}
                }
                
            elif method == "tools/call":
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
                result = await tool.execute(**tool_args)
                
                # Format result according to MCP protocol
                formatted_result = {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result)
                        }
                    ]
                }
                
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": formatted_result
                }
                
            elif method == "notifications/initialized":
                # Client is ready, just acknowledge
                logger.info("Client initialized")
                return None  # Notifications don't need responses
                
            elif method == "notifications/cancelled":
                # Client cancelled a request, just acknowledge silently
                return None  # Notifications don't need responses
                
            else:
                raise ValueError(f"Unknown method: {method}")
                
        except Exception as e:
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
        logger.info(f"Starting {self.server_info['name']} MCP server...")
        
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
    def add_tool_from_def(self, tool_def):
        """Add a tool from a tool definition dictionary"""
        class DynamicTool:
            def __init__(self, name, description, input_schema, handler):
                self.name = name
                self.description = description
                self.input_schema = input_schema
                self._handler = handler
            
            async def execute(self, **kwargs):
                if asyncio.iscoroutinefunction(self._handler):
                    return await self._handler(**kwargs)
                else:
                    return self._handler(**kwargs)
        
        tool = DynamicTool(
            tool_def['name'],
            tool_def['description'], 
            tool_def['inputSchema'],
            tool_def['handler']
        )
        self.add_tool(tool)
