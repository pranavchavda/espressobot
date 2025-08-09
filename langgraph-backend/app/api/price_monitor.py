"""
Price Monitor API Endpoints

FastAPI router providing price monitoring functionality:
- Dashboard statistics and overview
- Competitor management CRUD operations
- Product matching algorithms
- Shopify synchronization endpoints

Replaces the Node.js price monitor API endpoints with Python equivalents.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.services.price_monitor import (
    PriceMonitorDashboard,
    CompetitorService,
    ProductMatchingService,
    ShopifySyncService,
    AlertsService,
    ViolationsService,
    ScrapingEngineService,
    JobStatusService,
    SettingsService
)
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Request/Response models
class CompetitorCreate(BaseModel):
    name: str
    domain: str
    collections: Optional[List[str]] = []
    scraping_strategy: Optional[str] = 'collections'
    url_patterns: Optional[List[str]] = []
    search_terms: Optional[List[str]] = []
    exclude_patterns: Optional[List[str]] = []
    is_active: Optional[bool] = True
    scrape_schedule: Optional[str] = None
    rate_limit_ms: Optional[int] = 2000

class CompetitorUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    collections: Optional[List[str]] = None
    scraping_strategy: Optional[str] = None
    url_patterns: Optional[List[str]] = None
    search_terms: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    is_active: Optional[bool] = None
    scrape_schedule: Optional[str] = None
    rate_limit_ms: Optional[int] = None

class AutoMatchRequest(BaseModel):
    brands: Optional[List[str]] = None
    min_confidence: Optional[str] = 'medium'
    dry_run: Optional[bool] = False

class ManualMatchRequest(BaseModel):
    idc_product_id: str
    competitor_product_id: str
    confidence_override: Optional[str] = None

class PerfectMatchRequest(BaseModel):
    idc_product_id: str
    competitor_product_id: str

class SyncRequest(BaseModel):
    brands: Optional[List[str]] = None
    force: Optional[bool] = False

class ScrapeJobRequest(BaseModel):
    competitor_ids: Optional[List[str]] = None
    collections: Optional[List[str]] = None

class ClearMatchesRequest(BaseModel):
    include_manual: Optional[bool] = False

# Initialize router
router = APIRouter(prefix="/api/price-monitor", tags=["price-monitor"])

# Initialize services
dashboard_service = PriceMonitorDashboard()
competitor_service = CompetitorService()
matching_service = ProductMatchingService()
shopify_service = ShopifySyncService()
alerts_service = AlertsService()
violations_service = ViolationsService()
scraping_service = ScrapingEngineService()
job_status_service = JobStatusService()
settings_service = SettingsService()

# Dashboard endpoints
@router.get("/dashboard/overview")
async def get_dashboard_overview():
    """Get simple overview statistics for dashboard"""
    try:
        overview = await dashboard_service.get_overview()
        return overview
    except Exception as e:
        logger.error(f"Error fetching dashboard overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard overview")

@router.get("/dashboard/stats")
async def get_dashboard_stats():
    """Get comprehensive dashboard statistics"""
    try:
        stats = await dashboard_service.get_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard stats")

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    period: str = Query('7d', description="Time period: 24h, 7d, or 30d")
):
    """Get summary statistics for charts/graphs"""
    try:
        summary = await dashboard_service.get_summary(period=period)
        return summary
    except Exception as e:
        logger.error(f"Error fetching dashboard summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch dashboard summary")

# Competitor endpoints
@router.get("/competitors")
async def get_competitors(
    search: Optional[str] = Query(None, description="Search by name or domain"),
    status: Optional[str] = Query(None, description="Filter by status: active or inactive")
):
    """Get all competitors with optional filtering"""
    try:
        competitors = await competitor_service.get_competitors(search=search, status=status)
        return competitors
    except Exception as e:
        logger.error(f"Error fetching competitors: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch competitors")

@router.get("/competitors/products")
async def get_competitor_products(
    limit: int = Query(500, description="Maximum number of products to return"),
    search: Optional[str] = Query(None, description="Search by title, vendor, or SKU"),
    competitor_id: Optional[str] = Query(None, description="Filter by competitor ID")
):
    """Get competitor products for manual matching"""
    try:
        products = await competitor_service.get_competitor_products(
            limit=limit, search=search, competitor_id=competitor_id
        )
        return products
    except Exception as e:
        logger.error(f"Error fetching competitor products: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch competitor products")

@router.get("/competitors/{competitor_id}")
async def get_competitor_by_id(competitor_id: str):
    """Get a single competitor by ID"""
    try:
        competitor = await competitor_service.get_competitor_by_id(competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        return competitor
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching competitor {competitor_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch competitor")

@router.post("/competitors")
async def create_competitor(competitor_data: CompetitorCreate):
    """Create a new competitor"""
    try:
        competitor = await competitor_service.create_competitor(competitor_data.dict())
        return competitor
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating competitor: {e}")
        raise HTTPException(status_code=500, detail="Failed to create competitor")

@router.put("/competitors/{competitor_id}")
async def update_competitor(competitor_id: str, competitor_data: CompetitorUpdate):
    """Update an existing competitor"""
    try:
        # Only include non-None fields
        update_data = {k: v for k, v in competitor_data.dict().items() if v is not None}
        competitor = await competitor_service.update_competitor(competitor_id, update_data)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        return competitor
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating competitor {competitor_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update competitor")

@router.delete("/competitors/{competitor_id}")
async def delete_competitor(competitor_id: str):
    """Delete a competitor"""
    try:
        success = await competitor_service.delete_competitor(competitor_id)
        if not success:
            raise HTTPException(status_code=404, detail="Competitor not found")
        return {"message": "Competitor deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting competitor {competitor_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete competitor")

@router.post("/competitors/{competitor_id}/toggle")
async def toggle_competitor_status(competitor_id: str):
    """Toggle competitor active status"""
    try:
        competitor = await competitor_service.toggle_competitor_status(competitor_id)
        if not competitor:
            raise HTTPException(status_code=404, detail="Competitor not found")
        return competitor
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling competitor {competitor_id} status: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle competitor status")

@router.post("/competitors/{competitor_id}/scrape")
async def start_scrape_job(competitor_id: str, request: ScrapeJobRequest):
    """Start scraping for a specific competitor"""
    try:
        result = await competitor_service.start_scrape_job(
            competitor_id, request.collections
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting scrape job for {competitor_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start scraping")

@router.get("/competitors/{competitor_id}/scrape-jobs")
async def get_scrape_jobs(
    competitor_id: str,
    limit: int = Query(20, description="Maximum number of jobs to return"),
    status: Optional[str] = Query(None, description="Filter by job status")
):
    """Get scrape jobs for a competitor"""
    try:
        jobs = await competitor_service.get_scrape_jobs(
            competitor_id, limit=limit, status=status
        )
        return jobs
    except Exception as e:
        logger.error(f"Error fetching scrape jobs for {competitor_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scrape jobs")

# Product matching endpoints
@router.post("/product-matching/auto-match")
async def auto_match_products(request: AutoMatchRequest):
    """Match products automatically using similarity algorithms"""
    try:
        result = await matching_service.auto_match_products(
            brands=request.brands,
            min_confidence=request.min_confidence,
            dry_run=request.dry_run
        )
        return result
    except Exception as e:
        logger.error(f"Error in automatic product matching: {e}")
        raise HTTPException(status_code=500, detail="Failed to match products automatically")

@router.post("/product-matching/manual-match")
async def create_manual_match(request: ManualMatchRequest):
    """Create a manual product match"""
    try:
        result = await matching_service.create_manual_match(
            request.idc_product_id,
            request.competitor_product_id,
            request.confidence_override
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating manual match: {e}")
        raise HTTPException(status_code=500, detail="Failed to create manual product match")

@router.post("/product-matching/perfect-match")
async def create_perfect_match(request: PerfectMatchRequest):
    """Create a perfect manual match with 100% scores"""
    try:
        result = await matching_service.create_perfect_match(
            request.idc_product_id,
            request.competitor_product_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating perfect match: {e}")
        raise HTTPException(status_code=500, detail="Failed to create perfect manual match")

@router.get("/product-matching/matches")
async def get_product_matches(
    confidence_level: Optional[str] = Query(None, description="Filter by confidence level"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    has_violations: Optional[bool] = Query(None, description="Filter by violation status"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Items per page")
):
    """Get product matches with filtering and pagination"""
    try:
        matches = await matching_service.get_matches(
            confidence_level=confidence_level,
            brand=brand,
            has_violations=has_violations,
            page=page,
            limit=limit
        )
        return matches
    except Exception as e:
        logger.error(f"Error fetching product matches: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch product matches")

@router.delete("/product-matching/matches/{match_id}")
async def delete_product_match(match_id: str):
    """Delete a product match"""
    try:
        success = await matching_service.delete_match(match_id)
        if not success:
            raise HTTPException(status_code=404, detail="Product match not found")
        return {"message": "Product match deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting product match {match_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete product match")

@router.post("/product-matching/clear-all-matches")
async def clear_all_matches(request: ClearMatchesRequest):
    """Clear all product matches (automated by default)"""
    try:
        result = await matching_service.clear_all_matches(
            include_manual=request.include_manual
        )
        return result
    except Exception as e:
        logger.error(f"Error clearing product matches: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear product matches")

# Shopify sync endpoints
@router.post("/shopify-sync/sync-idc-products")
async def sync_idc_products(request: SyncRequest):
    """Sync iDC products for monitored brands (safe version)"""
    try:
        result = await shopify_service.sync_idc_products_safe(
            brands=request.brands,
            force=request.force
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing iDC products: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync iDC products")

@router.get("/shopify-sync/sync-status")
async def get_sync_status():
    """Get synchronization status for all brands"""
    try:
        status = await shopify_service.get_sync_status()
        return status
    except Exception as e:
        logger.error(f"Error fetching sync status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch sync status")

@router.get("/shopify-sync/idc-products")
async def get_idc_products(
    brand: Optional[str] = Query(None, description="Filter by brand"),
    search: Optional[str] = Query(None, description="Search by title or SKU"),
    available: Optional[bool] = Query(None, description="Filter by availability"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Items per page")
):
    """Get iDC products with filtering and pagination"""
    try:
        products = await shopify_service.get_idc_products(
            brand=brand,
            search=search,
            available=available,
            page=page,
            limit=limit
        )
        return products
    except Exception as e:
        logger.error(f"Error fetching iDC products: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch iDC products")

@router.post("/shopify-sync/sync-brand/{brand_name}")
async def sync_brand(brand_name: str):
    """Sync products for a specific brand"""
    try:
        result = await shopify_service.sync_brand(brand_name)
        return result
    except Exception as e:
        logger.error(f"Error syncing brand {brand_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to sync brand")

@router.post("/shopify-sync/auto-sync")
async def auto_sync():
    """Auto-sync all monitored brands that need syncing"""
    try:
        result = await shopify_service.auto_sync()
        return result
    except Exception as e:
        logger.error(f"Error during auto-sync: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform auto-sync")

@router.get("/shopify-sync/products-by-brand/{brand_name}")
async def get_products_by_brand(
    brand_name: str,
    search: Optional[str] = Query(None, description="Search by title, SKU, or description"),
    available: Optional[bool] = Query(None, description="Filter by availability"),
    price_min: Optional[float] = Query(None, description="Minimum price filter"),
    price_max: Optional[float] = Query(None, description="Maximum price filter"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(50, description="Items per page")
):
    """Get products for a specific brand with enhanced filtering"""
    try:
        products = await shopify_service.get_products_by_brand(
            brand_name=brand_name,
            search=search,
            available=available,
            price_min=price_min,
            price_max=price_max,
            page=page,
            limit=limit
        )
        return products
    except Exception as e:
        logger.error(f"Error fetching products for brand {brand_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch brand products")

@router.get("/shopify-sync/health")
async def health_check():
    """Check Shopify connection health"""
    try:
        health = await shopify_service.health_check()
        if health['status'] == 'unhealthy':
            raise HTTPException(status_code=500, detail=health)
        return health
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Shopify health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "shopify_connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )


# Additional request models for new endpoints
class ViolationScanRequest(BaseModel):
    brands: Optional[List[str]] = None
    severity_filter: Optional[str] = None
    record_history: Optional[bool] = True
    capture_screenshots: Optional[bool] = False
    dry_run: Optional[bool] = False

class BrandCreateRequest(BaseModel):
    brand_name: str
    is_active: Optional[bool] = True

class CollectionCreateRequest(BaseModel):
    collection_name: str
    is_active: Optional[bool] = True

class SystemSettingsRequest(BaseModel):
    confidence_threshold: Optional[float] = None
    scraping_interval: Optional[int] = None
    alert_thresholds: Optional[Dict[str, float]] = None
    rate_limits: Optional[Dict[str, int]] = None
    matching_settings: Optional[Dict[str, float]] = None
    violation_settings: Optional[Dict[str, float]] = None
    scraping_settings: Optional[Dict[str, Any]] = None

class TestConnectionRequest(BaseModel):
    competitor_id: str
    collection: Optional[str] = None


# Alerts endpoints
@router.get("/alerts/data")
async def get_alerts_data(
    db: AsyncSession = Depends(get_db),
    status: str = Query('active', description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    limit: int = Query(50, description="Maximum alerts to return"),
    brand: Optional[str] = Query(None, description="Filter by brand"),
    competitor: Optional[str] = Query(None, description="Filter by competitor"),
    sort_by: str = Query('recent', description="Sort option")
):
    """Get alerts data for EspressoBot tools"""
    try:
        alerts_data = await alerts_service.get_alerts_data(
            db=db,
            status=status,
            severity=severity,
            limit=limit,
            brand=brand,
            competitor=competitor,
            sort_by=sort_by
        )
        return alerts_data
    except Exception as e:
        logger.error(f"Error fetching alerts data: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts data")

@router.post("/alerts/sync")
async def trigger_sync_operation(
    db: AsyncSession = Depends(get_db),
    request: SyncRequest = Body(...)
):
    """Trigger Shopify sync operation"""
    try:
        result = await alerts_service.trigger_sync_operation(
            db=db,
            brands=request.brands,
            limit=100  # Could be made configurable
        )
        return result
    except Exception as e:
        logger.error(f"Error triggering sync operation: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger sync operation")

@router.post("/alerts/scrape")
async def trigger_scraping_operation(
    db: AsyncSession = Depends(get_db),
    request: ScrapeJobRequest = Body(...)
):
    """Trigger competitor scraping operation"""
    try:
        result = await alerts_service.trigger_scraping_operation(
            db=db,
            competitor_ids=request.competitor_ids if hasattr(request, 'competitor_ids') else None,
            collections=request.collections
        )
        return result
    except Exception as e:
        logger.error(f"Error triggering scraping operation: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger scraping operation")

@router.post("/alerts/match")
async def trigger_product_matching(
    db: AsyncSession = Depends(get_db),
    request: AutoMatchRequest = Body(...)
):
    """Trigger product matching operation"""
    try:
        result = await alerts_service.trigger_product_matching(
            db=db,
            brands=request.brands,
            force_rematch=getattr(request, 'force_rematch', False),
            confidence_threshold=getattr(request, 'confidence_threshold', 0.7)
        )
        return result
    except Exception as e:
        logger.error(f"Error triggering matching operation: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger matching operation")

@router.post("/alerts/generate")
async def generate_alerts(
    db: AsyncSession = Depends(get_db),
    request: Dict[str, Any] = Body(...)
):
    """Generate new alerts (scan for MAP violations)"""
    try:
        result = await alerts_service.generate_alerts(
            db=db,
            brands=request.get('brands'),
            severity_filter=request.get('severity_filter'),
            create_alerts=request.get('create_alerts', True),
            dry_run=request.get('dry_run', False)
        )
        return result
    except Exception as e:
        logger.error(f"Error generating alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate alerts")

@router.get("/alerts/status")
async def get_operation_status(
    db: AsyncSession = Depends(get_db),
    operation_type: Optional[str] = Query(None, description="Operation type to check")
):
    """Get operation status"""
    try:
        status = await alerts_service.get_operation_status(db=db, operation_type=operation_type)
        return status
    except Exception as e:
        logger.error(f"Error fetching operation status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch operation status")


# Violations endpoints
@router.post("/violations/scan-and-record")
async def scan_and_record_violations(
    db: AsyncSession = Depends(get_db),
    request: ViolationScanRequest = Body(...)
):
    """Enhanced MAP violation scanner that records history"""
    try:
        result = await violations_service.scan_and_record_violations(
            db=db,
            brands=request.brands,
            severity_filter=request.severity_filter,
            record_history=request.record_history,
            capture_screenshots=request.capture_screenshots,
            dry_run=request.dry_run
        )
        return result
    except Exception as e:
        logger.error(f"Error scanning violations: {e}")
        raise HTTPException(status_code=500, detail="Failed to scan violations")

@router.get("/violations/history/{product_match_id}")
async def get_violation_history(
    product_match_id: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(100, description="Maximum records to return"),
    offset: int = Query(0, description="Offset for pagination"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter")
):
    """Get violation history for a product"""
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        history = await violations_service.get_violation_history(
            db=db,
            product_match_id=product_match_id,
            limit=limit,
            offset=offset,
            start_date=start_dt,
            end_date=end_dt
        )
        return history
    except Exception as e:
        logger.error(f"Error fetching violation history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch violation history")

@router.get("/violations/statistics")
async def get_violation_statistics(
    db: AsyncSession = Depends(get_db),
    brand: Optional[str] = Query(None, description="Brand filter"),
    competitor: Optional[str] = Query(None, description="Competitor filter"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    group_by: str = Query('day', description="Time grouping")
):
    """Get aggregated violation statistics"""
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        statistics = await violations_service.get_violation_statistics(
            db=db,
            brand=brand,
            competitor=competitor,
            start_date=start_dt,
            end_date=end_dt,
            group_by=group_by
        )
        return statistics
    except Exception as e:
        logger.error(f"Error fetching violation statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch violation statistics")

@router.get("/violations/export")
async def export_violation_history(
    db: AsyncSession = Depends(get_db),
    brand: Optional[str] = Query(None, description="Brand filter"),
    competitor: Optional[str] = Query(None, description="Competitor filter"),
    start_date: Optional[str] = Query(None, description="Start date filter"),
    end_date: Optional[str] = Query(None, description="End date filter"),
    format: str = Query('csv', description="Export format")
):
    """Export violation history report"""
    try:
        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None
        
        export_data = await violations_service.export_violation_history(
            db=db,
            brand=brand,
            competitor=competitor,
            start_date=start_dt,
            end_date=end_dt,
            format=format
        )
        
        if format == 'csv':
            from fastapi.responses import Response
            return Response(
                content=export_data,
                media_type='text/csv',
                headers={"Content-Disposition": f"attachment; filename=violation-history-{datetime.utcnow().strftime('%Y-%m-%d')}.csv"}
            )
        else:
            return export_data
    except Exception as e:
        logger.error(f"Error exporting violation history: {e}")
        raise HTTPException(status_code=500, detail="Failed to export violation history")


# Scraping Engine endpoints
@router.post("/scraping/start-scrape")
async def start_scrape_job(
    db: AsyncSession = Depends(get_db),
    request: Dict[str, Any] = Body(...)
):
    """Start scraping job for a competitor"""
    try:
        result = await scraping_service.start_scrape_job(
            db=db,
            competitor_id=request.get('competitor_id'),
            collections=request.get('collections')
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting scrape job: {e}")
        raise HTTPException(status_code=500, detail="Failed to start scraping job")

@router.get("/scraping/job/{job_id}/status")
async def get_scrape_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get scrape job status"""
    try:
        job_status = await scraping_service.get_job_status(db=db, job_id=job_id)
        if not job_status:
            raise HTTPException(status_code=404, detail="Scrape job not found")
        return job_status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job status: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job status")

