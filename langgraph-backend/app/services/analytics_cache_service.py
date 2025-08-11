"""
Analytics Cache Service
Manages caching and retrieval of historical analytics data
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.dialects.postgresql import insert

from app.database.models import (
    DailyAnalyticsCache,
    HourlyAnalyticsCache,
    AnalyticsSyncStatus
)

logger = logging.getLogger(__name__)


class AnalyticsCacheService:
    """Service for managing analytics data cache"""
    
    async def get_cached_analytics(
        self,
        db: AsyncSession,
        target_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached analytics for a specific date
        Returns None if not cached or if date is today
        """
        # Don't use cache for today's data
        today = date.today()
        query_date = datetime.strptime(target_date, '%Y-%m-%d').date()
        
        if query_date >= today:
            logger.info(f"[Cache] Skipping cache for today/future date: {target_date}")
            return None
        
        # Query cache
        result = await db.execute(
            select(DailyAnalyticsCache).where(
                and_(
                    DailyAnalyticsCache.date == query_date,
                    DailyAnalyticsCache.is_complete == True
                )
            )
        )
        cached = result.scalar_one_or_none()
        
        if not cached:
            logger.info(f"[Cache] No cached data found for {target_date}")
            return None
        
        logger.info(f"[Cache] Using cached data for {target_date}")
        
        # Build response from cache
        return {
            'date': target_date,
            'from_cache': True,
            'cached_at': cached.created_at.isoformat(),
            'shopify': {
                'total_revenue': str(cached.shopify_revenue or 0),
                'order_count': cached.shopify_orders or 0,
                'average_order_value': str(cached.shopify_aov or 0),
                'top_products': cached.shopify_top_products or [],
                'raw_response': cached.shopify_raw_data
            },
            'ga4': {
                'ecommerce': {
                    'revenue': str(cached.ga4_revenue or 0),
                    'transactions': cached.ga4_transactions or 0,
                    'aov': str(cached.ga4_revenue / cached.ga4_transactions if cached.ga4_transactions else 0),
                    'conversion_rate': f"{cached.ga4_conversion_rate or 0}%",
                    'users': cached.ga4_users or 0
                },
                'traffic_sources': cached.ga4_traffic_sources or [],
                'ads_performance': cached.ga4_ads_performance or {}
            },
            'workspace': cached.workspace_data or {}
        }
    
    async def save_analytics_to_cache(
        self,
        db: AsyncSession,
        target_date: str,
        shopify_data: Dict[str, Any],
        ga4_data: Dict[str, Any],
        workspace_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Save analytics data to cache
        Returns True if saved successfully
        """
        try:
            query_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            
            # Don't cache today's data
            if query_date >= date.today():
                logger.info(f"[Cache] Not caching today/future date: {target_date}")
                return False
            
            # Prepare cache data
            cache_data = {
                'date': query_date,
                'shopify_revenue': float(shopify_data.get('total_revenue', 0)),
                'shopify_orders': shopify_data.get('order_count', 0),
                'shopify_aov': float(shopify_data.get('average_order_value', 0)),
                'shopify_top_products': shopify_data.get('top_products', []),
                'shopify_raw_data': shopify_data.get('raw_response'),
                'ga4_revenue': float(ga4_data.get('ecommerce', {}).get('revenue', 0)),
                'ga4_transactions': ga4_data.get('ecommerce', {}).get('transactions', 0),
                'ga4_users': ga4_data.get('ecommerce', {}).get('users', 0),
                'ga4_conversion_rate': float(ga4_data.get('ecommerce', {}).get('conversion_rate', '0').replace('%', '')),
                'ga4_traffic_sources': ga4_data.get('traffic_sources', []),
                'ga4_ads_performance': ga4_data.get('ads_performance', {}),
                'ga4_raw_data': ga4_data,
                'workspace_data': workspace_data,
                'is_complete': True
            }
            
            # Upsert the cache entry
            stmt = insert(DailyAnalyticsCache).values(**cache_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=['date'],
                set_=cache_data
            )
            
            await db.execute(stmt)
            await db.commit()
            
            logger.info(f"[Cache] Successfully cached analytics for {target_date}")
            return True
            
        except Exception as e:
            logger.error(f"[Cache] Failed to save cache for {target_date}: {e}")
            await db.rollback()
            return False
    
    async def bulk_fetch_historical_data(
        self,
        db: AsyncSession,
        start_date: str,
        end_date: str,
        fetch_function,  # Async function to fetch data for a date
        batch_size: int = 10
    ) -> Dict[str, Any]:
        """
        Bulk fetch historical data for a date range
        """
        # Create sync status record
        sync_status = AnalyticsSyncStatus(
            sync_type='daily',
            start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
            end_date=datetime.strptime(end_date, '%Y-%m-%d').date(),
            status='in_progress',
            started_at=datetime.utcnow()
        )
        
        # Calculate total days
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        total_days = (end - start).days + 1
        sync_status.total_days = total_days
        
        db.add(sync_status)
        await db.commit()
        
        # Process dates in batches
        success_count = 0
        fail_count = 0
        current_date = start
        
        while current_date <= end:
            try:
                # Check if already cached
                existing = await db.execute(
                    select(DailyAnalyticsCache).where(
                        and_(
                            DailyAnalyticsCache.date == current_date.date(),
                            DailyAnalyticsCache.is_complete == True
                        )
                    )
                )
                
                if not existing.scalar_one_or_none():
                    # Fetch and cache the data
                    date_str = current_date.strftime('%Y-%m-%d')
                    logger.info(f"[Bulk Cache] Fetching data for {date_str}")
                    
                    data = await fetch_function(date_str)
                    
                    if data:
                        await self.save_analytics_to_cache(
                            db,
                            date_str,
                            data.get('shopify', {}),
                            data.get('ga4', {}),
                            data.get('workspace')
                        )
                        success_count += 1
                    else:
                        fail_count += 1
                else:
                    logger.info(f"[Bulk Cache] Skipping {current_date.strftime('%Y-%m-%d')} - already cached")
                    success_count += 1
                
                # Update progress
                sync_status.processed_days = success_count + fail_count
                sync_status.failed_days = fail_count
                await db.commit()
                
            except Exception as e:
                logger.error(f"[Bulk Cache] Error processing {current_date}: {e}")
                fail_count += 1
                sync_status.last_error = str(e)[:500]
            
            current_date += timedelta(days=1)
        
        # Mark sync as complete
        sync_status.status = 'completed' if fail_count == 0 else 'partial'
        sync_status.completed_at = datetime.utcnow()
        await db.commit()
        
        return {
            'total_days': total_days,
            'success_count': success_count,
            'fail_count': fail_count,
            'status': sync_status.status
        }
    
    async def get_cache_statistics(self, db: AsyncSession) -> Dict[str, Any]:
        """Get statistics about cached data"""
        
        # Count total cached days
        total_result = await db.execute(
            select(DailyAnalyticsCache).where(
                DailyAnalyticsCache.is_complete == True
            )
        )
        total_cached = len(total_result.scalars().all())
        
        # Get date range
        range_result = await db.execute(
            select(
                DailyAnalyticsCache.date
            ).where(
                DailyAnalyticsCache.is_complete == True
            ).order_by(
                DailyAnalyticsCache.date
            )
        )
        dates = [r.date for r in range_result]
        
        # Get recent sync status
        sync_result = await db.execute(
            select(AnalyticsSyncStatus).order_by(
                desc(AnalyticsSyncStatus.created_at)
            ).limit(5)
        )
        recent_syncs = sync_result.scalars().all()
        
        return {
            'total_cached_days': total_cached,
            'oldest_date': dates[0].isoformat() if dates else None,
            'newest_date': dates[-1].isoformat() if dates else None,
            'recent_syncs': [
                {
                    'type': s.sync_type,
                    'start_date': s.start_date.isoformat(),
                    'end_date': s.end_date.isoformat(),
                    'status': s.status,
                    'processed': s.processed_days,
                    'failed': s.failed_days
                }
                for s in recent_syncs
            ]
        }


# Singleton instance
_cache_service: Optional[AnalyticsCacheService] = None

def get_cache_service() -> AnalyticsCacheService:
    """Get or create the cache service singleton"""
    global _cache_service
    if _cache_service is None:
        _cache_service = AnalyticsCacheService()
    return _cache_service