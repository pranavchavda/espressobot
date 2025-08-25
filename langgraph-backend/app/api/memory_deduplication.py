"""
Memory Deduplication API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import logging

from app.memory.memory_deduplication import get_deduplication_service, DuplicateGroup

logger = logging.getLogger(__name__)
router = APIRouter()

class DeduplicationRequest(BaseModel):
    user_id: str
    category: Optional[str] = None
    dry_run: bool = True

class DeduplicationResult(BaseModel):
    groups_found: int
    memories_analyzed: int  
    memories_merged: int
    memories_removed: int
    dry_run: bool
    execution_time_ms: float

class DuplicateGroupInfo(BaseModel):
    primary_memory_id: str
    primary_content: str
    primary_importance: float
    duplicate_count: int
    duplicate_ids: List[str]
    duplicate_contents: List[str]
    similarity_scores: List[float]
    merged_content: str

@router.post("/deduplicate", response_model=DeduplicationResult)
async def deduplicate_memories(request: DeduplicationRequest):
    """
    Deduplicate memories for a user
    """
    try:
        import time
        start_time = time.time()
        
        deduplication_service = get_deduplication_service()
        
        # Run deduplication
        stats = await deduplication_service.deduplicate_memories(
            user_id=request.user_id,
            category=request.category,
            dry_run=request.dry_run
        )
        
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        
        result = DeduplicationResult(
            **stats,
            execution_time_ms=execution_time
        )
        
        logger.info(f"Deduplication {'(dry run)' if request.dry_run else ''} completed for user {request.user_id}: {stats}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in deduplication: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview/{user_id}", response_model=List[DuplicateGroupInfo])
async def preview_duplicates(
    user_id: str,
    category: Optional[str] = Query(None),
    similarity_threshold: float = Query(0.85, ge=0.1, le=1.0)
):
    """
    Preview duplicate groups without making changes
    """
    try:
        deduplication_service = get_deduplication_service()
        deduplication_service.similarity_threshold = similarity_threshold
        
        duplicate_groups = await deduplication_service.find_duplicate_groups(
            user_id=user_id,
            category=category
        )
        
        # Convert to response format
        preview_groups = []
        for group in duplicate_groups:
            group_info = DuplicateGroupInfo(
                primary_memory_id=group.primary_memory.id,
                primary_content=group.primary_memory.content,
                primary_importance=group.primary_memory.importance_score,
                duplicate_count=len(group.duplicates),
                duplicate_ids=[dup.id for dup in group.duplicates],
                duplicate_contents=[dup.content for dup in group.duplicates],
                similarity_scores=group.similarity_scores,
                merged_content=group.merged_content
            )
            preview_groups.append(group_info)
        
        logger.info(f"Found {len(preview_groups)} duplicate groups for user {user_id}")
        
        return preview_groups
        
    except Exception as e:
        logger.error(f"Error previewing duplicates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{user_id}")
async def get_deduplication_stats(user_id: str):
    """
    Get statistics about potential duplicates
    """
    try:
        deduplication_service = get_deduplication_service()
        
        # Get dry run stats
        stats = await deduplication_service.deduplicate_memories(
            user_id=user_id,
            dry_run=True
        )
        
        # Get category breakdown
        categories = ['facts', 'preferences', 'problems', 'solutions', 'relationships', 'expertise', 'general']
        category_stats = {}
        
        for category in categories:
            cat_stats = await deduplication_service.deduplicate_memories(
                user_id=user_id,
                category=category,
                dry_run=True
            )
            if cat_stats['groups_found'] > 0:
                category_stats[category] = cat_stats
        
        return {
            "overall": stats,
            "by_category": category_stats,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error(f"Error getting deduplication stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/merge-group")
async def merge_duplicate_group(group_data: dict):
    """
    Merge a specific duplicate group
    """
    try:
        deduplication_service = get_deduplication_service()
        
        # Extract group data
        primary_id = group_data.get("primary_memory_id")
        duplicate_ids = group_data.get("duplicate_ids", [])
        merged_content = group_data.get("merged_content")
        
        if not primary_id or not duplicate_ids:
            raise HTTPException(status_code=400, detail="Invalid group data")
        
        # Update primary memory if content changed
        if merged_content:
            await deduplication_service._update_memory_content(primary_id, merged_content)
        
        # Remove duplicates
        removed_count = 0
        for dup_id in duplicate_ids:
            await deduplication_service._remove_memory(dup_id)
            removed_count += 1
        
        return {
            "success": True,
            "primary_updated": bool(merged_content),
            "duplicates_removed": removed_count
        }
        
    except Exception as e:
        logger.error(f"Error merging duplicate group: {e}")
        raise HTTPException(status_code=500, detail=str(e))