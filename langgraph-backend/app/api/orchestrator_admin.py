"""
Orchestrator admin endpoints (reload dynamic agents, status)
"""
from fastapi import APIRouter
import logging
from typing import Any, Dict

from app.api.chat import get_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator-admin"])

@router.post("/reload-dynamic-agents")
async def reload_dynamic_agents() -> Dict[str, Any]:
    """Reload dynamic agents from the database into the orchestrator.

    Returns the number of dynamic agents loaded and total agents available.
    """
    orch = get_orchestrator()
    await orch._load_dynamic_agents()
    loaded = getattr(orch, "_dynamic_agents", []) or []
    logger.info(f"Reloaded dynamic agents: {len(loaded)} loaded")
    return {
        "success": True,
        "dynamic_agents_loaded": len(loaded),
        "total_agents": len(orch.agents)
    }

@router.get("/status")
async def orchestrator_status() -> Dict[str, Any]:
    """Return a brief orchestrator status including agent names."""
    orch = get_orchestrator()
    names = list(orch.agents.keys())
    dyn = [getattr(a, 'name', '') for a in getattr(orch, '_dynamic_agents', [])]
    return {
        "success": True,
        "agents": names,
        "dynamic_agents": dyn,
        "total": len(names),
        "dynamic_total": len(dyn)
    }

