"""
Products Agent using native LangChain MCP support (simplified approach)
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from langchain_mcp import MCPTool
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
import logging
import os
from pathlib import Path
import asyncio
import json

logger = logging.getLogger(__name__)

class ProductsAgentNativeMCPv2:
    """Products agent using native LangChain MCP integration with direct tool invocation"""
    
    def __init__(self):
        self.name = "products"
        self.description = "Handles product searches, SKU lookups, and product information queries"
        self.model = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0.0,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.session = None
        self.read_stream = None
        self.write_stream = None
        self.tools = []
        self.system_prompt = self._get_system_prompt()
        
    async def _ensure_mcp_connected(self):
        """Ensure MCP session is initialized"""
        if not self.session:
            try:
                # Create server parameters
                server_params = StdioServerParameters(
                    command="python3",
                    args=[str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-products-server.py"))],
                    env={
                        **os.environ,
                        "PYTHONPATH": "/home/pranav/espressobot/frontend/python-tools"
                    }
                )
                
                # Start the stdio client (don't use async with)
                self.read_stream, self.write_stream = await stdio_client(server_params).__aenter__()
                self.session = ClientSession(self.read_stream, self.write_stream)
                
                # Initialize session
                await self.session.initialize()
                
                # Get tools list
                tools_result = await self.session.list_tools()
                
                # Create LangChain tools from MCP tools
                self.tools = []
                for tool in tools_result.tools:
                    lc_tool = MCPTool(
                        session=self.session,
                        name=tool.name,
                        description=tool.description or "",
                        args_schema=tool.inputSchema
                    )
                    self.tools.append(lc_tool)
                
                logger.info(f"Connected to Products MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP session: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a Products specialist agent with deep expertise in Shopify product management.

You have access to product management tools. Use these tools to search for products, 
get product details, create new products, and manage product status.

Available tools include:
- search_products: Search for products with filters
- get_product: Get detailed product information
- create_product: Create new products
- update_status: Change product status
- update_variant_weight: Update product variant weight

Always use the appropriate tool to fulfill the user's request and provide clear, formatted responses."""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state and return updated state"""
        try:
            await self._ensure_mcp_connected()
            
            messages = state.get("messages", [])
            
            if not messages:
                return state
            
            # Get last user message
            last_message = messages[-1]
            if not isinstance(last_message, HumanMessage):
                return state
            
            # Use the model with tools
            model_with_tools = self.model.bind_tools(self.tools)
            
            # Get response from model
            response = await model_with_tools.ainvoke([
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": last_message.content}
            ])
            
            # Check if model wants to use tools
            if response.tool_calls:
                tool_results = []
                for tool_call in response.tool_calls:
                    # Find the matching tool
                    tool = next((t for t in self.tools if t.name == tool_call["name"]), None)
                    if tool:
                        try:
                            result = await tool.ainvoke(tool_call["args"])
                            tool_results.append({
                                "tool": tool_call["name"],
                                "result": result
                            })
                        except Exception as e:
                            logger.error(f"Tool execution error: {e}")
                            tool_results.append({
                                "tool": tool_call["name"],
                                "error": str(e)
                            })
                
                # Get final response with tool results
                final_response = await self.model.ainvoke([
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": last_message.content},
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": f"Tool results: {json.dumps(tool_results, indent=2)}. Please provide a response based on these results."}
                ])
                
                state["messages"].append(AIMessage(
                    content=final_response.content,
                    metadata={"agent": self.name, "tools_used": [tc["name"] for tc in response.tool_calls]}
                ))
            else:
                # No tool calls, just return the response
                state["messages"].append(AIMessage(
                    content=response.content,
                    metadata={"agent": self.name}
                ))
            
            state["last_agent"] = self.name
            return state
            
        except Exception as e:
            logger.error(f"Error in ProductsAgentNativeMCPv2: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in products agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["product", "sku", "find", "search", "item", "listing", 
                   "coffee", "machine", "grinder", "espresso", "breville",
                   "miele", "sanremo", "eureka", "accessories"]
        
        message_content = last_message.content.lower()
        return any(keyword in message_content for keyword in keywords)
    
    async def cleanup(self):
        """Clean up MCP connection"""
        if self.session:
            try:
                # Close the session properly
                if self.write_stream:
                    self.write_stream.close()
                if self.read_stream:
                    await self.read_stream.aclose()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")