@router.get("/scraping/jobs")
async def get_recent_scrape_jobs(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, description="Maximum jobs to return"),
    status: Optional[str] = Query(None, description="Filter by job status"),
    competitor_id: Optional[str] = Query(None, description="Filter by competitor")
):
    """Get recent scrape jobs"""
    try:
        jobs = await scraping_service.get_recent_jobs(
            db=db,
            limit=limit,
            status=status,
            competitor_id=competitor_id
        )
        return jobs
    except Exception as e:
        logger.error(f"Error fetching scrape jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch scrape jobs")

@router.post("/scraping/test-connection")
async def test_competitor_connection(
    db: AsyncSession = Depends(get_db),
    request: TestConnectionRequest = Body(...)
):
    """Test competitor connection"""
    try:
        result = await scraping_service.test_connection(
            db=db,
            competitor_id=request.competitor_id,
            collection=request.collection
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        raise HTTPException(status_code=500, detail="Failed to test connection")


# Job Status endpoints
@router.post("/job-status/record")
async def record_job_execution(
    db: AsyncSession = Depends(get_db),
    request: Dict[str, Any] = Body(...)
):
    """Record a job execution"""
    try:
        job_id = await job_status_service.record_job_execution(
            db=db,
            job_type=request.get('job_type'),
            status=request.get('status', 'completed'),
            details=request.get('details'),
            competitor_id=request.get('competitor_id'),
            duration_seconds=request.get('duration_seconds')
        )
        return {'message': 'Job execution recorded', 'job_id': job_id}
    except Exception as e:
        logger.error(f"Error recording job execution: {e}")
        raise HTTPException(status_code=500, detail="Failed to record job execution")

@router.get("/job-status/last-runs")
async def get_last_runs(
    db: AsyncSession = Depends(get_db)
):
    """Get last execution times for each job type"""
    try:
        last_runs = await job_status_service.get_last_runs(db=db)
        return last_runs
    except Exception as e:
        logger.error(f"Error fetching last runs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch last runs")

@router.get("/job-status/history/{job_type}")
async def get_job_history(
    job_type: str,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, description="Maximum records to return")
):
    """Get job history for a specific type"""
    try:
        history = await job_status_service.get_job_history(
            db=db,
            job_type=job_type,
            limit=limit
        )
        return history
    except Exception as e:
        logger.error(f"Error fetching job history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job history")

