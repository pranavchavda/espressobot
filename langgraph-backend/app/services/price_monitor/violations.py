"""Violations service for price monitoring system.

Provides comprehensive violation tracking functionality including:
- Violation history recording and retrieval
- MAP violation scanning with history recording
- Violation statistics and analytics
- Export capabilities for violation reports
- Violation trend analysis and reporting

Combines functionality from violation-history.js and map-violations.js.
"""

from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc, and_, or_, case, text
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import logging
import csv
import io

from app.database.price_monitor_models import (
    ViolationHistory, ProductMatch, IdcProduct, CompetitorProduct, Competitor,
    PriceAlert
)
from app.database.session import get_db

logger = logging.getLogger(__name__)


class MAPViolationDetector:
    """MAP violation detection engine."""
    
    def __init__(self):
        self.violation_thresholds = {
            'minor': 0.01,    # 1% below MAP
            'moderate': 0.10, # 10% below MAP
            'severe': 0.20    # 20% below MAP
        }
    
    def calculate_violation_severity(self, map_price: float, competitor_price: float) -> Optional[str]:
        """Calculate violation severity based on price difference.
        
        Args:
            map_price: MAP price from iDC product
            competitor_price: Competitor's selling price
            
        Returns:
            Severity level ('minor', 'moderate', 'severe') or None if no violation
        """
        if not map_price or not competitor_price or map_price <= 0 or competitor_price <= 0:
            return None
        
        price_difference = map_price - competitor_price
        violation_percentage = price_difference / map_price
        
        if violation_percentage <= 0:
            return None  # No violation - competitor price is at or above MAP
        
        if violation_percentage >= self.violation_thresholds['severe']:
            return 'severe'
        elif violation_percentage >= self.violation_thresholds['moderate']:
            return 'moderate'
        elif violation_percentage >= self.violation_thresholds['minor']:
            return 'minor'
        
        return None  # Below minor threshold
    
    def calculate_financial_impact(
        self,
        map_price: float,
        competitor_price: float,
        estimated_volume: int = 10
    ) -> Dict[str, float]:
        """Calculate financial impact of violation.
        
        Args:
            map_price: MAP price
            competitor_price: Competitor price
            estimated_volume: Estimated sales volume
            
        Returns:
            Dict with financial impact metrics
        """
        price_difference = map_price - competitor_price
        return {
            'price_gap': price_difference,
            'percentage_below': (price_difference / map_price) * 100,
            'potential_lost_revenue': price_difference * estimated_volume,
            'competitor_advantage': competitor_price / map_price
        }


