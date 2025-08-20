"""
Orchestrator admin endpoints (reload dynamic agents, status)
"""
from fastapi import APIRouter
import logging
from typing import Any, Dict

from app.orchestrator import get_orchestrator, reload_orchestrator_agents, get_orchestrator_agent_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator-admin"])

@router.post("/reload-dynamic-agents")
async def reload_dynamic_agents() -> Dict[str, Any]:
    """Reload dynamic agents from the database into the orchestrator.

    Returns the number of dynamic agents loaded and total agents available.
    """
    try:
        result = await reload_orchestrator_agents()
        logger.info(f"Successfully reloaded dynamic agents: {result}")
        return {
            "success": True,
            "message": "Dynamic agents reloaded successfully",
            "result": result
        }
    except Exception as e:
        logger.error(f"Failed to reload dynamic agents: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/status")
async def orchestrator_status() -> Dict[str, Any]:
    """Return detailed orchestrator status including all registered agents."""
    try:
        agent_info = get_orchestrator_agent_info()
        return {
            "success": True,
            "status": "active",
            **agent_info
        }
    except Exception as e:
        logger.error(f"Failed to get orchestrator status: {e}")
        return {
            "success": False,
            "error": str(e)
        }