@router.get("/job-status/statistics")
async def get_job_statistics(
    db: AsyncSession = Depends(get_db),
    days: int = Query(7, description="Number of days to look back")
):
    """Get job execution statistics"""
    try:
        statistics = await job_status_service.get_job_statistics(db=db, days=days)
        return statistics
    except Exception as e:
        logger.error(f"Error fetching job statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job statistics")

@router.get("/job-status/active")
async def get_active_jobs(
    db: AsyncSession = Depends(get_db)
):
    """Get currently active/running jobs"""
    try:
        active_jobs = await job_status_service.get_active_jobs(db=db)
        return active_jobs
    except Exception as e:
        logger.error(f"Error fetching active jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch active jobs")


# Settings endpoints
@router.get("/settings/monitored-brands")
async def get_monitored_brands(
    db: AsyncSession = Depends(get_db)
):
    """Get monitored brands"""
    try:
        brands = await settings_service.get_monitored_brands(db=db)
        return brands
    except Exception as e:
        logger.error(f"Error fetching monitored brands: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch monitored brands")

@router.post("/settings/monitored-brands")
async def create_monitored_brand(
    db: AsyncSession = Depends(get_db),
    request: BrandCreateRequest = Body(...)
):
    """Create monitored brand"""
    try:
        brand = await settings_service.create_monitored_brand(
            db=db,
            brand_name=request.brand_name,
            is_active=request.is_active
        )
        return brand
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating monitored brand: {e}")
        raise HTTPException(status_code=500, detail="Failed to create monitored brand")

