"""
Enhanced chat endpoint with A2A orchestration support
"""
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional
import json
import logging
import asyncio
import time
from app.orchestrator import Orchestrator
from app.orchestrator_a2a import A2AOrchestrator
from pydantic import BaseModel
from langchain_anthropic import ChatAnthropic
import os

logger = logging.getLogger(__name__)
router = APIRouter()

_orchestrator: Optional[Orchestrator] = None
_a2a_orchestrator: Optional[A2AOrchestrator] = None
_complexity_analyzer = None

def get_orchestrator() -> Orchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator

def get_a2a_orchestrator() -> A2AOrchestrator:
    """Get or create the global A2A orchestrator instance"""
    global _a2a_orchestrator
    if _a2a_orchestrator is None:
        _a2a_orchestrator = A2AOrchestrator()
    return _a2a_orchestrator

def get_complexity_analyzer():
    """Get complexity analyzer model"""
    global _complexity_analyzer
    if _complexity_analyzer is None:
        _complexity_analyzer = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0.0,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
    return _complexity_analyzer

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    conv_id: Optional[str] = None
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    thread_id: Optional[str] = None
    mode: Optional[str] = "auto"  # "auto", "simple", "a2a"

async def analyze_complexity(message: str) -> Dict[str, Any]:
    """Analyze if request needs A2A orchestration"""
    analyzer = get_complexity_analyzer()
    
    prompt = """Analyze this request and determine if it needs multiple agents to collaborate.

Complex (needs A2A):
- Requests that need data from multiple sources
- Questions combining product details with pricing/inventory
- Multi-step operations requiring agent coordination
- Requests explicitly asking for comprehensive information

Simple (single agent):
- Direct lookups (price, SKU, etc.)
- Single-domain questions
- Basic information requests
- Greetings or general chat

Request: {message}

Return JSON: {{"pattern": "simple|a2a", "reason": "...", "likely_agents": ["..."]}}"""
    
    try:
        response = analyzer.invoke([
            {"role": "system", "content": prompt},
            {"role": "user", "content": message}
        ])
        
        import re
        json_match = re.search(r'\{[^}]+\}', response.content)
        if json_match:
            result = json.loads(json_match.group())
            return result
    except Exception as e:
        logger.error(f"Complexity analysis failed: {e}")
    
    return {"pattern": "simple", "reason": "Default to simple pattern"}

@router.post("/stream")
async def enhanced_chat_stream(request: ChatRequest):
    """Enhanced streaming endpoint with A2A support"""
    
    # Determine conversation/thread ID
    conversation_id = request.conv_id or request.conversation_id
    thread_id = request.thread_id or conversation_id or f"chat-{int(time.time())}"
    
    # Determine orchestration mode
    if request.mode == "auto":
        complexity = await analyze_complexity(request.message)
        use_a2a = complexity["pattern"] == "a2a"
        logger.info(f"🧠 Complexity analysis: {complexity['pattern']} - {complexity['reason']}")
    elif request.mode == "a2a":
        use_a2a = True
        complexity = {"pattern": "a2a", "reason": "Forced A2A mode"}
    else:
        use_a2a = False
        complexity = {"pattern": "simple", "reason": "Forced simple mode"}
    
    async def generate():
        try:
            # Send conversation ID and pattern info
            yield json.dumps({
                "event": "conversation_id",
                "conv_id": thread_id,
                "thread_id": thread_id,
                "pattern": complexity["pattern"],
                "analysis": complexity.get("reason", "")
            }) + "\n"
            
            if use_a2a:
                # Use A2A orchestrator
                logger.info(f"🔄 Using A2A orchestration for: {request.message[:50]}...")
                
                yield json.dumps({
                    "event": "agent_message",
                    "agent": "A2A-Orchestrator",
                    "message": "Coordinating multiple agents for comprehensive response...",
                    "tokens": []
                }) + "\n"
                
                a2a_orchestrator = get_a2a_orchestrator()
                
                # Run A2A orchestration
                result = await a2a_orchestrator.run(
                    message=request.message,
                    thread_id=thread_id
                )
                
                # Stream the response with execution metadata
                yield json.dumps({
                    "event": "a2a_metadata",
                    "execution_path": result.get("execution_path", []),
                    "agents_involved": result.get("agents_involved", []),
                    "a2a_requests": result.get("a2a_requests", [])
                }) + "\n"
                
                # Stream the final response
                response = result.get("response", "")
                for i in range(0, len(response), 20):  # Stream in chunks
                    chunk = response[i:i+20]
                    yield json.dumps({
                        "event": "agent_message",
                        "agent": "A2A-Synthesizer",
                        "message": response[:i+20],
                        "tokens": [chunk]
                    }) + "\n"
                    await asyncio.sleep(0.02)  # Small delay for streaming effect
                
            else:
                # Use simple orchestrator
                logger.info(f"📍 Using simple orchestration for: {request.message[:50]}...")
                
                orchestrator = get_orchestrator()
                
                buffer = ""
                current_agent = "Orchestrator"
                token_buffer = ""
                
                async for chunk in orchestrator.stream(
                    message=request.message,
                    conversation_id=conversation_id,
                    user_id=request.user_id,
                    context=request.context,
                    thread_id=thread_id
                ):
                    if chunk["type"] == "token":
                        content = chunk["content"]
                        if isinstance(content, list):
                            content = "".join(str(c) for c in content)
                        else:
                            content = str(content)
                        
                        new_agent = chunk.get("agent", current_agent)
                        if new_agent != current_agent:
                            buffer = ""
                            token_buffer = ""
                            current_agent = new_agent
                        
                        buffer += content
                        token_buffer += content
                        
                        if len(token_buffer) >= 3 or content.endswith(('.', '!', '?', '\n')):
                            yield json.dumps({
                                "event": "agent_message",
                                "agent": current_agent,
                                "message": buffer,
                                "tokens": [token_buffer]
                            }) + "\n"
                            token_buffer = ""
                    
                    elif chunk["type"] == "agent_switch":
                        current_agent = chunk["agent"]
                        yield json.dumps({
                            "event": "agent_switch",
                            "agent": current_agent
                        }) + "\n"
                
                # Send final chunk if any
                if token_buffer:
                    yield json.dumps({
                        "event": "agent_message",
                        "agent": current_agent,
                        "message": buffer,
                        "tokens": [token_buffer]
                    }) + "\n"
            
            # Send completion event
            yield json.dumps({
                "event": "done",
                "agent": "A2A-Orchestrator" if use_a2a else current_agent,
                "pattern": complexity["pattern"]
            }) + "\n"
            
        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield json.dumps({
                "event": "error",
                "error": str(e)
            }) + "\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/test-a2a")
async def test_a2a_endpoint(request: ChatRequest):
    """Test endpoint to force A2A orchestration"""
    request.mode = "a2a"
    return await enhanced_chat_stream(request)