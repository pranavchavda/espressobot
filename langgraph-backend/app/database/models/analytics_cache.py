"""
Analytics Cache Models
Store historical analytics data to avoid repeated API calls
"""

from sqlalchemy import Column, Integer, String, JSON, DateTime, Date, Float, Boolean, Index
from sqlalchemy.sql import func
from app.database.base import Base


class DailyAnalyticsCache(Base):
    """Cache daily analytics data from multiple sources"""
    
    __tablename__ = "daily_analytics_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True, index=True)
    
    # Shopify data
    shopify_revenue = Column(Float)
    shopify_orders = Column(Integer)
    shopify_aov = Column(Float)
    shopify_top_products = Column(JSON)  # Store top 10 products as JSON
    shopify_raw_data = Column(JSON)  # Full raw response for future needs
    
    # GA4 data
    ga4_revenue = Column(Float)
    ga4_transactions = Column(Integer)
    ga4_users = Column(Integer)
    ga4_conversion_rate = Column(Float)
    ga4_traffic_sources = Column(JSON)
    ga4_ads_performance = Column(JSON)
    ga4_raw_data = Column(JSON)
    
    # Google Workspace data (optional, as it changes frequently)
    workspace_data = Column(JSON, nullable=True)
    
    # Metadata
    is_complete = Column(Boolean, default=False)  # Whether all data sources succeeded
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Create composite index for efficient queries
    __table_args__ = (
        Index('idx_date_complete', 'date', 'is_complete'),
    )


class HourlyAnalyticsCache(Base):
    """Cache hourly analytics for today's data"""
    
    __tablename__ = "hourly_analytics_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer, nullable=False)  # 0-23
    
    # Hourly metrics
    revenue = Column(Float)
    orders = Column(Integer)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Composite unique constraint
    __table_args__ = (
        Index('idx_date_hour', 'date', 'hour', unique=True),
    )


class AnalyticsSyncStatus(Base):
    """Track sync status for bulk data fetching"""
    
    __tablename__ = "analytics_sync_status"
    
    id = Column(Integer, primary_key=True, index=True)
    sync_type = Column(String(50), nullable=False)  # 'daily', 'monthly', 'yearly'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Status tracking
    status = Column(String(20), default='pending')  # pending, in_progress, completed, failed
    total_days = Column(Integer)
    processed_days = Column(Integer, default=0)
    failed_days = Column(Integer, default=0)
    
    # Timing
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Error tracking
    last_error = Column(String(500))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())