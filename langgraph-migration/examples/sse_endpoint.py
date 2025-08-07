"""
Example SSE (Server-Sent Events) endpoint implementation for FastAPI.
Maintains compatibility with the existing React frontend.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="EspressoBot LangGraph API")

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class Message(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None


class ChatRequest(BaseModel):
    messages: List[Message]
    conversation_id: Optional[str] = None
    user_id: str
    stream: Optional[bool] = True


# Mock orchestrator for demonstration
class MockOrchestrator:
    """Mock orchestrator that simulates LangGraph processing"""
    
    async def process_stream(self, request: ChatRequest):
        """Simulate streaming responses"""
        
        # Simulate agent processing
        agents = ["Router", "ProductsAgent", "Orchestrator"]
        
        for agent in agents:
            # Simulate processing time
            await asyncio.sleep(0.5)
            
            # Yield agent status
            yield {
                "event": "agent_processing",
                "data": {
                    "agent": agent,
                    "status": "processing",
                    "message": f"{agent} is analyzing the request..."
                }
            }
        
        # Simulate token-by-token streaming
        response_text = "I'll help you with that request. Let me search for the product information."
        tokens = response_text.split()
        
        for i, token in enumerate(tokens):
            await asyncio.sleep(0.05)  # Simulate token generation time
            
            yield {
                "event": "agent_message",
                "data": {
                    "agent": "Assistant",
                    "message": token + " ",
                    "tokens": [token],
                    "isComplete": i == len(tokens) - 1
                }
            }
        
        # Final completion event
        yield {
            "event": "completion",
            "data": {
                "conversation_id": request.conversation_id or "new_conv_123",
                "message_count": len(request.messages) + 1,
                "tokens_used": len(tokens),
                "timestamp": datetime.utcnow().isoformat()
            }
        }


# Initialize orchestrator
orchestrator = MockOrchestrator()


@app.post("/api/agent/sse")
async def chat_sse(request: ChatRequest):
    """
    SSE endpoint that matches the current OpenAI SDK API.
    The React frontend expects this exact endpoint and event format.
    """
    
    async def event_generator():
        """Generate SSE events"""
        
        try:
            # Log the request
            logger.info(f"Processing chat request for user {request.user_id}")
            
            # Stream responses from orchestrator
            async for event in orchestrator.process_stream(request):
                # Format as SSE
                event_name = event["event"]
                event_data = json.dumps(event["data"])
                
                # SSE format: "event: name\ndata: json\n\n"
                yield {
                    "event": event_name,
                    "data": event_data
                }
                
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            
            # Send error event
            yield {
                "event": "error",
                "data": json.dumps({
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
            }
    
    # Return SSE response
    return EventSourceResponse(event_generator())


@app.post("/api/agent/chat")
async def chat_non_streaming(request: ChatRequest):
    """
    Non-streaming chat endpoint for simpler requests.
    Returns complete response at once.
    """
    
    # Collect all events
    events = []
    async for event in orchestrator.process_stream(request):
        events.append(event)
    
    # Extract final message
    message_parts = []
    for event in events:
        if event["event"] == "agent_message":
            message_parts.append(event["data"]["message"])
    
    final_message = "".join(message_parts)
    
    return {
        "message": final_message,
        "conversation_id": request.conversation_id or "new_conv_123",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "espressobot-langgraph",
        "timestamp": datetime.utcnow().isoformat()
    }


# WebSocket alternative (if needed)
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time bidirectional communication.
    Alternative to SSE if needed.
    """
    
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            # Create request
            request = ChatRequest(**data)
            
            # Stream responses
            async for event in orchestrator.process_stream(request):
                await websocket.send_json(event)
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# Example of maintaining exact compatibility with current API
class LangGraphSSEAdapter:
    """
    Adapter to ensure LangGraph events match the exact format
    expected by the current React frontend.
    """
    
    @staticmethod
    def format_agent_message(agent: str, content: str, tokens: List[str] = None):
        """Format agent message in expected format"""
        return {
            "event": "agent_message",
            "data": json.dumps({
                "agent": agent,
                "message": content,
                "tokens": tokens or [content],
                "timestamp": datetime.utcnow().isoformat()
            })
        }
    
    @staticmethod
    def format_agent_processing(agent: str, message: str, status: str = "processing"):
        """Format agent processing status"""
        return {
            "event": "agent_processing",
            "data": json.dumps({
                "agent": agent,
                "message": message,
                "status": status
            })
        }
    
    @staticmethod
    def format_error(error: str, code: Optional[str] = None):
        """Format error event"""
        return {
            "event": "error",
            "data": json.dumps({
                "error": error,
                "code": code,
                "timestamp": datetime.utcnow().isoformat()
            })
        }
    
    @staticmethod
    def format_completion(conversation_id: str, **kwargs):
        """Format completion event"""
        return {
            "event": "completion",
            "data": json.dumps({
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            })
        }


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )