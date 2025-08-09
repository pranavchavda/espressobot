"""
Price Monitor Dashboard Service

Provides dashboard statistics, overview data, and summary analytics
for the price monitoring system.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from app.database import (
    IdcProduct, CompetitorProduct, ProductMatch, Competitor, 
    MonitoredBrand, PriceAlert, ViolationHistory
)
from app.database.session import AsyncSessionLocal
import logging

logger = logging.getLogger(__name__)

class PriceMonitorDashboard:
    """Service for price monitor dashboard operations"""
    
    def __init__(self):
        self.session_local = AsyncSessionLocal
    
    async def get_overview(self) -> Dict:
        """Get simple overview statistics for dashboard"""
        async with self.session_local() as session:
            try:
                # Get basic counts in parallel
                total_idc_products = await session.scalar(
                    select(func.count(IdcProduct.id))
                )
                
                total_competitor_products = await session.scalar(
                    select(func.count(CompetitorProduct.id))
                )
                
                total_matches = await session.scalar(
                    select(func.count(ProductMatch.id))
                )
                
                active_violations = await session.scalar(
                    select(func.count(PriceAlert.id)).where(
                        ~PriceAlert.status.in_(['resolved', 'dismissed'])
                    )
                )
                
                # Generate recent activity
                recent_activity = [
                    {
                        'title': 'Product Sync',
                        'description': f'{total_idc_products} products synced from Shopify',
                        'created_at': datetime.utcnow().isoformat()
                    },
                    {
                        'title': 'Product Matching',
                        'description': f'{total_matches} product matches found',
                        'created_at': datetime.utcnow().isoformat()
                    },
                    {
                        'title': 'Competitor Data',
                        'description': f'{total_competitor_products} competitor products tracked',
                        'created_at': datetime.utcnow().isoformat()
                    }
                ]
                
                return {
                    'total_idc_products': total_idc_products or 0,
                    'total_competitor_products': total_competitor_products or 0,
                    'total_matches': total_matches or 0,
                    'active_violations': active_violations or 0,
                    'recent_activity': recent_activity
                }
                
            except Exception as e:
                logger.error(f"Error fetching dashboard overview: {e}")
                raise
    
    async def get_stats(self) -> Dict:
        """Get comprehensive dashboard statistics"""
        async with self.session_local() as session:
            try:
                # Get basic counts
                total_matches = await session.scalar(select(func.count(ProductMatch.id)))
                
                active_violations = await session.scalar(
                    select(func.count(PriceAlert.id)).where(
                        ~PriceAlert.status.in_(['resolved', 'dismissed'])
                    )
                )
                
                total_competitors = await session.scalar(
                    select(func.count(Competitor.id)).where(Competitor.is_active == True)
                )
                
                total_idc_products = await session.scalar(select(func.count(IdcProduct.id)))
                
                total_competitor_products = await session.scalar(
                    select(func.count(CompetitorProduct.id))
                )
                
                active_brands = await session.scalar(
                    select(func.count(MonitoredBrand.id)).where(MonitoredBrand.is_active == True)
                )
                
                # Calculate revenue at risk from MAP violations
                revenue_at_risk_result = await session.execute(
                    select(func.sum(func.abs(PriceAlert.price_change))).where(
                        ~PriceAlert.status.in_(['resolved', 'dismissed'])
                    )
                )
                revenue_at_risk = revenue_at_risk_result.scalar() or 0
                
                # Find worst offender (competitor with most violations)
                worst_offender = await self._get_worst_offender(session)
                
                # Get competitor status
                competitor_status = await self._get_competitor_status(session)
                
                # Get recent alerts
                recent_alerts = await self._get_recent_alerts(session)
                
                stats = {
                    'products_monitored': total_matches or 0,
                    'idc_products': total_idc_products or 0,
                    'competitor_products': total_competitor_products or 0,
                    'active_brands': active_brands or 0,
                    'active_alerts': active_violations or 0,
                    'competitors_tracked': total_competitors or 0,
                    'map_violations': active_violations or 0,
                    'revenue_at_risk': float(revenue_at_risk),
                    'worst_offender': worst_offender
                }
                
                return {
                    'stats': stats,
                    'competitor_status': competitor_status,
                    'recent_alerts': recent_alerts
                }
                
            except Exception as e:
                logger.error(f"Error fetching dashboard stats: {e}")
                raise
    
    async def get_summary(self, period: str = '7d') -> Dict:
        """Get summary statistics for charts/graphs"""
        async with self.session_local() as session:
            try:
                # Calculate date range based on period
                now = datetime.utcnow()
                if period == '24h':
                    start_date = now - timedelta(hours=24)
                elif period == '30d':
                    start_date = now - timedelta(days=30)
                else:  # Default to 7d
                    start_date = now - timedelta(days=7)
                
                # Get violations over time
                violations_result = await session.execute(
                    select(
                        PriceAlert.created_at,
                        PriceAlert.severity,
                        PriceAlert.price_change
                    ).where(
                        and_(
                            PriceAlert.created_at >= start_date,
                            ~PriceAlert.status.in_(['resolved', 'dismissed'])
                        )
                    ).order_by(PriceAlert.created_at.asc())
                )
                
                violations_over_time = [
                    {
                        'created_at': row.created_at.isoformat() if row.created_at else None,
                        'severity': row.severity,
                        'price_change': float(row.price_change) if row.price_change else 0
                    }
                    for row in violations_result
                ]
                
                # Get competitor performance
                competitor_performance = await self._get_competitor_performance(session, start_date)
                
                return {
                    'period': period,
                    'violations_over_time': violations_over_time,
                    'competitor_performance': competitor_performance
                }
                
            except Exception as e:
                logger.error(f"Error fetching dashboard summary: {e}")
                raise
    
    async def _get_worst_offender(self, session: AsyncSession) -> Optional[Dict]:
        """Get the competitor with the most violations"""
        try:
            # Get violations with competitor data
            violations_result = await session.execute(
                select(
                    Competitor.id,
                    Competitor.name,
                    Competitor.domain,
                    PriceAlert.price_change
                ).select_from(
                    PriceAlert
                    .join(ProductMatch, PriceAlert.product_match_id == ProductMatch.id)
                    .join(CompetitorProduct, ProductMatch.competitor_product_id == CompetitorProduct.id)
                    .join(Competitor, CompetitorProduct.competitor_id == Competitor.id)
                ).where(
                    ~PriceAlert.status.in_(['resolved', 'dismissed'])
                )
            )
            
            # Group by competitor to find worst offender
            competitor_violations = {}
            for row in violations_result:
                if row.id not in competitor_violations:
                    competitor_violations[row.id] = {
                        'name': row.name,
                        'domain': row.domain,
                        'violations': 0,
                        'violation_amount': 0
                    }
                competitor_violations[row.id]['violations'] += 1
                competitor_violations[row.id]['violation_amount'] += abs(float(row.price_change or 0))
            
            if competitor_violations:
                # Sort by violation count and return the worst offender
                worst = max(competitor_violations.values(), key=lambda x: x['violations'])
                return worst
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting worst offender: {e}")
            return None
    
    async def _get_competitor_status(self, session: AsyncSession) -> List[Dict]:
        """Get status information for all active competitors"""
        try:
            competitors_result = await session.execute(
                select(
                    Competitor.name,
                    Competitor.domain,
                    Competitor.last_scraped_at,
                    func.count(CompetitorProduct.id).label('product_count')
                ).select_from(
                    Competitor
                    .outerjoin(CompetitorProduct)
                ).where(
                    Competitor.is_active == True
                ).group_by(
                    Competitor.id, Competitor.name, Competitor.domain, Competitor.last_scraped_at
                )
            )
            
            competitor_status = []
            for row in competitors_result:
                last_updated = 'Never'
                if row.last_scraped_at:
                    last_updated = self._get_time_ago(row.last_scraped_at)
                
                competitor_status.append({
                    'name': row.name,
                    'domain': row.domain,
                    'status': 'Active',
                    'last_updated': last_updated,
                    'products_tracked': row.product_count,
                    'avg_price_difference': 0  # TODO: Calculate from matches
                })
            
            return competitor_status
            
        except Exception as e:
            logger.error(f"Error getting competitor status: {e}")
            return []
    
    async def _get_recent_alerts(self, session: AsyncSession) -> List[Dict]:
        """Get recent price alerts/violations"""
        try:
            alerts_result = await session.execute(
                select(
                    PriceAlert.id,
                    PriceAlert.alert_type,
                    PriceAlert.severity,
                    PriceAlert.old_price,
                    PriceAlert.new_price,
                    PriceAlert.price_change,
                    PriceAlert.created_at,
                    CompetitorProduct.title,
                    Competitor.name.label('competitor_name')
                ).select_from(
                    PriceAlert
                    .join(ProductMatch, PriceAlert.product_match_id == ProductMatch.id)
                    .join(CompetitorProduct, ProductMatch.competitor_product_id == CompetitorProduct.id)
                    .join(Competitor, CompetitorProduct.competitor_id == Competitor.id)
                ).where(
                    ~PriceAlert.status.in_(['resolved', 'dismissed'])
                ).order_by(desc(PriceAlert.created_at))
            )
            
            recent_alerts = []
            for row in alerts_result:
                recent_alerts.append({
                    'id': row.id,
                    'product_title': row.title or 'Unknown Product',
                    'competitor': row.competitor_name or 'Unknown Competitor',
                    'alert_type': row.alert_type or 'map_violation',
                    'severity': row.severity,
                    'map_price': float(row.old_price or 0),
                    'competitor_price': float(row.new_price or 0),
                    'price_difference': abs(float(row.price_change or 0)),
                    'created_at': row.created_at
                })
            
            return recent_alerts
            
        except Exception as e:
            logger.error(f"Error getting recent alerts: {e}")
            return []
    
    async def _get_competitor_performance(self, session: AsyncSession, start_date: datetime) -> List[Dict]:
        """Get competitor performance data for the specified period"""
        try:
            performance_result = await session.execute(
                select(
                    Competitor.id,
                    Competitor.name,
                    Competitor.domain,
                    PriceAlert.price_change
                ).select_from(
                    PriceAlert
                    .join(ProductMatch, PriceAlert.product_match_id == ProductMatch.id)
                    .join(CompetitorProduct, ProductMatch.competitor_product_id == CompetitorProduct.id)
                    .join(Competitor, CompetitorProduct.competitor_id == Competitor.id)
                ).where(
                    and_(
                        PriceAlert.created_at >= start_date,
                        ~PriceAlert.status.in_(['resolved', 'dismissed'])
                    )
                )
            )
            
            # Process competitor performance data
            competitor_performance = {}
            for row in performance_result:
                if row.id not in competitor_performance:
                    competitor_performance[row.id] = {
                        'competitor_name': row.name,
                        'competitor_domain': row.domain,
                        'violation_count': 0,
                        'total_violation_amount': 0
                    }
                competitor_performance[row.id]['violation_count'] += 1
                competitor_performance[row.id]['total_violation_amount'] += abs(float(row.price_change or 0))
            
            # Sort by violation count descending
            sorted_performance = sorted(
                competitor_performance.values(),
                key=lambda x: x['violation_count'],
                reverse=True
            )
            
            return sorted_performance
            
        except Exception as e:
            logger.error(f"Error getting competitor performance: {e}")
            return []
    
    def _get_time_ago(self, date: datetime) -> str:
        """Calculate human-readable time ago string"""
        now = datetime.utcnow()
        diff = now - date
        
        total_minutes = int(diff.total_seconds() / 60)
        total_hours = int(diff.total_seconds() / 3600)
        total_days = diff.days
        
        if total_minutes < 60:
            return f"{total_minutes}m ago"
        elif total_hours < 24:
            return f"{total_hours}h ago"
        else:
            return f"{total_days}d ago"
