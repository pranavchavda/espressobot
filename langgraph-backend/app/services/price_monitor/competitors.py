"""
Competitor Management Service

Provides CRUD operations for competitors and competitor products.
Handles competitor data management, scraping job management.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, update, delete
from sqlalchemy.orm import selectinload
from app.database import (
    Competitor, CompetitorProduct, ScrapeJob
)
from app.database.session import AsyncSessionLocal
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)

class CompetitorService:
    """Service for competitor management operations"""
    
    def __init__(self):
        self.session_local = AsyncSessionLocal
    
    async def get_competitors(
        self,
        search: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict:
        """Get all competitors with optional filtering"""
        async with self.session_local() as session:
            try:
                query = select(Competitor).options(
                    selectinload(Competitor.competitor_products),
                    selectinload(Competitor.scrape_jobs)
                )
                
                # Apply filters
                if search:
                    query = query.where(
                        or_(
                            Competitor.name.icontains(search),
                            Competitor.domain.icontains(search)
                        )
                    )
                
                if status == 'active':
                    query = query.where(Competitor.is_active == True)
                elif status == 'inactive':
                    query = query.where(Competitor.is_active == False)
                
                query = query.order_by(desc(Competitor.created_at))
                
                result = await session.execute(query)
                competitors = result.scalars().all()
                
                # Transform data to include counts
                formatted_competitors = []
                for competitor in competitors:
                    formatted_competitors.append({
                        **competitor.__dict__,
                        'total_products': len(competitor.competitor_products),
                        'total_scrape_jobs': len(competitor.scrape_jobs)
                    })
                
                return {
                    'competitors': formatted_competitors,
                    'total': len(formatted_competitors)
                }
                
            except Exception as e:
                logger.error(f"Error fetching competitors: {e}")
                raise
    
    async def get_competitor_products(
        self,
        limit: int = 500,
        search: Optional[str] = None,
        competitor_id: Optional[str] = None
    ) -> Dict:
        """Get competitor products for manual matching"""
        async with self.session_local() as session:
            try:
                query = select(CompetitorProduct).options(
                    selectinload(CompetitorProduct.competitor)
                )
                
                # Apply filters
                if search:
                    query = query.where(
                        or_(
                            CompetitorProduct.title.icontains(search),
                            CompetitorProduct.vendor.icontains(search),
                            CompetitorProduct.sku.icontains(search)
                        )
                    )
                
                if competitor_id:
                    query = query.where(CompetitorProduct.competitor_id == competitor_id)
                
                query = query.limit(limit).order_by(desc(CompetitorProduct.scraped_at))
                
                result = await session.execute(query)
                products = result.scalars().all()
                
                # Format products with competitor info
                formatted_products = []
                for product in products:
                    formatted_products.append({
                        **product.__dict__,
                        'competitors': {
                            'id': product.competitor.id if product.competitor else None,
                            'name': product.competitor.name if product.competitor else None,
                            'domain': product.competitor.domain if product.competitor else None
                        } if product.competitor else None
                    })
                
                return {
                    'products': formatted_products,
                    'total': len(formatted_products)
                }
                
            except Exception as e:
                logger.error(f"Error fetching competitor products: {e}")
                raise
    
    async def get_competitor_by_id(self, competitor_id: str) -> Optional[Dict]:
        """Get a single competitor by ID with related data"""
        async with self.session_local() as session:
            try:
                query = select(Competitor).options(
                    selectinload(Competitor.competitor_products),
                    selectinload(Competitor.scrape_jobs)
                ).where(Competitor.id == competitor_id)
                
                result = await session.execute(query)
                competitor = result.scalar_one_or_none()
                
                if not competitor:
                    return None
                
                return {
                    **competitor.__dict__,
                    'competitor_products': [
                        {**product.__dict__} for product in competitor.competitor_products
                    ],
                    'scrape_jobs': [
                        {**job.__dict__} for job in competitor.scrape_jobs
                    ],
                    'total_products': len(competitor.competitor_products),
                    'total_scrape_jobs': len(competitor.scrape_jobs)
                }
                
            except Exception as e:
                logger.error(f"Error fetching competitor {competitor_id}: {e}")
                raise
    
    async def create_competitor(self, competitor_data: Dict) -> Dict:
        """Create a new competitor"""
        async with self.session_local() as session:
            try:
                # Validate required fields
                name = competitor_data.get('name')
                domain = competitor_data.get('domain')
                
                if not name or not domain:
                    raise ValueError('Name and domain are required')
                
                # Check if domain already exists
                existing = await session.execute(
                    select(Competitor).where(Competitor.domain == domain)
                )
                if existing.scalar_one_or_none():
                    raise ValueError('A competitor with this domain already exists')
                
                # Create competitor
                competitor = Competitor(
                    id=str(uuid4()),
                    name=name,
                    domain=domain,
                    collections=competitor_data.get('collections', []),
                    scraping_strategy=competitor_data.get('scraping_strategy', 'collections'),
                    url_patterns=competitor_data.get('url_patterns', []),
                    search_terms=competitor_data.get('search_terms', []),
                    exclude_patterns=competitor_data.get('exclude_patterns', []),
                    is_active=competitor_data.get('is_active', True),
                    scrape_schedule=competitor_data.get('scrape_schedule'),
                    rate_limit_ms=competitor_data.get('rate_limit_ms', 2000),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                session.add(competitor)
                await session.commit()
                await session.refresh(competitor)
                
                logger.info(f"Created competitor: {competitor.name}")
                return competitor.__dict__
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error creating competitor: {e}")
                raise
    
    async def update_competitor(self, competitor_id: str, competitor_data: Dict) -> Optional[Dict]:
        """Update an existing competitor"""
        async with self.session_local() as session:
            try:
                # Get existing competitor
                competitor = await session.get(Competitor, competitor_id)
                if not competitor:
                    return None
                
                # If domain is being changed, check if new domain already exists
                new_domain = competitor_data.get('domain')
                if new_domain and new_domain != competitor.domain:
                    existing = await session.execute(
                        select(Competitor).where(Competitor.domain == new_domain)
                    )
                    if existing.scalar_one_or_none():
                        raise ValueError('A competitor with this domain already exists')
                
                # Update fields
                for field in ['name', 'domain', 'collections', 'scraping_strategy', 
                             'url_patterns', 'search_terms', 'exclude_patterns',
                             'is_active', 'scrape_schedule', 'rate_limit_ms']:
                    if field in competitor_data:
                        setattr(competitor, field, competitor_data[field])
                
                competitor.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(competitor)
                
                logger.info(f"Updated competitor: {competitor.name}")
                return competitor.__dict__
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error updating competitor {competitor_id}: {e}")
                raise
    
    async def delete_competitor(self, competitor_id: str) -> bool:
        """Delete a competitor and all related data"""
        async with self.session_local() as session:
            try:
                # Check if competitor exists
                competitor = await session.get(Competitor, competitor_id)
                if not competitor:
                    return False
                
                # Delete competitor (cascade will handle related records)
                await session.delete(competitor)
                await session.commit()
                
                logger.info(f"Deleted competitor: {competitor.name}")
                return True
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error deleting competitor {competitor_id}: {e}")
                raise
    
    async def toggle_competitor_status(self, competitor_id: str) -> Optional[Dict]:
        """Toggle competitor active status"""
        async with self.session_local() as session:
            try:
                competitor = await session.get(Competitor, competitor_id)
                if not competitor:
                    return None
                
                competitor.is_active = not competitor.is_active
                competitor.updated_at = datetime.utcnow()
                
                await session.commit()
                await session.refresh(competitor)
                
                logger.info(f"Toggled competitor {competitor.name} status to: {competitor.is_active}")
                return competitor.__dict__
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error toggling competitor {competitor_id} status: {e}")
                raise
    
    async def start_scrape_job(self, competitor_id: str, collections: Optional[List[str]] = None) -> Dict:
        """Start a scraping job for a competitor"""
        async with self.session_local() as session:
            try:
                competitor = await session.get(Competitor, competitor_id)
                if not competitor:
                    raise ValueError('Competitor not found')
                
                if not competitor.is_active:
                    raise ValueError('Competitor is not active')
                
                # Create scrape job
                scrape_job = ScrapeJob(
                    id=str(uuid4()),
                    competitor_id=competitor_id,
                    collections=collections or competitor.collections,
                    status='pending',
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                session.add(scrape_job)
                await session.commit()
                await session.refresh(scrape_job)
                
                # TODO: Trigger actual scraping process here
                # This would typically be handled by a background job queue
                
                logger.info(f"Created scrape job {scrape_job.id} for competitor {competitor.name}")
                
                return {
                    'message': 'Scraping job queued successfully',
                    'job': scrape_job.__dict__
                }
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error starting scrape job for {competitor_id}: {e}")
                raise
    
    async def get_scrape_jobs(
        self,
        competitor_id: str,
        limit: int = 20,
        status: Optional[str] = None
    ) -> Dict:
        """Get scrape jobs for a competitor"""
        async with self.session_local() as session:
            try:
                query = select(ScrapeJob).where(ScrapeJob.competitor_id == competitor_id)
                
                if status:
                    query = query.where(ScrapeJob.status == status)
                
                query = query.limit(limit).order_by(desc(ScrapeJob.created_at))
                
                result = await session.execute(query)
                scrape_jobs = result.scalars().all()
                
                return {
                    'scrape_jobs': [job.__dict__ for job in scrape_jobs]
                }
                
            except Exception as e:
                logger.error(f"Error fetching scrape jobs for {competitor_id}: {e}")
                raise
