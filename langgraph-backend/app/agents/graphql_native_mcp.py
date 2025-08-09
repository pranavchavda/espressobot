"""
GraphQL Agent using native LangChain MCP support with MultiServerMCPClient
"""
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
import logging
import os
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

# Import the model manager
from app.config.agent_model_manager import agent_model_manager

# Import context mixin for A2A context handling
from app.agents.base_context_mixin import ContextAwareMixin

class GraphQLAgentNativeMCP(ContextAwareMixin):
    """GraphQL agent using native LangChain MCP integration with MultiServerMCPClient"""
    
    def __init__(self):
        self.name = "graphql"
        self.description = "Executes custom GraphQL queries and mutations"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")

        self.client = None
        self.tools = None
        self.agent = None
        self.system_prompt = self._get_system_prompt()
        
    async def _ensure_mcp_connected(self):
        """Ensure MCP client and agent are initialized"""
        if not self.agent:
            try:
                # Initialize MultiServerMCPClient with GraphQL server
                self.client = MultiServerMCPClient({
                    "graphql": {
                        "command": "python3",
                        "args": [str(Path("/home/pranav/espressobot/frontend/python-tools/mcp-graphql-server.py"))],
                        "transport": "stdio",
                        "env": {
                            **os.environ,
                            "PYTHONPATH": "/home/pranav/espressobot/frontend/python-tools"
                        }
                    }
                })
                
                # Get tools from client
                self.tools = await self.client.get_tools()
                
                # Create react agent with tools
                self.agent = create_react_agent(
                    self.model,
                    self.tools,
                    state_modifier=self.system_prompt
                )
                
                logger.info(f"Connected to GraphQL MCP server with {len(self.tools)} tools")
                
            except Exception as e:
                logger.error(f"Failed to initialize MCP client: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        return """You are a GraphQL specialist agent with expertise in Shopify's Admin API.

You have access to GraphQL tools through the MCP server. Use these tools to execute custom queries 
and mutations against the Shopify Admin API.

Available tools include:
- graphql_query: Execute GraphQL queries on Shopify Admin API
- graphql_mutation: Execute GraphQL mutations on Shopify Admin API

## Your Expertise:
- Shopify Admin API GraphQL schema
- Query optimization and performance
- Mutation structure and error handling
- Bulk operations and data fetching
- Custom API operations

## GraphQL Query Capabilities:
- Fetch specific fields efficiently
- Complex nested queries
- Pagination with cursors
- Query cost tracking
- Filter and search operations

## GraphQL Mutation Capabilities:
- Product and variant updates
- Metafield operations
- Bulk mutations
- User error handling
- Atomic operations

## Best Practices:
- Check userErrors in mutation responses
- Use variables for dynamic values
- Optimize query cost
- Request only needed fields
- Handle pagination properly

## Common Operations:
- Product queries with specific fields
- Variant bulk updates
- Metafield management
- Collection operations
- Order and customer queries

## Query Structure:
```graphql
query {
  product(id: "gid://shopify/Product/123") {
    title
    variants(first: 10) {
      edges {
        node {
          sku
          price
        }
      }
    }
  }
}
```

## Mutation Structure:
```graphql
mutation productUpdate($input: ProductInput!) {
  productUpdate(input: $input) {
    product {
      id
      title
    }
    userErrors {
      field
      message
    }
  }
}
```

IMPORTANT: 
- Always check for errors in responses
- Use proper GID format for IDs
- Test queries before mutations
- Prefer specialized tools for common operations

Always provide clear, formatted responses with query/mutation results and handle errors gracefully."""
    
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
            
            # Use context-aware messages from the mixin
            context_aware_messages = self.build_context_aware_messages(state, self.system_prompt)
            
            # Use the agent to process the request with context
            agent_state = {"messages": context_aware_messages}
            
            # Run the agent
            logger.info(f"🚀 Running GraphQL agent with context-aware prompt with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ GraphQL agent completed")
            
            # Extract the response
            if result.get("messages"):
                # Get the last AI message from the agent's response
                agent_messages = result["messages"]
                for msg in reversed(agent_messages):
                    if hasattr(msg, 'content') and msg.content:
                        state["messages"].append(AIMessage(
                            content=msg.content,
                            metadata={"agent": self.name}
                        ))
                        break
            else:
                state["messages"].append(AIMessage(
                    content="I processed your request but couldn't generate a response.",
                    metadata={"agent": self.name}
                ))
            
            state["last_agent"] = self.name
            return state
            
        except Exception as e:
            logger.error(f"Error in GraphQLAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in GraphQL agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        keywords = ["graphql", "query", "mutation", "admin api", "custom query",
                   "bulk operation", "gid", "shopify api", "api query"]
        
        content = last_message.content.lower()
        return any(keyword in content for keyword in keywords)