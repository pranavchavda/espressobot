"""
WebSocket API for real-time task updates
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json

from app.orchestrator_async import get_async_orchestrator

logger = logging.getLogger(__name__)
router = APIRouter()

@router.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for real-time task updates
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for thread {thread_id}")
    
    orchestrator = await get_async_orchestrator()
    
    try:
        # Add websocket to orchestrator for updates
        await orchestrator.add_websocket(thread_id, websocket)
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "thread_id": thread_id,
            "message": "WebSocket connection established"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                # Handle different message types
                if message_data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
                elif message_data.get("type") == "get_task_status":
                    task_id = message_data.get("task_id")
                    if task_id:
                        task_status = orchestrator.get_task_status(task_id)
                        if task_status:
                            await websocket.send_json({
                                "type": "task_status",
                                "task_id": task_id,
                                "status": task_status.status.value,
                                "message": task_status.message,
                                "progress": task_status.progress,
                                "response": task_status.response,
                                "updated_at": task_status.updated_at.isoformat()
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Task {task_id} not found"
                            })
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error", 
                    "message": "Invalid JSON"
                })
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e)
                })
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for thread {thread_id}")
    except Exception as e:
        logger.error(f"WebSocket error for thread {thread_id}: {e}")
    finally:
        # Clean up websocket connection
        try:
            await orchestrator.remove_websocket(thread_id, websocket)
        except Exception as e:
            logger.error(f"Error removing websocket: {e}")

@router.websocket("/ws/task/{task_id}")
async def task_websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket endpoint for specific task updates
    """
    await websocket.accept()
    logger.info(f"Task WebSocket connected for task {task_id}")
    
    orchestrator = await get_async_orchestrator()
    
    try:
        # Send initial task status
        task_status = orchestrator.get_task_status(task_id)
        if task_status:
            await websocket.send_json({
                "type": "task_status",
                "task_id": task_id,
                "status": task_status.status.value,
                "message": task_status.message,
                "progress": task_status.progress,
                "response": task_status.response,
                "updated_at": task_status.updated_at.isoformat()
            })
        else:
            await websocket.send_json({
                "type": "error",
                "message": f"Task {task_id} not found"
            })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                
                if message_data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Task WebSocket error: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"Task WebSocket disconnected for task {task_id}")
    except Exception as e:
        logger.error(f"Task WebSocket error for task {task_id}: {e}")