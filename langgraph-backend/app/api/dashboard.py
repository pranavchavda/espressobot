from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.session import get_db
from app.database.models import Conversation, Message, User
from app.services.dashboard_analytics import get_dashboard_analytics_service
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics"""
    
    total_users = await db.execute(select(func.count(User.id)))
    total_conversations = await db.execute(select(func.count(Conversation.id)))
    total_messages = await db.execute(select(func.count(Message.id)))
    
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    
    today_conversations = await db.execute(
        select(func.count(Conversation.id))
        .where(Conversation.created_at >= today_start)
    )
    
    return {
        "total_users": total_users.scalar(),
        "total_conversations": total_conversations.scalar(),
        "total_messages": total_messages.scalar(),
        "today_conversations": today_conversations.scalar()
    }

@router.get("/activity")
async def get_activity(
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """Get activity data for the last N days"""
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    result = await db.execute(
        select(
            func.date(Message.created_at).label("date"),
            func.count(Message.id).label("count")
        )
        .where(Message.created_at >= start_date)
        .group_by(func.date(Message.created_at))
        .order_by(func.date(Message.created_at))
    )
    
    activity = result.all()
    
    return {
        "dates": [str(row.date) for row in activity],
        "message_counts": [row.count for row in activity]
    }


@router.get("/analytics")
async def get_dashboard_analytics(
    start_date: Optional[str] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[str] = Query(None, description="End date in YYYY-MM-DD format"),
    user_id: int = Query(1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch dashboard analytics data directly for dashboard UI
    Provides Shopify, GA4, and Google Workspace data
    """
    try:
        analytics_service = get_dashboard_analytics_service()
        
        dashboard_data = await analytics_service.get_dashboard_analytics(
            db=db,
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info("[Dashboard Analytics] Successfully compiled dashboard data")
        return dashboard_data
        
    except Exception as error:
        logger.error(f"[Dashboard Analytics] Error: {error}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to fetch analytics data",
                "message": str(error),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


@router.get("/summary")
async def get_dashboard_summary(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    user_id: int = Query(1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Provide a conversational summary of analytics data for agents
    """
    try:
        analytics_service = get_dashboard_analytics_service()
        
        summary = await analytics_service.get_dashboard_summary(
            db=db,
            user_id=user_id,
            date=date
        )
        
        logger.info("[Dashboard Summary] Successfully generated conversational summary")
        return summary
        
    except Exception as error:
        logger.error(f"[Dashboard Summary] Error: {error}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to generate analytics summary",
                "message": str(error),
                "timestamp": datetime.utcnow().isoformat()
            }
        )