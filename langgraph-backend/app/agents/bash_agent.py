"""
Bash Agent - LLM-powered agent that executes bash commands in a secure sandbox environment.

This agent can:
- Understand natural language requests for shell operations
- Run shell commands safely
- Download files from the internet
- Create and run scripts
- Generate reports and analysis
- Process data files
- Install packages (within sandbox)
- Provide intelligent explanations of command results

All operations are contained within the agent_sandbox directory.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from app.tools.bash_tool import bash_tool
from app.config.agent_model_manager import agent_model_manager

logger = logging.getLogger(__name__)

class BashAgent:
    """LLM-powered agent for executing bash commands in a secure sandbox."""
    
    def __init__(self):
        self.name = "bash"
        self.description = "Execute bash commands, scripts, and system operations in a secure sandbox"
        self.model = agent_model_manager.get_model_for_agent(self.name)
        logger.info(f"{self.name} agent initialized with model: {type(self.model).__name__}")
        self.system_prompt = self._get_system_prompt()
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for bash agent."""
        return """You are a bash execution agent. You can execute shell commands, scripts, and system operations in a secure sandbox environment.

Your capabilities include:
- Running shell commands safely (pwd, ls, echo, cat, etc.)
- Downloading files from the internet (curl, wget)
- Creating and executing scripts (Python, Node.js, bash)
- Installing packages (pip, npm, apt - within sandbox)
- Processing data files (CSV, JSON, text analysis)
- Generating reports and analysis
- File operations (create, modify, compress)

All operations are contained within a secure sandbox directory at: /home/pranav/espressobot/langgraph-backend/app/agent_sandbox
Files created are accessible via web URLs: /api/sandbox/{filename}

IMPORTANT INSTRUCTIONS:
1. When asked to execute a command, first understand what the user wants
2. Execute the appropriate bash command using your tools
3. Explain the results clearly and provide context
4. If files are created, mention their web URLs
5. For complex tasks, break them down into steps
6. Always be helpful and explain what each command does

RESPONSE FORMAT:
- First execute the command
- Then provide a clear explanation of what happened
- Include any relevant output or file information
- Suggest next steps if appropriate

You have access to a bash execution tool that runs commands in the sandbox."""
        
    async def process_request(self, request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process a bash execution request using LLM reasoning."""
        try:
            logger.info(f"Bash agent processing request: {request[:100]}...")
            
            # Build messages for LLM - simple approach
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=f"""I need you to help with this bash/shell request: {request}

Please:
1. Understand what the user wants to accomplish
2. Determine the appropriate bash command to run
3. Respond with the command in this format: EXECUTE: <command>
4. I will then execute it and provide you the results

For example:
- If asked for current directory: respond with "EXECUTE: pwd"
- If asked to list files: respond with "EXECUTE: ls -la" 
- If asked to create a file: respond with "EXECUTE: echo 'content' > filename.txt"

Start your response with EXECUTE: followed by the exact command to run.""")
            ]
            
            # Get LLM response
            try:
                response = await self.model.ainvoke(messages)
                response_text = response.content.strip()
                
                # Check if LLM wants to execute a command
                if response_text.startswith("EXECUTE:"):
                    command = response_text[8:].strip()  # Remove "EXECUTE: " prefix
                    
                    # Execute the bash command
                    bash_result = await bash_tool.execute_command(command)
                    
                    # Get final response from LLM with results
                    final_messages = messages + [
                        AIMessage(content=f"EXECUTE: {command}"),
                        HumanMessage(content=f"""Command executed successfully! Results:

Command: {command}
Success: {bash_result['success']}
Return code: {bash_result['return_code']}
Output: {bash_result.get('stdout', 'No output')}
Error: {bash_result.get('stderr', '')}
Working directory: {bash_result.get('working_directory', '')}
Created files: {bash_result.get('created_files', [])}

Please provide a helpful explanation of these results to the user. Be conversational and explain what the command did and what the output means.""")
                    ]
                    
                    final_response = await self.model.ainvoke(final_messages)
                    
                    return {
                        "success": bash_result["success"],
                        "agent": self.name,
                        "command": command,
                        "output": bash_result.get("stdout", ""),
                        "error": bash_result.get("stderr", ""),
                        "return_code": bash_result.get("return_code", 0),
                        "created_files": bash_result.get("created_files", []),
                        "working_directory": bash_result.get("working_directory", ""),
                        "explanation": final_response.content,
                        "response": final_response.content  # For orchestrator compatibility
                    }
                
                # No EXECUTE command, just return the LLM response
                return {
                    "success": True,
                    "agent": self.name,
                    "response": response_text,
                    "explanation": response_text
                }
                
            except Exception as llm_error:
                logger.error(f"LLM error in bash agent: {llm_error}")
                # Fallback to direct command execution if LLM fails
                return await self._fallback_command_execution(request)
                
        except Exception as e:
            logger.error(f"Error in bash agent: {e}")
            return {
                "success": False,
                "error": f"Bash agent error: {str(e)}",
                "agent": self.name
            }
    
    async def _fallback_command_execution(self, request: str) -> Dict[str, Any]:
        """Fallback method for direct command execution when LLM fails."""
        # Simple pattern matching for common commands
        if request.lower().startswith(('list files', 'show files', 'ls')):
            command = "ls -la"
        elif request.lower().startswith(('clean sandbox', 'clear sandbox')):
            result = await bash_tool.clean_sandbox()
            return {
                "success": result["success"],
                "agent": self.name,
                "response": f"Sandbox cleanup: {result.get('message', 'completed')}",
                "removed_files": result.get("removed_files", [])
            }
        elif 'pwd' in request.lower():
            command = "pwd"
        else:
            # Try to extract a command from the request
            command = request.replace("bash:", "").replace("execute:", "").strip()
        
        # Execute the command
        result = await bash_tool.execute_command(command)
        
        # Build response
        response_text = f"Executed command: `{command}`\n"
        if result["success"]:
            response_text += f"Output: {result.get('stdout', 'No output')}"
            if result.get("created_files"):
                file_links = [f"- [{f['name']}]({f['url']}) ({f['size']} bytes)" for f in result["created_files"]]
                response_text += f"\n\nCreated files:\n" + "\n".join(file_links)
        else:
            response_text += f"Error: {result.get('stderr', 'Command failed')}"
        
        return {
            "success": result["success"],
            "agent": self.name,
            "command": command,
            "output": result.get("stdout", ""),
            "error": result.get("stderr", ""),
            "return_code": result.get("return_code", 0),
            "created_files": result.get("created_files", []),
            "working_directory": result.get("working_directory", ""),
            "response": response_text
        }

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
            
            user_query = last_message.content
            logger.info(f"🚀 Bash agent processing query: {user_query[:100]}...")
            
            # Process the bash request
            result = await self.process_request(user_query)
            
            # Add response to state
            if result.get("success"):
                response_content = result.get("response", result.get("explanation", "Command executed successfully"))
                state["messages"].append(AIMessage(
                    content=response_content,
                    metadata={"agent": self.name}
                ))
            else:
                error_msg = result.get("error", "Unknown error occurred")
                state["messages"].append(AIMessage(
                    content=f"I encountered an error: {error_msg}",
                    metadata={"agent": self.name, "error": True}
                ))
            
            state["last_agent"] = self.name
            logger.info(f"✅ Bash agent completed")
            return state
            
        except Exception as e:
            logger.error(f"Error in BashAgent.__call__: {e}")
            state["messages"].append(AIMessage(
                content=f"I encountered an error: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state

    def get_capabilities(self) -> List[str]:
        """Return list of bash agent capabilities."""
        return [
            "Execute shell commands in secure sandbox",
            "Download files from internet (curl, wget)",
            "Create and run scripts (Python, Node.js, etc.)",
            "Install packages with pip, npm, etc.",
            "Process data files (CSV, JSON, text)",
            "Generate reports and analysis",
            "File operations (create, modify, compress)",
            "System information gathering",
            "Network testing and API calls",
            "List and manage sandbox files"
        ]
    
    def get_example_requests(self) -> List[str]:
        """Return example requests for this agent."""
        return [
            "curl -o data.json https://api.example.com/data",
            "python3 -c \"print('Hello from sandbox')\"",
            "ls -la",
            "wget https://example.com/file.zip && unzip file.zip",
            "pip install requests && python3 -c \"import requests; print(requests.get('https://httpbin.org/json').json())\"",
            "echo 'test data' > test.txt && cat test.txt",
            "list files",
            "clean sandbox"
        ]