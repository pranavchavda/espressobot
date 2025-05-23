"""
HTTP wrapper for MCP servers to make them accessible via HTTP for OpenAI's MCP integration.
"""
import os
import json
import asyncio
import subprocess
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MCP HTTP Wrapper")

# CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MCPRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}
    read_timeout_seconds: int = 30

# Store running processes to manage them
active_processes: Dict[str, subprocess.Popen] = {}

def run_mcp_command(command: str, args: list, input_data: Optional[Dict] = None, timeout: int = 30) -> Dict:
    """Run an MCP command and return the result."""
    try:
        process = subprocess.Popen(
            [command] + args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=os.environ.copy()
        )
        
        # Add to active processes
        process_id = str(process.pid)
        active_processes[process_id] = process
        
        try:
            # Send input if provided
            if input_data:
                stdout, stderr = process.communicate(input=json.dumps(input_data), timeout=timeout)
            else:
                stdout, stderr = process.communicate(timeout=timeout)
                
            # Check if process completed successfully
            if process.returncode != 0:
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "MCP command failed",
                        "stderr": stderr,
                        "returncode": process.returncode
                    }
                )
                
            try:
                return json.loads(stdout)
            except json.JSONDecodeError:
                return {"output": stdout.strip()}
                
        except subprocess.TimeoutExpired:
            process.kill()
            raise HTTPException(status_code=504, detail="MCP command timed out")
            
    except Exception as e:
        logger.error(f"Error running MCP command: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Clean up
        if process_id in active_processes:
            del active_processes[process_id]

@app.post("/mcp/invoke")
async def invoke_mcp(request: MCPRequest):
    """Generic endpoint to invoke any MCP tool."""
    tool_name = request.tool_name
    args = request.arguments
    
    # Map tool names to their respective commands
    tool_commands = {
        "shopify-dev-mcp": {"command": "npx", "args": ["@shopify/dev-mcp"]},
        "perplexity-ask": {"command": "npx", "args": ["server-perplexity-ask"]},
        "sequential-thinking": {"command": "npx", "args": ["@modelcontextprotocol/server-sequential-thinking"]},
        "fetch": {"command": "python", "args": ["-m", "mcp_server_fetch"]},
    }
    
    if tool_name not in tool_commands:
        raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")
    
    cmd = tool_commands[tool_name]
    return run_mcp_command(
        command=cmd["command"],
        args=cmd["args"],
        input_data={"tool_name": tool_name, "arguments": args},
        timeout=request.read_timeout_seconds
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
