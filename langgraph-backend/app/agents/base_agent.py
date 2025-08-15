"""
Base agent class without LangGraph dependencies
Provides stateful, async-native agent capabilities with tool execution
"""
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
import json
import logging
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AgentResponse:
    """Response from an agent execution"""
    content: str
    tool_calls: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None
    
class BaseAgent(ABC):
    """Base class for all agents - handles tool execution and state management"""
    
    def __init__(self):
        self.name = "base"
        self.description = "Base agent"
        self.tools: Dict[str, BaseTool] = {}
        self.model = None
        self.conversation_state = {}  # Persistent state across calls
        self.operations_performed = []  # Track what the agent has done
        
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass
    
    @abstractmethod
    def _get_tools(self) -> List[BaseTool]:
        """Get the tools available to this agent"""
        pass
    
    def _initialize_tools(self):
        """Initialize tools dictionary for easy lookup"""
        tools = self._get_tools()
        self.tools = {tool.name: tool for tool in tools}
        logger.info(f"Initialized {self.name} agent with {len(self.tools)} tools")
        
    async def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """Execute a tool and return its result"""
        if tool_name not in self.tools:
            return f"Error: Tool {tool_name} not found"
        
        tool = self.tools[tool_name]
        try:
            # Handle both BaseTool objects and dict-based tools
            if hasattr(tool, '_arun'):
                result = await tool._arun(**tool_args)
            elif hasattr(tool, '_run'):
                # Fall back to sync version in thread pool
                result = await asyncio.get_event_loop().run_in_executor(
                    None, tool._run, **tool_args
                )
            elif hasattr(tool, 'invoke'):
                # Some tools use invoke method
                result = await tool.invoke(**tool_args)
            else:
                # Tool doesn't have a known execution method
                return f"Error: Tool {tool_name} doesn't have a known execution method"
            
            # Track the operation
            self.operations_performed.append({
                "tool": tool_name,
                "args": tool_args,
                "success": True
            })
            
            # Convert result to string if needed
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
            
        except Exception as e:
            logger.error(f"Tool execution error ({tool_name}): {e}")
            self.operations_performed.append({
                "tool": tool_name,
                "args": tool_args,
                "success": False,
                "error": str(e)
            })
            return f"Error executing {tool_name}: {str(e)}"
    
    def _build_context_prompt(self, state: Dict[str, Any]) -> str:
        """Build context-aware prompt from state and conversation history"""
        messages = state.get("messages", [])
        
        # Extract conversation context
        context_parts = []
        for msg in messages[-10:]:  # Last 10 messages
            if isinstance(msg, HumanMessage):
                context_parts.append(f"User: {msg.content[:500]}")
            elif isinstance(msg, AIMessage):
                # Only include non-error messages
                if not msg.metadata.get("error"):
                    context_parts.append(f"Assistant: {msg.content[:500]}")
        
        conversation_context = "\n".join(context_parts[-6:])  # Last 3 exchanges
        
        # Build operations context
        operations_context = ""
        if self.operations_performed:
            ops = []
            for op in self.operations_performed[-5:]:  # Last 5 operations
                if op["success"]:
                    ops.append(f"- Used {op['tool']} successfully")
                else:
                    ops.append(f"- Failed to use {op['tool']}: {op.get('error', 'Unknown error')}")
            operations_context = "\n## Previous Operations:\n" + "\n".join(ops)
            operations_context += "\n**Note: You have already performed these operations. Build on them, don't repeat.**"
        
        # Get memory context if available
        memory_context = ""
        if state.get("memory_context"):
            memories = state["memory_context"][:3]
            memory_parts = [f"- {m['content']}" for m in memories]
            memory_context = "\n## Relevant Context:\n" + "\n".join(memory_parts)
        
        return f"""
## Conversation Context:
{conversation_context}

{memory_context}

{operations_context}
"""
    
    async def think_and_act(self, message: str, state: Dict[str, Any]) -> AgentResponse:
        """
        Main agent logic - think about the request and take action
        Uses ReAct pattern: Reasoning + Acting
        """
        if not self.model:
            raise ValueError(f"Model not initialized for {self.name} agent")
        
        # Build enhanced prompt with context
        system_prompt = self._get_system_prompt()
        context_prompt = self._build_context_prompt(state)
        
        # Format tools for the prompt
        tools_description = self._format_tools_for_prompt()
        
        # Create the full prompt
        full_prompt = f"""{system_prompt}

{context_prompt}

## Available Tools:
{tools_description}

## Instructions:
1. Analyze the user's request
2. Use tools as needed to fulfill the request
3. Provide a helpful response based on the results

When you need to use a tool, respond with:
TOOL_CALL: {{
    "tool": "tool_name",
    "args": {{"arg1": "value1", "arg2": "value2"}}
}}

After receiving tool results, continue with your response or make additional tool calls as needed.

Current request: {message}"""
        
        # Start the reasoning loop
        max_iterations = 5
        iteration = 0
        accumulated_response = []
        
        while iteration < max_iterations:
            iteration += 1
            
            # Get LLM response
            if iteration == 1:
                # First iteration - full prompt
                response = await self.model.ainvoke(full_prompt)
            else:
                # Subsequent iterations - continue conversation
                response = await self.model.ainvoke(
                    f"Continue based on the tool result. You can make more tool calls or provide the final response.\n\nTool result:\n{tool_result}"
                )
            
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Check if the response contains a tool call
            if "TOOL_CALL:" in response_text:
                # Extract and execute tool call
                try:
                    tool_call_json = response_text.split("TOOL_CALL:")[1].strip()
                    # Find the JSON object
                    import re
                    json_match = re.search(r'\{.*\}', tool_call_json, re.DOTALL)
                    if json_match:
                        tool_call = json.loads(json_match.group())
                        tool_name = tool_call.get("tool")
                        tool_args = tool_call.get("args", {})
                        
                        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                        tool_result = await self._execute_tool(tool_name, tool_args)
                        
                        # Add the part before the tool call to accumulated response
                        before_tool = response_text.split("TOOL_CALL:")[0].strip()
                        if before_tool:
                            accumulated_response.append(before_tool)
                        
                        # Continue the loop with the tool result
                        continue
                except Exception as e:
                    logger.error(f"Failed to parse/execute tool call: {e}")
                    accumulated_response.append(f"Error with tool execution: {str(e)}")
                    break
            else:
                # No tool call, this is the final response
                accumulated_response.append(response_text)
                break
        
        # Combine all response parts
        final_response = "\n\n".join(accumulated_response)
        
        return AgentResponse(
            content=final_response,
            metadata={
                "agent": self.name,
                "iterations": iteration,
                "operations_performed": len(self.operations_performed)
            }
        )
    
    def _format_tools_for_prompt(self) -> str:
        """Format available tools for the prompt"""
        tool_descriptions = []
        for name, tool in self.tools.items():
            # Handle both BaseTool objects and dict-based tools
            if hasattr(tool, 'description'):
                desc = f"- **{name}**: {tool.description}"
            elif isinstance(tool, dict) and 'description' in tool:
                desc = f"- **{name}**: {tool['description']}"
            else:
                desc = f"- **{name}**: (no description)"
                
            if hasattr(tool, 'args_schema') and hasattr(tool.args_schema, 'schema'):
                # Add parameter information
                schema = tool.args_schema.schema()
                properties = schema.get('properties', {})
                if properties:
                    params = []
                    for param_name, param_info in properties.items():
                        param_desc = param_info.get('description', 'No description')
                        required = param_name in schema.get('required', [])
                        params.append(f"    - {param_name}: {param_desc} {'(required)' if required else '(optional)'}")
                    desc += "\n" + "\n".join(params)
            tool_descriptions.append(desc)
        
        return "\n".join(tool_descriptions)
    
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
            
            # Process the request
            logger.info(f"🚀 Running {self.name} agent with message: {last_message.content[:100]}...")
            response = await self.think_and_act(last_message.content, state)
            logger.info(f"✅ {self.name} agent completed")
            
            # Add response to state
            state["messages"].append(AIMessage(
                content=response.content,
                metadata={
                    "agent": self.name,
                    **response.metadata
                }
            ))
            
            # Update conversation state
            self.conversation_state["last_response"] = response.content
            self.conversation_state["operations_count"] = len(self.operations_performed)
            
            state["last_agent"] = self.name
            return state
            
        except Exception as e:
            logger.error(f"Error in {self.name} agent: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in {self.name} agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state