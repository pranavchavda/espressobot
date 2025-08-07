from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database.session import get_db
from app.database.models import Conversation, Message, User
from datetime import datetime, timedelta
from typing import Dict, Any

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