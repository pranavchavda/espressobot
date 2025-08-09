"""
Price Monitor Service Module

Provides comprehensive price monitoring functionality including:
- Dashboard statistics and overview
- Competitor management and scraping
- Product matching algorithms
- Shopify synchronization
- Alert management and notifications
- Violation tracking and reporting
- Job status monitoring
- System settings management

All services use async/await patterns and SQLAlchemy ORM.
"""

from .dashboard import PriceMonitorDashboard
from .competitors import CompetitorService
from .product_matching import ProductMatchingService
from .shopify_sync import ShopifySyncService
from .alerts import AlertsService
from .violations import ViolationsService, MAPViolationDetector
from .scraping_engine import ScrapingEngineService, CompetitorScraper
from .job_status import JobStatusService
from .settings import SettingsService

__all__ = [
    'PriceMonitorDashboard',
    'CompetitorService', 
    'ProductMatchingService',
    'ShopifySyncService',
    'AlertsService',
    'ViolationsService',
    'MAPViolationDetector',
    'ScrapingEngineService',
    'CompetitorScraper',
    'JobStatusService',
    'SettingsService'
]