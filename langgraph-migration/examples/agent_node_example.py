"""
Example of a LangGraph agent node implementation for the Products Agent.
This pattern can be replicated for all specialized agents.
"""

from typing import Dict, Any, List
from langgraph.graph import MessagesState
from langchain_community.tools import MCPClient
import logging

logger = logging.getLogger(__name__)


class ProductsAgent:
    """Products specialist agent using MCP server"""
    
    def __init__(self):
        self.name = "ProductsAgent"
        self.mcp_server_path = "/home/pranav/espressobot/frontend/python-tools/mcp-products-server.py"
        self.mcp_client = None
        self.tools = None
        
    async def initialize(self):
        """Initialize MCP connection and load tools"""
        try:
            self.mcp_client = MCPClient(f"stdio://{self.mcp_server_path}")
            self.tools = await self.mcp_client.get_tools()
            logger.info(f"Initialized {self.name} with {len(self.tools)} tools")
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            raise
            
    async def __call__(self, state: MessagesState) -> MessagesState:
        """Process the state - this is what LangGraph calls"""
        
        # Get the last user message
        last_message = state["messages"][-1]
        
        # Log the request
        logger.info(f"{self.name} processing: {last_message.content[:100]}...")
        
        # Determine which tool to use based on the message
        tool_to_use = self._select_tool(last_message.content)
        
        if tool_to_use:
            # Execute the tool
            result = await self._execute_tool(tool_to_use, last_message.content)
            
            # Add the result to messages
            state["messages"].append({
                "role": "assistant",
                "content": result,
                "agent": self.name
            })
        else:
            # No appropriate tool found
            state["messages"].append({
                "role": "assistant",
                "content": "I couldn't find an appropriate tool for that request.",
                "agent": self.name
            })
            
        return state
    
    def _select_tool(self, message: str) -> Dict[str, Any]:
        """Select the appropriate tool based on the message"""
        
        message_lower = message.lower()
        
        # Simple keyword matching (can be enhanced with LLM)
        tool_mapping = {
            "get_product": ["get", "find", "show", "details"],
            "search_products": ["search", "list", "find all"],
            "create_product": ["create", "add new", "make"],
            "update_status": ["status", "activate", "deactivate", "archive"]
        }
        
        for tool_name, keywords in tool_mapping.items():
            if any(keyword in message_lower for keyword in keywords):
                # Find the tool in our tools list
                for tool in self.tools:
                    if tool["name"] == tool_name:
                        return tool
                        
        return None
    
    async def _execute_tool(self, tool: Dict[str, Any], message: str) -> str:
        """Execute the selected tool with parameters extracted from the message"""
        
        try:
            # Extract parameters from message (simplified - use LLM in production)
            params = self._extract_parameters(tool, message)
            
            # Execute via MCP client
            result = await self.mcp_client.call_tool(
                tool["name"],
                params
            )
            
            return f"Successfully executed {tool['name']}: {result}"
            
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return f"Failed to execute {tool['name']}: {str(e)}"
    
    def _extract_parameters(self, tool: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Extract tool parameters from the message"""
        
        # This is simplified - in production, use an LLM to extract parameters
        # based on the tool's input schema
        
        params = {}
        
        # Example: Extract SKU from message
        if "sku" in tool.get("inputSchema", {}).get("properties", {}):
            # Look for SKU pattern
            import re
            sku_match = re.search(r'\b[A-Z]{2,}-\d{3,}\b', message)
            if sku_match:
                params["sku"] = sku_match.group()
                
        # Example: Extract search query
        if "query" in tool.get("inputSchema", {}).get("properties", {}):
            # Use the entire message as query (simplified)
            params["query"] = message
            
        return params


# Example usage in LangGraph
async def create_products_node():
    """Factory function to create the node for LangGraph"""
    
    agent = ProductsAgent()
    await agent.initialize()
    
    # Return the callable that LangGraph will use
    return agent


# Example of how to add this to a LangGraph workflow
"""
from langgraph.graph import StateGraph, END

async def build_graph():
    # Create the graph
    graph = StateGraph(MessagesState)
    
    # Create and add the products agent node
    products_node = await create_products_node()
    graph.add_node("products_agent", products_node)
    
    # Add routing logic
    graph.add_edge("START", "products_agent")
    graph.add_edge("products_agent", END)
    
    # Compile the graph
    return graph.compile()
"""