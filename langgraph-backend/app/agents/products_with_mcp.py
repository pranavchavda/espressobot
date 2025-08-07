"""
Products Agent with direct MCP integration
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
import logging
import os
import json
import re
from app.tools.mcp_client import MCPClient
from pathlib import Path

logger = logging.getLogger(__name__)

class ProductsAgentMCP:
    """Products agent with direct MCP server integration"""
    
    def __init__(self):
        self.name = "products"
        self.description = "Handles product searches, SKU lookups, and product information queries"
        self.model = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0.0,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.mcp_client = None
        self.system_prompt = self._get_system_prompt()
    
    async def _ensure_mcp_connected(self):
        """Ensure MCP server is connected"""
        if not self.mcp_client:
            server_path = Path("/home/pranav/espressobot/frontend/python-tools/mcp-products-server.py")
            self.mcp_client = MCPClient(str(server_path))
            await self.mcp_client.connect()
            logger.info("Connected to Products MCP server")
    
    def _get_system_prompt(self) -> str:
        return """You are a Products specialist agent with deep expertise in Shopify product management.

You have access to MCP tools through function calls. When you need to search or get product information, 
express your intent using this format:

<tool_call>
{
  "tool": "search_products",
  "arguments": {
    "query": "coffee",
    "status": "active",
    "limit": 5
  }
}
</tool_call>

Or for getting a specific product:

<tool_call>
{
  "tool": "get_product",
  "arguments": {
    "identifier": "ESP-001"
  }
}
</tool_call>

Available tools:
- search_products: Search for products with filters (query, vendor, product_type, status, limit)
- get_product: Get detailed product information by SKU, handle, or ID

After I execute the tool for you, I'll provide the results. Then you should format and present them clearly to the user.

## Your Expertise:
- Product lifecycle management
- SKU and inventory tracking
- Product search and filtering
- Understanding product attributes

## Business Context:
- Products are the core of iDrinkCoffee.com's catalog
- SKUs must be unique across all products
- Product status affects visibility

Always verify product exists before suggesting updates."""
    
    def _extract_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """Extract tool calls from model response"""
        tool_calls = []
        pattern = r'<tool_call>(.*?)</tool_call>'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for match in matches:
            try:
                tool_call = json.loads(match.strip())
                tool_calls.append(tool_call)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse tool call: {match}")
        
        return tool_calls
    
    async def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool through MCP"""
        await self._ensure_mcp_connected()
        
        try:
            result = await self.mcp_client.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"error": str(e)}
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state and return updated state"""
        try:
            messages = state.get("messages", [])
            
            if not messages:
                return state
            
            # Get last user message
            last_message = messages[-1]
            if not isinstance(last_message, HumanMessage):
                return state
            
            # First, ask the model what it wants to do
            prompt_messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": last_message.content}
            ]
            
            response = await self.model.ainvoke(prompt_messages)
            
            # Check for tool calls
            tool_calls = self._extract_tool_calls(response.content)
            
            if tool_calls:
                # Execute tools and collect results
                tool_results = []
                for tool_call in tool_calls:
                    tool_name = tool_call.get("tool")
                    arguments = tool_call.get("arguments", {})
                    
                    logger.info(f"Executing tool: {tool_name} with args: {arguments}")
                    result = await self._execute_tool(tool_name, arguments)
                    tool_results.append({
                        "tool": tool_name,
                        "arguments": arguments,
                        "result": result
                    })
                
                # Now ask the model to interpret the results
                result_prompt = f"""Here are the results from the tool calls:

{json.dumps(tool_results, indent=2)}

Please provide a clear, formatted response to the user based on these results."""
                
                final_messages = prompt_messages + [
                    {"role": "assistant", "content": response.content},
                    {"role": "user", "content": result_prompt}
                ]
                
                final_response = await self.model.ainvoke(final_messages)
                
                state["messages"].append(AIMessage(
                    content=final_response.content,
                    metadata={"agent": self.name, "tools_used": [tc["tool"] for tc in tool_calls]}
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
            logger.error(f"Error in ProductsAgentMCP: {e}")
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
        if self.mcp_client:
            await self.mcp_client.disconnect()