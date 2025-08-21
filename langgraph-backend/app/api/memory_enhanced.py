"""Enhanced Memory API endpoints with full CRUD and management capabilities"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import csv
import io
import logging
from enum import Enum

logger = logging.getLogger(__name__)
router = APIRouter(tags=["memory"])

# ==================== Request/Response Models ====================

class MemoryCategory(str, Enum):
    """Memory categories"""
    PRODUCTS = "products"
    PREFERENCES = "preferences"
    INTERACTIONS = "interactions"
    FACTS = "facts"
    PROBLEMS = "problems"
    SOLUTIONS = "solutions"
    GENERAL = "general"

class MemoryResponse(BaseModel):
    """Memory response model"""
    id: str  # UUID string from database
    user_id: str
    content: str
    category: Optional[str]
    importance_score: float
    access_count: int
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None
    similarity_score: Optional[float] = None

class MemoryCreateRequest(BaseModel):
    """Create memory request"""
    content: str = Field(..., min_length=1, max_length=5000)
    category: Optional[MemoryCategory] = MemoryCategory.GENERAL
    importance_score: float = Field(1.0, ge=0.0, le=10.0)
    metadata: Optional[Dict[str, Any]] = {}

class MemoryUpdateRequest(BaseModel):
    """Update memory request"""
    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    category: Optional[MemoryCategory] = None
    importance_score: Optional[float] = Field(None, ge=0.0, le=10.0)
    metadata: Optional[Dict[str, Any]] = None

class MemoryBulkOperation(BaseModel):
    """Bulk memory operation"""
    operation: str = Field(..., pattern="^(delete|update|export)$")
    memory_ids: List[str]  # UUID strings
    updates: Optional[MemoryUpdateRequest] = None

class MemorySearchRequest(BaseModel):
    """Memory search request"""
    query: str
    limit: int = Field(10, ge=1, le=100)
    similarity_threshold: float = Field(0.7, ge=0.0, le=1.0)
    category: Optional[MemoryCategory] = None
    importance_min: Optional[float] = None

class MemoryDashboardResponse(BaseModel):
    """Memory dashboard response"""
    stats: Dict[str, Any]
    recent_memories: List[MemoryResponse]
    important_memories: List[MemoryResponse]
    memory_timeline: List[Dict[str, Any]]
    category_distribution: Dict[str, int]

# ==================== Dependencies ====================

async def get_memory_manager():
    """Get memory manager instance"""
    from app.memory.shared_manager import get_shared_memory_manager
    return await get_shared_memory_manager()

async def verify_user_access(user_id: str, memory_id: Optional[int] = None):
    """Verify user has access to memory"""
    # In production, this would check authentication and authorization
    # For now, just return True
    return True

# ==================== Dashboard Endpoints ====================

@router.get("/dashboard/{user_id}", response_model=MemoryDashboardResponse)
async def get_memory_dashboard(
    user_id: str,
    days: int = Query(30, description="Number of days for timeline")
):
    """Get comprehensive memory dashboard for user"""
    try:
        manager = await get_memory_manager()
        
        # Get statistics
        stats = await manager.get_user_memory_stats(user_id)
        
        # Get recent memories
        recent_query = """
        SELECT * FROM memories 
        WHERE user_id = $1 AND status = 'active'
        ORDER BY created_at DESC 
        LIMIT 10
        """
        recent_results = await manager._execute_query(recent_query, user_id)
        recent_memories = [_row_to_memory(row) for row in recent_results]
        
        # Get important memories
        important_query = """
        SELECT * FROM memories 
        WHERE user_id = $1 AND status = 'active' AND importance_score >= 0.8
        ORDER BY importance_score DESC, access_count DESC
        LIMIT 10
        """
        important_results = await manager._execute_query(important_query, user_id)
        important_memories = [_row_to_memory(row) for row in important_results]
        
        # Get memory timeline
        timeline_query = """
        SELECT DATE(created_at) as date, COUNT(*) as count, 
               AVG(importance_score) as avg_importance
        FROM memories 
        WHERE user_id = $1 AND status = 'active' AND created_at >= $2
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        timeline_results = await manager._execute_query(timeline_query, user_id, cutoff_date)
        
        memory_timeline = [
            {
                "date": row['date'].isoformat(),
                "count": row['count'],
                "avg_importance": float(row['avg_importance'])
            }
            for row in timeline_results
        ]
        
        # Get category distribution
        category_query = """
        SELECT category, COUNT(*) as count
        FROM memories
        WHERE user_id = $1 AND status = 'active'
        GROUP BY category
        """
        category_results = await manager._execute_query(category_query, user_id)
        category_distribution = {
            row['category'] or 'uncategorized': row['count']
            for row in category_results
        }
        
        # Don't close the shared manager
        
        return MemoryDashboardResponse(
            stats=stats,
            recent_memories=recent_memories,
            important_memories=important_memories,
            memory_timeline=memory_timeline,
            category_distribution=category_distribution
        )
        
    except Exception as e:
        logger.error(f"Error getting memory dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== CRUD Endpoints ====================

@router.get("/list/{user_id}", response_model=List[MemoryResponse])
async def list_memories(
    user_id: str,
    category: Optional[MemoryCategory] = None,
    importance_min: Optional[float] = Query(None, ge=0.0, le=10.0),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """List user memories with filtering"""
    try:
        manager = await get_memory_manager()
        
        # Build query with filters
        query_parts = ["SELECT * FROM memories WHERE user_id = $1 AND status = 'active'"]
        params = [user_id]
        param_count = 1
        
        if category:
            param_count += 1
            query_parts.append(f"AND category = ${param_count}")
            params.append(category.value)
        
        if importance_min is not None:
            param_count += 1
            query_parts.append(f"AND importance_score >= ${param_count}")
            params.append(importance_min)
        
        query_parts.append("ORDER BY importance_score DESC, created_at DESC")
        
        param_count += 1
        query_parts.append(f"LIMIT ${param_count}")
        params.append(limit)
        
        param_count += 1
        query_parts.append(f"OFFSET ${param_count}")
        params.append(offset)
        
        query = " ".join(query_parts)
        results = await manager._execute_query(query, *params)
        
        memories = [_row_to_memory(row) for row in results]
        
        # Don't close the shared manager
        
        return memories
        
    except Exception as e:
        logger.error(f"Error listing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{memory_id}", response_model=MemoryResponse)
async def get_memory(memory_id: str, user_id: str = Query(...)):
    """Get specific memory by ID"""
    try:
        manager = await get_memory_manager()
        
        query = """
        SELECT * FROM memories 
        WHERE id = $1 AND user_id = $2 AND status = 'active'
        """
        result = await manager._execute_one(query, memory_id, user_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        # Update access count
        await manager._update_memory_access(memory_id)
        
        memory = _row_to_memory(result)
        
        # Don't close the shared manager
        
        return memory
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create/{user_id}", response_model=MemoryResponse)
async def create_memory(
    user_id: str,
    request: MemoryCreateRequest
):
    """Create a new memory"""
    try:
        from app.memory.postgres_memory_manager import Memory
        
        manager = await get_memory_manager()
        
        memory = Memory(
            user_id=user_id,
            content=request.content,
            category=request.category.value if request.category else None,
            importance_score=request.importance_score,
            metadata=request.metadata or {}
        )
        
        memory_id = await manager.store_memory(memory)
        
        # Fetch the created memory
        query = "SELECT * FROM memories WHERE id = $1"
        result = await manager._execute_one(query, memory_id)
        
        created_memory = _row_to_memory(result)
        
        # Don't close the shared manager
        
        return created_memory
        
    except Exception as e:
        logger.error(f"Error creating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{memory_id}", response_model=MemoryResponse)
async def update_memory(
    memory_id: str,
    request: MemoryUpdateRequest,
    user_id: str = Query(...)
):
    """Update an existing memory"""
    try:
        manager = await get_memory_manager()
        
        # Build update query dynamically
        update_parts = []
        params = []
        param_count = 0
        
        if request.content is not None:
            param_count += 1
            update_parts.append(f"content = ${param_count}")
            params.append(request.content)
        
        if request.category is not None:
            param_count += 1
            update_parts.append(f"category = ${param_count}")
            params.append(request.category.value)
        
        if request.importance_score is not None:
            param_count += 1
            update_parts.append(f"importance_score = ${param_count}")
            params.append(request.importance_score)
        
        if request.metadata is not None:
            param_count += 1
            update_parts.append(f"metadata = ${param_count}")
            params.append(json.dumps(request.metadata))
        
        if not update_parts:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        param_count += 1
        params.append(memory_id)
        param_count += 1
        params.append(user_id)
        
        query = f"""
        UPDATE memories 
        SET {', '.join(update_parts)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ${param_count - 1} AND user_id = ${param_count}
        RETURNING *
        """
        
        result = await manager._execute_one(query, *params)
        
        if not result:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        updated_memory = _row_to_memory(result)
        
        # Don't close the shared manager
        
        return updated_memory
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, user_id: str = Query(None)):
    """Delete a memory"""
    try:
        # Handle case where user_id might not be provided or be 'undefined'
        if not user_id or user_id == 'undefined' or user_id == 'null':
            user_id = "1"  # Default to user ID 1
            logger.warning(f"No valid user_id provided for deletion, using default: {user_id}")
        
        manager = await get_memory_manager()
        
        # Log the deletion attempt
        logger.info(f"Attempting to delete memory {memory_id} for user {user_id}")
        
        success = await manager.delete_memory(memory_id, user_id)
        
        if not success:
            logger.warning(f"Memory {memory_id} not found for user {user_id}")
            # Try without user_id constraint as fallback
            query = "DELETE FROM memories WHERE id = $1"
            result = await manager._execute_command(query, memory_id)
            if result and "DELETE" in str(result):
                logger.info(f"Deleted memory {memory_id} without user constraint")
                return {"success": True, "message": "Memory deleted successfully"}
            raise HTTPException(status_code=404, detail="Memory not found")
        
        # Don't close the shared manager
        
        return {"success": True, "message": "Memory deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Bulk Operations ====================

@router.post("/bulk/{user_id}")
async def bulk_memory_operation(
    user_id: str,
    request: MemoryBulkOperation
):
    """Perform bulk operations on memories"""
    try:
        manager = await get_memory_manager()
        
        if request.operation == "delete":
            # IDs are already strings (UUIDs), no conversion needed
            if not request.memory_ids:
                return {
                    "success": False,
                    "operation": "delete",
                    "affected_count": 0,
                    "error": "No memory IDs provided"
                }
            
            # Bulk delete
            delete_query = """
            DELETE FROM memories 
            WHERE id = ANY($1) AND user_id = $2
            """
            result = await manager._execute_command(
                delete_query, 
                request.memory_ids,  # Use string array directly (UUIDs)
                user_id
            )
            
            deleted_count = int(result.split()[-1]) if result else 0
            
            # Don't close the shared manager
            
            return {
                "success": True,
                "operation": "delete",
                "affected_count": deleted_count
            }
            
        elif request.operation == "update" and request.updates:
            # Bulk update
            # Similar to single update but for multiple IDs
            # Implementation would be similar to update_memory but with ANY($1)
            pass
            
        elif request.operation == "export":
            # Export memories
            export_query = """
            SELECT * FROM memories 
            WHERE id = ANY($1) AND user_id = $2 AND status = 'active'
            """
            results = await manager._execute_query(
                export_query,
                request.memory_ids,
                user_id
            )
            
            memories = [_row_to_memory(row) for row in results]
            
            # Don't close the shared manager
            
            return {
                "success": True,
                "operation": "export",
                "memories": memories
            }
            
    except Exception as e:
        logger.error(f"Error in bulk operation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Search Endpoints ====================

@router.post("/search/{user_id}", response_model=List[MemoryResponse])
async def search_memories(
    user_id: str,
    request: MemorySearchRequest
):
    """Search memories using semantic similarity"""
    try:
        manager = await get_memory_manager()
        
        search_results = await manager.search_memories(
            user_id=user_id,
            query=request.query,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )
        
        memories = []
        for result in search_results:
            memory_dict = _memory_to_dict(result.memory)
            memory_dict['similarity_score'] = result.similarity_score
            memories.append(MemoryResponse(**memory_dict))
        
        # Don't close the shared manager
        
        return memories
        
    except Exception as e:
        logger.error(f"Error searching memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Export/Import Endpoints ====================

@router.get("/export/{user_id}")
async def export_memories(
    user_id: str,
    format: str = Query("json", pattern="^(json|csv)$")
):
    """Export user memories"""
    try:
        manager = await get_memory_manager()
        
        query = """
        SELECT * FROM memories 
        WHERE user_id = $1 AND status = 'active'
        ORDER BY created_at DESC
        """
        results = await manager._execute_query(query, user_id)
        
        # Don't close the shared manager
        
        if format == "json":
            # Export as JSON
            memories = [_row_to_dict(row) for row in results]
            content = json.dumps(memories, indent=2, default=str)
            
            return StreamingResponse(
                io.BytesIO(content.encode()),
                media_type="application/json",
                headers={
                    "Content-Disposition": f"attachment; filename=memories_{user_id}.json"
                }
            )
            
        else:  # CSV
            # Export as CSV
            output = io.StringIO()
            
            if results:
                fieldnames = ['id', 'content', 'category', 'importance_score', 
                            'access_count', 'created_at', 'updated_at']
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                
                for row in results:
                    writer.writerow({
                        'id': row['id'],
                        'content': row['content'],
                        'category': row['category'],
                        'importance_score': row['importance_score'],
                        'access_count': row['access_count'],
                        'created_at': row['created_at'],
                        'updated_at': row['updated_at']
                    })
            
            content = output.getvalue()
            
            return StreamingResponse(
                io.BytesIO(content.encode()),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=memories_{user_id}.csv"
                }
            )
            
    except Exception as e:
        logger.error(f"Error exporting memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import/{user_id}")
async def import_memories(
    user_id: str,
    file: UploadFile = File(...)
):
    """Import memories from file"""
    try:
        from app.memory.postgres_memory_manager import Memory
        
        manager = await get_memory_manager()
        
        content = await file.read()
        
        if file.filename.endswith('.json'):
            # Import from JSON
            memories_data = json.loads(content)
            
            imported_count = 0
            for memory_data in memories_data:
                memory = Memory(
                    user_id=user_id,
                    content=memory_data.get('content', ''),
                    category=memory_data.get('category'),
                    importance_score=memory_data.get('importance_score', 1.0),
                    metadata=memory_data.get('metadata', {})
                )
                
                await manager.store_memory(memory)
                imported_count += 1
            
        elif file.filename.endswith('.csv'):
            # Import from CSV
            import csv
            
            text_content = content.decode('utf-8')
            reader = csv.DictReader(io.StringIO(text_content))
            
            imported_count = 0
            for row in reader:
                memory = Memory(
                    user_id=user_id,
                    content=row.get('content', ''),
                    category=row.get('category'),
                    importance_score=float(row.get('importance_score', 1.0)),
                    metadata={}
                )
                
                await manager.store_memory(memory)
                imported_count += 1
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        # Don't close the shared manager
        
        return {
            "success": True,
            "imported_count": imported_count,
            "message": f"Successfully imported {imported_count} memories"
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Error importing memories: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== Helper Functions ====================

def _row_to_memory(row) -> MemoryResponse:
    """Convert database row to MemoryResponse"""
    return MemoryResponse(
        id=row['id'],
        user_id=row['user_id'],
        content=row['content'],
        category=row['category'],
        importance_score=float(row['importance_score']),
        access_count=row['access_count'] or 0,
        metadata=json.loads(row['metadata']) if row['metadata'] else {},
        created_at=row['created_at'],
        updated_at=row['updated_at'],
        last_accessed_at=row.get('last_accessed_at')  # Handle None gracefully
    )

def _memory_to_dict(memory) -> dict:
    """Convert Memory object to dictionary"""
    return {
        "id": str(memory.id) if memory.id else None,
        "user_id": memory.user_id,
        "content": memory.content,
        "category": getattr(memory, 'category', None),
        "importance_score": getattr(memory, 'importance_score', 1.0),
        "access_count": getattr(memory, 'access_count', 0),
        "metadata": getattr(memory, 'metadata', {}) or {},
        "created_at": getattr(memory, 'created_at', None),
        "updated_at": getattr(memory, 'updated_at', None),
        "last_accessed_at": getattr(memory, 'last_accessed_at', None)
    }

def _row_to_dict(row) -> dict:
    """Convert database row to dictionary"""
    return {
        "id": row['id'],
        "user_id": row['user_id'],
        "content": row['content'],
        "category": row['category'],
        "importance_score": float(row['importance_score']),
        "access_count": row['access_count'],
        "metadata": json.loads(row['metadata']) if row['metadata'] else {},
        "created_at": row['created_at'].isoformat() if row['created_at'] else None,
        "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
        "last_accessed_at": row['last_accessed_at'].isoformat() if row['last_accessed_at'] else None
    }