class ViolationsService:
    """Service for managing violation history and MAP violation detection."""
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
        self.detector = MAPViolationDetector()
    
    async def record_violation(
        self,
        db: AsyncSession,
        product_match_id: str,
        violation_type: str,
        competitor_price: Decimal,
        idc_price: Decimal,
        violation_amount: Decimal,
        violation_percent: float,
        previous_price: Optional[Decimal] = None,
        screenshot_url: Optional[str] = None,
        competitor_url: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ViolationHistory:
        """Record a violation in history.
        
        Args:
            db: Database session
            product_match_id: ID of the product match
            violation_type: Type of violation
            competitor_price: Current competitor price
            idc_price: iDC MAP price
            violation_amount: Amount of violation
            violation_percent: Percentage of violation
            previous_price: Previous competitor price
            screenshot_url: URL to screenshot evidence
            competitor_url: URL to competitor product
            notes: Additional notes
            
        Returns:
            Created violation history record
        """
        try:
            violation_record = ViolationHistory(
                id=str(uuid.uuid4()),
                product_match_id=product_match_id,
                violation_type=violation_type,
                competitor_price=competitor_price,
                idc_price=idc_price,
                violation_amount=violation_amount,
                violation_percent=violation_percent,
                previous_price=previous_price,
                price_change=competitor_price - previous_price if previous_price else None,
                screenshot_url=screenshot_url,
                competitor_url=competitor_url,
                notes=notes,
                detected_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(violation_record)
            
            # Update product match with violation tracking
            match_query = select(ProductMatch).where(ProductMatch.id == product_match_id)
            result = await db.execute(match_query)
            product_match = result.scalar_one_or_none()
            
            if product_match:
                # Get first violation date
                first_violation_date = await self._get_first_violation_date(db, product_match_id)
                
                product_match.is_map_violation = True
                product_match.violation_amount = violation_amount
                product_match.violation_percentage = violation_percent
                product_match.first_violation_date = first_violation_date
                product_match.last_checked_at = datetime.utcnow()
            
            await db.commit()
            return violation_record
            
        except Exception as e:
            await db.rollback()
            self.logger.error(f'Error recording violation: {e}')
            raise
    
    async def _get_first_violation_date(self, db: AsyncSession, product_match_id: str) -> datetime:
        """Get first violation date for a product match."""
        query = select(ViolationHistory.detected_at).where(
            ViolationHistory.product_match_id == product_match_id
        ).order_by(asc(ViolationHistory.detected_at)).limit(1)
        
        result = await db.execute(query)
        first_date = result.scalar()
        
        return first_date or datetime.utcnow()
    
    async def scan_and_record_violations(
        self,
        db: AsyncSession,
        brands: Optional[List[str]] = None,
        severity_filter: Optional[str] = None,
        record_history: bool = True,
        capture_screenshots: bool = False,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Enhanced MAP violation scanner that records history.
        
        Args:
            db: Database session
            brands: List of brands to scan
            severity_filter: Filter by severity level
            record_history: Whether to record violation history
            capture_screenshots: Whether to capture screenshots
            dry_run: Whether this is a dry run
            
        Returns:
            Dict with scan results
        """
        try:
            self.logger.info('Starting MAP violation scan with history recording')
            
            results = {
                'total_matches_scanned': 0,
                'violations_found': 0,
                'history_recorded': 0,
                'by_severity': {
                    'minor': 0,
                    'moderate': 0,
                    'severe': 0
                },
                'violations': []
            }
            
            # Build query for product matches to scan
            query = select(ProductMatch).options(
                selectinload(ProductMatch.idc_product),
                selectinload(ProductMatch.competitor_product).options(
                    selectinload(CompetitorProduct.competitor)
                ),
                selectinload(ProductMatch.violation_history).options(
                    selectinload(ViolationHistory.product_match)
                )
            )
            
            # Filter by brands if specified
            if brands:
                query = query.join(ProductMatch.idc_product).where(
                    IdcProduct.vendor.in_(brands)
                )
            
            result = await db.execute(query)
            product_matches = result.scalars().all()
            
            self.logger.info(f'Scanning {len(product_matches)} product matches for violations')
            
            for match in product_matches:
                if not match.idc_product or not match.competitor_product:
                    continue
                
                idc_product = match.idc_product
                competitor_product = match.competitor_product
                
                map_price = float(idc_product.price) if idc_product.price else None
                competitor_price = float(competitor_product.price) if competitor_product.price else None
                
                # Get last violation from history
                last_violation = None
                if match.violation_history:
                    last_violation = max(match.violation_history, key=lambda v: v.detected_at)
                
                if not map_price or not competitor_price or competitor_price >= map_price:
                    # No violation or invalid prices
                    if match.is_map_violation and competitor_price >= map_price:
                        # Violation resolved - update the match
                        if not dry_run:
                            match.is_map_violation = False
                            match.violation_amount = None
                            match.violation_percentage = None
                            match.last_checked_at = datetime.utcnow()
                    results['total_matches_scanned'] += 1
                    continue
                
                violation_amount = map_price - competitor_price
                violation_percent = (violation_amount / map_price) * 100
                
                # Determine severity
                severity = self.detector.calculate_violation_severity(map_price, competitor_price)
                
                if severity and (not severity_filter or severity == severity_filter):
                    # Check if this is a new violation or price change
                    is_new_violation = not last_violation
                    is_price_change = (
                        last_violation and 
                        float(last_violation.competitor_price) != competitor_price
                    )
                    
                    if (is_new_violation or is_price_change) and record_history and not dry_run:
                        # Record in violation history
                        await self.record_violation(
                            db=db,
                            product_match_id=match.id,
                            violation_type=f'map_violation_{severity}',
                            competitor_price=Decimal(str(competitor_price)),
                            idc_price=Decimal(str(map_price)),
                            violation_amount=Decimal(str(violation_amount)),
                            violation_percent=violation_percent,
                            previous_price=Decimal(str(last_violation.competitor_price)) if last_violation else None,
                            competitor_url=competitor_product.product_url,
                            notes='Initial violation detected' if is_new_violation else 'Price changed'
                        )
                        
                        results['history_recorded'] += 1
                    
                    results['violations_found'] += 1
                    results['by_severity'][severity] += 1
                    
                    results['violations'].append({
                        'match_id': match.id,
                        'is_new': is_new_violation,
                        'price_changed': is_price_change,
                        'idc_product': {
                            'title': idc_product.title,
                            'vendor': idc_product.vendor,
                            'sku': idc_product.sku,
                            'price': map_price
                        },
                        'competitor_product': {
                            'title': competitor_product.title,
                            'vendor': competitor_product.vendor,
                            'sku': competitor_product.sku,
                            'price': competitor_price,
                            'competitor': competitor_product.competitor.name,
                            'domain': competitor_product.competitor.domain,
                            'url': competitor_product.product_url
                        },
                        'violation': {
                            'severity': severity,
                            'amount': violation_amount,
                            'percentage': round(violation_percent, 2),
                            'previous_price': float(last_violation.competitor_price) if last_violation else None,
                            'first_detected': match.first_violation_date or datetime.utcnow(),
                            'last_detected': datetime.utcnow()
                        }
                    })
                
                results['total_matches_scanned'] += 1
            
            self.logger.info(
                f'Scan completed: {results["violations_found"]} violations found, '
                f'{results["history_recorded"]} recorded'
            )
            
            return {
                'message': f'MAP violation scan completed{" (dry run)" if dry_run else ""}',
                **results
            }
            
        except Exception as e:
            self.logger.error(f'Error scanning violations: {e}')
            raise
    
    async def get_violation_history(
        self,
        db: AsyncSession,
        product_match_id: str,
        limit: int = 100,
        offset: int = 0,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get violation history for a product.
        
        Args:
            db: Database session
            product_match_id: Product match ID
            limit: Maximum records to return
            offset: Offset for pagination
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Dict with history and pagination info
        """
        try:
            conditions = [ViolationHistory.product_match_id == product_match_id]
            
            if start_date:
                conditions.append(ViolationHistory.detected_at >= start_date)
            if end_date:
                conditions.append(ViolationHistory.detected_at <= end_date)
            
            # Get history records
            history_query = select(ViolationHistory).options(
                selectinload(ViolationHistory.product_match).options(
                    selectinload(ProductMatch.idc_product),
                    selectinload(ProductMatch.competitor_product).options(
                        selectinload(CompetitorProduct.competitor)
                    )
                )
            ).where(and_(*conditions)).order_by(desc(ViolationHistory.detected_at)).offset(offset).limit(limit)
            
            # Get total count
            count_query = select(func.count(ViolationHistory.id)).where(and_(*conditions))
            
            history_result = await db.execute(history_query)
            count_result = await db.execute(count_query)
            
            history = history_result.scalars().all()
            total = count_result.scalar()
            
            return {
                'history': [
                    {
                        'id': record.id,
                        'violation_type': record.violation_type,
                        'competitor_price': float(record.competitor_price),
                        'idc_price': float(record.idc_price),
                        'violation_amount': float(record.violation_amount),
                        'violation_percent': record.violation_percent,
                        'previous_price': float(record.previous_price) if record.previous_price else None,
                        'price_change': float(record.price_change) if record.price_change else None,
                        'screenshot_url': record.screenshot_url,
                        'competitor_url': record.competitor_url,
                        'notes': record.notes,
                        'detected_at': record.detected_at,
                        'product_match': {
                            'id': record.product_match.id,
                            'idc_product': {
                                'title': record.product_match.idc_product.title,
                                'vendor': record.product_match.idc_product.vendor,
                                'sku': record.product_match.idc_product.sku
                            } if record.product_match.idc_product else None,
                            'competitor_product': {
                                'title': record.product_match.competitor_product.title,
                                'competitor': {
                                    'name': record.product_match.competitor_product.competitor.name,
                                    'domain': record.product_match.competitor_product.competitor.domain
                                }
                            } if record.product_match.competitor_product else None
                        } if record.product_match else None
                    } for record in history
                ],
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total
                }
            }
            
        except Exception as e:
            self.logger.error(f'Error fetching violation history: {e}')
            raise
    
    async def get_violation_statistics(
        self,
        db: AsyncSession,
        brand: Optional[str] = None,
        competitor: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        group_by: str = 'day'
    ) -> Dict[str, Any]:
        """Get aggregated violation statistics.
        
        Args:
            db: Database session
            brand: Brand filter
            competitor: Competitor filter
            start_date: Start date filter
            end_date: End date filter
            group_by: Time grouping ('day', 'week', 'month')
            
        Returns:
            Dict with violation statistics
        """
        try:
            conditions = []
            
            if start_date:
                conditions.append(ViolationHistory.detected_at >= start_date)
            if end_date:
                conditions.append(ViolationHistory.detected_at <= end_date)
            
            base_query = select(ViolationHistory)
            
            # Add joins for brand/competitor filters
            if brand or competitor:
                base_query = base_query.join(ViolationHistory.product_match)
                if brand:
                    base_query = base_query.join(ProductMatch.idc_product).where(
                        IdcProduct.vendor == brand
                    )
                if competitor:
                    base_query = base_query.join(ProductMatch.competitor_product).join(
                        CompetitorProduct.competitor
                    ).where(
                        Competitor.name == competitor
                    )
            
            if conditions:
                base_query = base_query.where(and_(*conditions))
            
            # Get summary statistics - use direct queries to avoid cartesian product
            # Build conditions for direct queries
            stats_conditions = conditions.copy()
            
            # Total violations - direct count
            total_violations_query = select(func.count(ViolationHistory.id))
            if brand or competitor:
                total_violations_query = total_violations_query.select_from(ViolationHistory)
                total_violations_query = total_violations_query.join(ViolationHistory.product_match)
                if brand:
                    total_violations_query = total_violations_query.join(ProductMatch.idc_product).where(
                        IdcProduct.vendor == brand
                    )
                if competitor:
                    total_violations_query = total_violations_query.join(ProductMatch.competitor_product).join(
                        CompetitorProduct.competitor
                    ).where(
                        Competitor.name == competitor
                    )
            else:
                total_violations_query = total_violations_query.select_from(ViolationHistory)
            
            if stats_conditions:
                total_violations_query = total_violations_query.where(and_(*stats_conditions))
            
            # Average and max statistics - direct queries
            avg_violation_query = select(
                func.avg(ViolationHistory.violation_percent),
                func.avg(ViolationHistory.violation_amount)
            ).select_from(ViolationHistory)
            
            max_violation_query = select(
                func.max(ViolationHistory.violation_percent),
                func.max(ViolationHistory.violation_amount)
            ).select_from(ViolationHistory)
            
            # Apply same filters to avg and max queries
            if brand or competitor:
                avg_violation_query = avg_violation_query.join(ViolationHistory.product_match)
                max_violation_query = max_violation_query.join(ViolationHistory.product_match)
                if brand:
                    avg_violation_query = avg_violation_query.join(ProductMatch.idc_product).where(
                        IdcProduct.vendor == brand
                    )
                    max_violation_query = max_violation_query.join(ProductMatch.idc_product).where(
                        IdcProduct.vendor == brand
                    )
                if competitor:
                    avg_violation_query = avg_violation_query.join(ProductMatch.competitor_product).join(
                        CompetitorProduct.competitor
                    ).where(
                        Competitor.name == competitor
                    )
                    max_violation_query = max_violation_query.join(ProductMatch.competitor_product).join(
                        CompetitorProduct.competitor
                    ).where(
                        Competitor.name == competitor
                    )
            
            if stats_conditions:
                avg_violation_query = avg_violation_query.where(and_(*stats_conditions))
                max_violation_query = max_violation_query.where(and_(*stats_conditions))
            
            # Active violations count
            active_violations_query = select(func.count(ProductMatch.id)).where(
                ProductMatch.is_map_violation == True
            )
            
            # Violations by type - direct query to avoid cartesian product
            violations_by_type_query = select(
                ViolationHistory.violation_type,
                func.count(ViolationHistory.id).label('count'),
                func.sum(ViolationHistory.violation_amount).label('total_amount'),
                func.avg(ViolationHistory.violation_percent).label('avg_percent')
            ).select_from(ViolationHistory)
            
            if brand or competitor:
                violations_by_type_query = violations_by_type_query.join(ViolationHistory.product_match)
                if brand:
                    violations_by_type_query = violations_by_type_query.join(ProductMatch.idc_product).where(
                        IdcProduct.vendor == brand
                    )
                if competitor:
                    violations_by_type_query = violations_by_type_query.join(ProductMatch.competitor_product).join(
                        CompetitorProduct.competitor
                    ).where(
                        Competitor.name == competitor
                    )
            
            if stats_conditions:
                violations_by_type_query = violations_by_type_query.where(and_(*stats_conditions))
            
            violations_by_type_query = violations_by_type_query.group_by(ViolationHistory.violation_type)
            
            # Execute queries
            total_result = await db.execute(total_violations_query)
            avg_result = await db.execute(avg_violation_query)
            max_result = await db.execute(max_violation_query)
            active_result = await db.execute(active_violations_query)
            type_result = await db.execute(violations_by_type_query)
            
            total_violations = total_result.scalar() or 0
            avg_data = avg_result.first()
            max_data = max_result.first()
            active_violations = active_result.scalar() or 0
            type_data = type_result.all()
            
            # Get all violations for time series
            violations_query = base_query.order_by(desc(ViolationHistory.detected_at))
            violations_result = await db.execute(violations_query)
            violations = violations_result.scalars().all()
            
            # Group violations by time period
            time_series_map = {}
            
            for violation in violations:
                date = violation.detected_at
                if group_by == 'month':
                    period_key = f'{date.year}-{date.month:02d}'
                elif group_by == 'week':
                    week_start = date - timedelta(days=date.weekday())
                    period_key = week_start.strftime('%Y-%m-%d')
                else:  # day
                    period_key = date.strftime('%Y-%m-%d')
                
                if period_key not in time_series_map:
                    time_series_map[period_key] = {
                        'period': period_key,
                        'violations': [],
                        'unique_products': set()
                    }
                
                time_series_map[period_key]['violations'].append(violation)
                time_series_map[period_key]['unique_products'].add(violation.product_match_id)
            
            # Calculate aggregates for each period
            time_series = []
            for period_key, data in sorted(time_series_map.items(), reverse=True):
                violations_list = data['violations']
                time_series.append({
                    'period': datetime.strptime(period_key + ('-01' if group_by == 'month' else ''), 
                                               '%Y-%m-%d'),
                    'violation_count': len(violations_list),
                    'avg_violation_pct': sum(v.violation_percent for v in violations_list) / len(violations_list) if violations_list else 0,
                    'total_impact': sum(float(v.violation_amount) for v in violations_list if v.violation_amount),
                    'unique_products': len(data['unique_products'])
                })
            
            return {
                'summary': {
                    'total_violations': total_violations,
                    'active_violations': active_violations,
                    'average_violation_percent': float(avg_data[0]) if avg_data[0] else 0,
                    'average_violation_amount': float(avg_data[1]) if avg_data[1] else 0,
                    'max_violation_percent': float(max_data[0]) if max_data[0] else 0,
                    'max_violation_amount': float(max_data[1]) if max_data[1] else 0
                },
                'by_type': [
                    {
                        'violation_type': row.violation_type,
                        '_count': {'id': row.count},
                        '_sum': {'violation_amount': float(row.total_amount) if row.total_amount else 0},
                        '_avg': {'violation_percent': float(row.avg_percent) if row.avg_percent else 0}
                    } for row in type_data
                ],
                'time_series': time_series,
                'filters': {
                    'brand': brand,
                    'competitor': competitor,
                    'start_date': start_date,
                    'end_date': end_date,
                    'group_by': group_by
                }
            }
            
        except Exception as e:
            self.logger.error(f'Error fetching violation statistics: {e}')
            raise
    
    async def export_violation_history(
        self,
        db: AsyncSession,
        brand: Optional[str] = None,
        competitor: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = 'csv'
    ) -> Union[str, Dict[str, Any]]:
        """Export violation history report.
        
        Args:
            db: Database session
            brand: Brand filter
            competitor: Competitor filter
            start_date: Start date filter
            end_date: End date filter
            format: Export format ('csv' or 'json')
            
        Returns:
            CSV string or JSON dict with violation data
        """
        try:
            conditions = []
            
            if start_date:
                conditions.append(ViolationHistory.detected_at >= start_date)
            if end_date:
                conditions.append(ViolationHistory.detected_at <= end_date)
            
            query = select(ViolationHistory).options(
                selectinload(ViolationHistory.product_match).options(
                    selectinload(ProductMatch.idc_product),
                    selectinload(ProductMatch.competitor_product).options(
                        selectinload(CompetitorProduct.competitor)
                    )
                )
            )
            
            # Add brand/competitor filters
            if brand or competitor:
                query = query.join(ViolationHistory.product_match)
                if brand:
                    query = query.join(ProductMatch.idc_product).where(
                        IdcProduct.vendor == brand
                    )
                if competitor:
                    query = query.join(ProductMatch.competitor_product).join(
                        CompetitorProduct.competitor
                    ).where(
                        Competitor.name == competitor
                    )
            
            if conditions:
                query = query.where(and_(*conditions))
            
            query = query.order_by(desc(ViolationHistory.detected_at))
            
            result = await db.execute(query)
            violations = result.scalars().all()
            
            if format == 'csv':
                output = io.StringIO()
                writer = csv.writer(output)
                
                # Write header
                writer.writerow([
                    'Date', 'Brand', 'Product', 'SKU', 'MAP Price', 
                    'Competitor', 'Competitor Price', 'Violation Amount', 
                    'Violation %', 'Type', 'Notes'
                ])
                
                # Write data rows
                for violation in violations:
                    match = violation.product_match
                    writer.writerow([
                        violation.detected_at.isoformat(),
                        match.idc_product.vendor if match.idc_product else '',
                        match.idc_product.title if match.idc_product else '',
                        match.idc_product.sku if match.idc_product else '',
                        float(violation.idc_price),
                        match.competitor_product.competitor.name if match.competitor_product and match.competitor_product.competitor else '',
                        float(violation.competitor_price),
                        float(violation.violation_amount),
                        round(violation.violation_percent, 2),
                        violation.violation_type,
                        violation.notes or ''
                    ])
                
                return output.getvalue()
            
            else:  # JSON format
                return [
                    {
                        'id': violation.id,
                        'detected_at': violation.detected_at,
                        'violation_type': violation.violation_type,
                        'competitor_price': float(violation.competitor_price),
                        'idc_price': float(violation.idc_price),
                        'violation_amount': float(violation.violation_amount),
                        'violation_percent': violation.violation_percent,
                        'notes': violation.notes,
                        'product_match': {
                            'idc_product': {
                                'title': violation.product_match.idc_product.title,
                                'vendor': violation.product_match.idc_product.vendor,
                                'sku': violation.product_match.idc_product.sku
                            } if violation.product_match.idc_product else None,
                            'competitor_product': {
                                'title': violation.product_match.competitor_product.title,
                                'competitor': {
                                    'name': violation.product_match.competitor_product.competitor.name
                                }
                            } if violation.product_match.competitor_product else None
                        }
                    } for violation in violations
                ]
            
        except Exception as e:
            self.logger.error(f'Error exporting violation history: {e}')
            raise
