"""
Test endpoint for A2A orchestrator pattern
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging
from app.orchestrator_a2a import A2AOrchestrator

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize A2A orchestrator
a2a_orchestrator = None

class TestRequest(BaseModel):
    message: str
    thread_id: str = "test-a2a-thread"

@router.post("/test-a2a")
async def test_a2a_orchestration(request: TestRequest) -> Dict[str, Any]:
    """Test the A2A orchestration pattern"""
    global a2a_orchestrator
    
    try:
        # Initialize orchestrator if needed
        if not a2a_orchestrator:
            logger.info("Initializing A2A Orchestrator...")
            a2a_orchestrator = A2AOrchestrator()
        
        # Run the orchestrator
        logger.info(f"Testing A2A with message: {request.message}")
        result = await a2a_orchestrator.run(
            message=request.message,
            thread_id=request.thread_id
        )
        
        return {
            "success": True,
            "response": result.get("response"),
            "execution_path": result.get("execution_path"),
            "agents_involved": result.get("agents_involved"),
            "a2a_requests": result.get("a2a_requests"),
            "pattern": "a2a_orchestration"
        }
        
    except Exception as e:
        logger.error(f"A2A test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))