@router.put("/settings/monitored-brands/{brand_id}/toggle")
async def toggle_monitored_brand(
    brand_id: str,
    db: AsyncSession = Depends(get_db),
    request: Dict[str, bool] = Body(default={})
):
    """Toggle monitored brand status"""
    try:
        brand = await settings_service.toggle_monitored_brand(
            db=db,
            brand_id=brand_id,
            is_active=request.get('is_active')
        )
        return brand
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error toggling brand status: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle brand status")

@router.delete("/settings/monitored-brands/{brand_id}")
async def delete_monitored_brand(
    brand_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete monitored brand"""
    try:
        result = await settings_service.delete_monitored_brand(db=db, brand_id=brand_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting brand: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete brand")

@router.get("/settings/monitored-collections")
async def get_monitored_collections(
    db: AsyncSession = Depends(get_db)
):
    """Get monitored collections"""
    try:
        collections = await settings_service.get_monitored_collections(db=db)
        return collections
    except Exception as e:
        logger.error(f"Error fetching monitored collections: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch monitored collections")

@router.post("/settings/monitored-collections")
async def create_monitored_collection(
    db: AsyncSession = Depends(get_db),
    request: CollectionCreateRequest = Body(...)
):
    """Create monitored collection"""
    try:
        collection = await settings_service.create_monitored_collection(
            db=db,
            collection_name=request.collection_name,
            is_active=request.is_active
        )
        return collection
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating monitored collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to create monitored collection")

@router.post("/settings/monitored-collections/{collection_id}/toggle")
async def toggle_monitored_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Toggle monitored collection status"""
    try:
        collection = await settings_service.toggle_monitored_collection(
            db=db,
            collection_id=collection_id
        )
        return collection
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error toggling collection status: {e}")
        raise HTTPException(status_code=500, detail="Failed to toggle collection status")

@router.delete("/settings/monitored-collections/{collection_id}")
async def delete_monitored_collection(
    collection_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete monitored collection"""
    try:
        result = await settings_service.delete_monitored_collection(
            db=db,
            collection_id=collection_id
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete collection")

@router.get("/settings/system")
async def get_system_settings():
    """Get system settings"""
    try:
        settings = await settings_service.get_system_settings()
        return settings
    except Exception as e:
        logger.error(f"Error fetching system settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system settings")

@router.post("/settings/system")
async def update_system_settings(
    request: SystemSettingsRequest = Body(...)
):
    """Update system settings"""
    try:
        result = await settings_service.update_system_settings(
            confidence_threshold=request.confidence_threshold,
            scraping_interval=request.scraping_interval,
            alert_thresholds=request.alert_thresholds,
            rate_limits=request.rate_limits,
            matching_settings=request.matching_settings,
            violation_settings=request.violation_settings,
            scraping_settings=request.scraping_settings
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating system settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to update system settings")

@router.post("/settings/system/reset")
async def reset_system_settings():
    """Reset system settings to defaults"""
    try:
        result = await settings_service.reset_system_settings()
        return result
    except Exception as e:
        logger.error(f"Error resetting system settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset system settings")

@router.get("/settings/system/validate")
async def validate_system_settings(
    settings: SystemSettingsRequest = Body(...)
):
    """Validate settings configuration"""
    try:
        validation = await settings_service.validate_settings(settings.dict(exclude_unset=True))
        return validation
    except Exception as e:
        logger.error(f"Error validating settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate settings")
