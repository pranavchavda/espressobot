"""Job status service for price monitoring system.

Provides job execution logging and status tracking functionality:
- Job execution recording with details
- Last run time tracking by job type
- Job history retrieval with pagination
- Status monitoring for various price monitoring operations

Ports functionality from job-status.js with enhanced type safety.
"""

from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, case
from datetime import datetime, timedelta
import uuid
import logging
import json

logger = logging.getLogger(__name__)


# Since we don't have job_execution_log table in the current models,
# we'll use the existing scrape_jobs table and extend functionality
# This could be enhanced with a dedicated job_execution_log table later

from app.database.price_monitor_models import ScrapeJob, Competitor


class JobStatusService:
    """Service for managing job execution logging and status tracking."""
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
        # Define supported job types
        self.job_types = [
            'shopify_sync',
            'competitor_scrape', 
            'violation_scan',
            'cron_job',
            'product_matching',
            'alert_generation'
        ]
    
    async def record_job_execution(
        self,
        db: AsyncSession,
        job_type: str,
        status: str = 'completed',
        details: Optional[Dict[str, Any]] = None,
        competitor_id: Optional[str] = None,
        duration_seconds: Optional[int] = None
    ) -> str:
        """Record a job execution.
        
        Args:
            db: Database session
            job_type: Type of job executed
            status: Job status ('completed', 'failed', 'running')
            details: Additional job details
            competitor_id: Optional competitor ID for scraping jobs
            duration_seconds: Job duration in seconds
            
        Returns:
            Job ID
        """
        try:
            # For scraping jobs, use ScrapeJob table
            if job_type == 'competitor_scrape' and competitor_id:
                job = ScrapeJob(
                    id=str(uuid.uuid4()),
                    competitor_id=competitor_id,
                    status=status,
                    collections=[],  # Will be updated by actual scraping process
                    started_at=datetime.utcnow(),
                    completed_at=datetime.utcnow() if status != 'running' else None,
                    duration_seconds=duration_seconds,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                if details:
                    job.products_found = details.get('products_found')
                    job.products_created = details.get('products_created') 
                    job.products_updated = details.get('products_updated')
                    if details.get('errors'):
                        job.errors = json.dumps(details['errors'])
                
                db.add(job)
                await db.commit()
                
                self.logger.info(f'Recorded {job_type} execution: {job.id}')
                return job.id
            
            else:
                # For other job types, we could extend this to use a dedicated
                # job_execution_log table. For now, log the execution.
                job_id = str(uuid.uuid4())
                
                self.logger.info(
                    f'Recorded {job_type} execution: {job_id} '
                    f'(status: {status}, details: {details})'
                )
                
                return job_id
        
        except Exception as e:
            self.logger.error(f'Error recording job execution: {e}')
            raise
    
    async def get_last_runs(self, db: AsyncSession) -> Dict[str, Any]:
        """Get last execution times for each job type.
        
        Args:
            db: Database session
            
        Returns:
            Dict with last run information by job type
        """
        try:
            last_runs_by_type = {}
            
            # Get scraping job information
            scrape_query = select(ScrapeJob).order_by(desc(ScrapeJob.created_at)).limit(1)
            result = await db.execute(scrape_query)
            last_scrape_job = result.scalar_one_or_none()
            
            if last_scrape_job:
                last_runs_by_type['competitor_scrape'] = {
                    'status': last_scrape_job.status,
                    'executed_at': last_scrape_job.completed_at or last_scrape_job.started_at,
                    'details': {
                        'products_found': last_scrape_job.products_found,
                        'products_created': last_scrape_job.products_created,
                        'products_updated': last_scrape_job.products_updated,
                        'duration_seconds': last_scrape_job.duration_seconds,
                        'errors': json.loads(last_scrape_job.errors) if last_scrape_job.errors else None
                    }
                }
            
            # Get today's execution counts for scraping
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            
            today_scrapes_query = select(func.count(ScrapeJob.id)).where(
                ScrapeJob.created_at >= today
            )
            today_scrapes_result = await db.execute(today_scrapes_query)
            today_scrapes_count = today_scrapes_result.scalar() or 0
            
            if 'competitor_scrape' in last_runs_by_type:
                last_runs_by_type['competitor_scrape']['runs_today'] = today_scrapes_count
            
            # For other job types, provide placeholder data
            # This could be enhanced with actual job tracking tables
            for job_type in self.job_types:
                if job_type not in last_runs_by_type:
                    last_runs_by_type[job_type] = {
                        'status': 'unknown',
                        'executed_at': None,
                        'details': {},
                        'runs_today': 0
                    }
            
            return last_runs_by_type
        
        except Exception as e:
            self.logger.error(f'Error fetching last runs: {e}')
            raise
    
    async def get_job_history(
        self,
        db: AsyncSession,
        job_type: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get job history for a specific type.
        
        Args:
            db: Database session
            job_type: Type of job to get history for
            limit: Maximum records to return
            
        Returns:
            List of job execution records
        """
        try:
            if job_type == 'competitor_scrape':
                # Get scraping job history
                query = select(ScrapeJob).options(
                    # selectinload(ScrapeJob.competitor)  # Uncomment if needed
                ).order_by(desc(ScrapeJob.created_at)).limit(limit)
                
                result = await db.execute(query)
                jobs = result.scalars().all()
                
                history = []
                for job in jobs:
                    history.append({
                        'id': job.id,
                        'job_type': 'competitor_scrape',
                        'status': job.status,
                        'executed_at': job.completed_at or job.started_at,
                        'created_at': job.created_at,
                        'details': {
                            'competitor_id': job.competitor_id,
                            'collections': job.collections,
                            'products_found': job.products_found,
                            'products_created': job.products_created,
                            'products_updated': job.products_updated,
                            'duration_seconds': job.duration_seconds,
                            'started_at': job.started_at,
                            'completed_at': job.completed_at,
                            'errors': json.loads(job.errors) if job.errors else None
                        }
                    })
                
                return history
            
            else:
                # For other job types, return empty history for now
                # This could be enhanced with dedicated job logging
                self.logger.info(f'No history available for job type: {job_type}')
                return []
        
        except Exception as e:
            self.logger.error(f'Error fetching job history for {job_type}: {e}')
            raise
    
    async def get_job_statistics(
        self,
        db: AsyncSession,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get job execution statistics.
        
        Args:
            db: Database session
            days: Number of days to look back
            
        Returns:
            Dict with job statistics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Get scraping job statistics
            scrape_stats_query = select(
                func.count(ScrapeJob.id).label('total_jobs'),
                func.sum(case(
                    (ScrapeJob.status == 'completed', 1),
                    else_=0
                )).label('completed_jobs'),
                func.sum(case(
                    (ScrapeJob.status == 'failed', 1),
                    else_=0
                )).label('failed_jobs'),
                func.sum(case(
                    (ScrapeJob.status == 'running', 1),
                    else_=0
                )).label('running_jobs'),
                func.sum(ScrapeJob.products_found).label('total_products_found'),
                func.sum(ScrapeJob.products_created).label('total_products_created'),
                func.sum(ScrapeJob.products_updated).label('total_products_updated'),
                func.avg(ScrapeJob.duration_seconds).label('avg_duration')
            ).where(ScrapeJob.created_at >= start_date)
            
            result = await db.execute(scrape_stats_query)
            stats = result.first()
            
            # Get daily breakdown
            daily_stats_query = select(
                func.date(ScrapeJob.created_at).label('date'),
                func.count(ScrapeJob.id).label('jobs_count'),
                func.sum(ScrapeJob.products_found).label('products_found')
            ).where(
                ScrapeJob.created_at >= start_date
            ).group_by(
                func.date(ScrapeJob.created_at)
            ).order_by(desc(func.date(ScrapeJob.created_at)))
            
            daily_result = await db.execute(daily_stats_query)
            daily_stats = daily_result.all()
            
            # Get competitor breakdown
            competitor_stats_query = select(
                Competitor.name.label('competitor_name'),
                func.count(ScrapeJob.id).label('jobs_count'),
                func.sum(ScrapeJob.products_found).label('products_found')
            ).join(
                ScrapeJob, ScrapeJob.competitor_id == Competitor.id
            ).where(
                ScrapeJob.created_at >= start_date
            ).group_by(
                Competitor.name
            ).order_by(
                desc(func.count(ScrapeJob.id))
            )
            
            competitor_result = await db.execute(competitor_stats_query)
            competitor_stats = competitor_result.all()
            
            return {
                'period_days': days,
                'summary': {
                    'total_jobs': stats.total_jobs or 0,
                    'completed_jobs': stats.completed_jobs or 0,
                    'failed_jobs': stats.failed_jobs or 0,
                    'running_jobs': stats.running_jobs or 0,
                    'success_rate': (
                        (stats.completed_jobs or 0) / (stats.total_jobs or 1)
                    ) * 100,
                    'total_products_found': stats.total_products_found or 0,
                    'total_products_created': stats.total_products_created or 0,
                    'total_products_updated': stats.total_products_updated or 0,
                    'avg_duration_seconds': float(stats.avg_duration or 0)
                },
                'daily_breakdown': [
                    {
                        'date': row.date,
                        'jobs_count': row.jobs_count,
                        'products_found': row.products_found or 0
                    } for row in daily_stats
                ],
                'competitor_breakdown': [
                    {
                        'competitor_name': row.competitor_name,
                        'jobs_count': row.jobs_count,
                        'products_found': row.products_found or 0
                    } for row in competitor_stats
                ]
            }
        
        except Exception as e:
            self.logger.error(f'Error fetching job statistics: {e}')
            raise
    
    async def get_active_jobs(self, db: AsyncSession) -> Dict[str, Any]:
        """Get currently active/running jobs.
        
        Args:
            db: Database session
            
        Returns:
            Dict with active job information
        """
        try:
            # Get running scrape jobs
            active_scrapes_query = select(ScrapeJob).options(
                # selectinload(ScrapeJob.competitor)  # Uncomment if needed
            ).where(
                ScrapeJob.status == 'running'
            ).order_by(desc(ScrapeJob.started_at))
            
            result = await db.execute(active_scrapes_query)
            active_scrape_jobs = result.scalars().all()
            
            active_jobs = []
            for job in active_scrape_jobs:
                # Calculate running time
                running_time = datetime.utcnow() - job.started_at
                running_seconds = int(running_time.total_seconds())
                
                active_jobs.append({
                    'id': job.id,
                    'job_type': 'competitor_scrape',
                    'status': job.status,
                    'competitor_id': job.competitor_id,
                    'collections': job.collections,
                    'started_at': job.started_at,
                    'running_seconds': running_seconds,
                    'products_found': job.products_found,
                    'products_created': job.products_created,
                    'products_updated': job.products_updated
                })
            
            return {
                'active_jobs': active_jobs,
                'total_active': len(active_jobs)
            }
        
        except Exception as e:
            self.logger.error(f'Error fetching active jobs: {e}')
            raise
    
    async def cleanup_old_jobs(
        self,
        db: AsyncSession,
        days_to_keep: int = 30
    ) -> Dict[str, Any]:
        """Clean up old job records.
        
        Args:
            db: Database session
            days_to_keep: Number of days of job history to keep
            
        Returns:
            Cleanup results
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # Count jobs to be deleted
            count_query = select(func.count(ScrapeJob.id)).where(
                and_(
                    ScrapeJob.created_at < cutoff_date,
                    ScrapeJob.status.in_(['completed', 'failed'])  # Keep running jobs
                )
            )
            
            count_result = await db.execute(count_query)
            jobs_to_delete = count_result.scalar() or 0
            
            if jobs_to_delete > 0:
                # Delete old jobs
                delete_query = select(ScrapeJob).where(
                    and_(
                        ScrapeJob.created_at < cutoff_date,
                        ScrapeJob.status.in_(['completed', 'failed'])
                    )
                )
                
                result = await db.execute(delete_query)
                old_jobs = result.scalars().all()
                
                for job in old_jobs:
                    await db.delete(job)
                
                await db.commit()
                
                self.logger.info(f'Cleaned up {jobs_to_delete} old job records')
            
            return {
                'jobs_deleted': jobs_to_delete,
                'cutoff_date': cutoff_date,
                'days_kept': days_to_keep
            }
        
        except Exception as e:
            self.logger.error(f'Error cleaning up old jobs: {e}')
            raise
