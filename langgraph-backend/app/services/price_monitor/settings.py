"""Settings service for price monitoring system.

Provides configuration management functionality including:
- Monitored brands CRUD operations
- Monitored collections management
- System settings configuration
- Rate limiting and threshold management
- Configuration validation and persistence

Ports functionality from settings.js with enhanced validation.
"""

from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime
from decimal import Decimal
import uuid
import logging
import json

from app.database.price_monitor_models import (
    MonitoredBrand, MonitoredCollection
)

logger = logging.getLogger(__name__)


# Default system settings - in production this could be stored in a dedicated settings table
DEFAULT_SETTINGS = {
    'confidence_threshold': 0.7,
    'scraping_interval': 24,
    'alert_thresholds': {
        'map_violation': 0.05,
        'price_change': 0.10
    },
    'rate_limits': {
        'requests_per_minute': 30,
        'delay_between_requests': 2000
    },
    'matching_settings': {
        'min_title_similarity': 0.6,
        'min_embedding_similarity': 0.7,
        'brand_weight': 0.3,
        'title_weight': 0.4,
        'embedding_weight': 0.3
    },
    'violation_settings': {
        'minor_threshold': 0.01,  # 1%
        'moderate_threshold': 0.10,  # 10%
        'severe_threshold': 0.20  # 20%
    },
    'scraping_settings': {
        'max_pages_per_collection': 50,
        'timeout_seconds': 30,
        'retry_attempts': 3,
        'user_agent': 'Mozilla/5.0 (compatible; PriceMonitor/1.0)'
    }
}


class SettingsService:
    """Service for managing price monitor settings and configuration."""
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
        self._cached_settings = None
    
    # Monitored Brands Management
    
    async def get_monitored_brands(self, db: AsyncSession) -> Dict[str, List[Dict[str, Any]]]:
        """Get all monitored brands with product counts.
        
        Args:
            db: Database session
            
        Returns:
            Dict with brands list
        """
        try:
            # Get brands with product counts
            query = select(
                MonitoredBrand,
                func.count(MonitoredBrand.idc_products.property.mapper.class_.id).label('product_count')
            ).outerjoin(
                MonitoredBrand.idc_products
            ).group_by(
                MonitoredBrand.id
            ).order_by(MonitoredBrand.brand_name)
            
            result = await db.execute(query)
            rows = result.all()
            
            brands = []
            for row in rows:
                brand = row[0]  # MonitoredBrand object
                product_count = row[1] if row[1] else 0
                
                brands.append({
                    'id': brand.id,
                    'brand_name': brand.brand_name,
                    'is_active': brand.is_active,
                    'created_at': brand.created_at,
                    'updated_at': brand.updated_at,
                    '_count': {
                        'idc_products': product_count
                    }
                })
            
            return {'brands': brands}
        
        except Exception as e:
            self.logger.error(f'Error fetching monitored brands: {e}')
            raise
    
    async def create_monitored_brand(
        self,
        db: AsyncSession,
        brand_name: str,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """Create a new monitored brand.
        
        Args:
            db: Database session
            brand_name: Name of the brand
            is_active: Whether the brand is active
            
        Returns:
            Created brand data
        """
        try:
            if not brand_name or not brand_name.strip():
                raise ValueError('Brand name is required')
            
            brand_name = brand_name.strip()
            
            # Check if brand already exists
            existing_query = select(MonitoredBrand).where(
                MonitoredBrand.brand_name == brand_name
            )
            result = await db.execute(existing_query)
            existing_brand = result.scalar_one_or_none()
            
            if existing_brand:
                raise ValueError('Brand already exists')
            
            # Create new brand
            brand = MonitoredBrand(
                id=str(uuid.uuid4()),
                brand_name=brand_name,
                is_active=is_active,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(brand)
            await db.commit()
            await db.refresh(brand)
            
            return {
                'id': brand.id,
                'brand_name': brand.brand_name,
                'is_active': brand.is_active,
                'created_at': brand.created_at,
                'updated_at': brand.updated_at
            }
        
        except ValueError:
            raise
        except Exception as e:
            await db.rollback()
            self.logger.error(f'Error creating monitored brand: {e}')
            raise
    
    async def toggle_monitored_brand(
        self,
        db: AsyncSession,
        brand_id: str,
        is_active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """Toggle monitored brand status.
        
        Args:
            db: Database session
            brand_id: ID of the brand
            is_active: New active status (if None, toggle current status)
            
        Returns:
            Updated brand data
        """
        try:
            brand_query = select(MonitoredBrand).where(MonitoredBrand.id == brand_id)
            result = await db.execute(brand_query)
            brand = result.scalar_one_or_none()
            
            if not brand:
                raise ValueError('Brand not found')
            
            # Set new status
            if is_active is not None:
                brand.is_active = is_active
            else:
                brand.is_active = not brand.is_active
            
            brand.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(brand)
            
            return {
                'id': brand.id,
                'brand_name': brand.brand_name,
                'is_active': brand.is_active,
                'created_at': brand.created_at,
                'updated_at': brand.updated_at
            }
        
        except ValueError:
            raise
        except Exception as e:
            await db.rollback()
            self.logger.error(f'Error toggling brand status: {e}')
            raise
    
    async def delete_monitored_brand(
        self,
        db: AsyncSession,
        brand_id: str
    ) -> Dict[str, str]:
        """Delete a monitored brand.
        
        Args:
            db: Database session
            brand_id: ID of the brand to delete
            
        Returns:
            Success message
        """
        try:
            brand_query = select(MonitoredBrand).where(MonitoredBrand.id == brand_id)
            result = await db.execute(brand_query)
            brand = result.scalar_one_or_none()
            
            if not brand:
                raise ValueError('Brand not found')
            
            await db.delete(brand)
            await db.commit()
            
            return {'message': 'Brand deleted successfully'}
        
        except ValueError:
            raise
        except Exception as e:
            await db.rollback()
            self.logger.error(f'Error deleting brand: {e}')
            raise
    
    # Monitored Collections Management
    
    async def get_monitored_collections(self, db: AsyncSession) -> Dict[str, List[Dict[str, Any]]]:
        """Get all monitored collections.
        
        Args:
            db: Database session
            
        Returns:
            Dict with collections list
        """
        try:
            query = select(MonitoredCollection).order_by(MonitoredCollection.collection_name)
            result = await db.execute(query)
            collections = result.scalars().all()
            
            collections_data = []
            for collection in collections:
                collections_data.append({
                    'id': collection.id,
                    'collection_name': collection.collection_name,
                    'is_active': collection.is_active,
                    'created_at': collection.created_at,
                    'updated_at': collection.updated_at
                })
            
            return {'collections': collections_data}
        
        except Exception as e:
            self.logger.error(f'Error fetching monitored collections: {e}')
            raise
    
    async def create_monitored_collection(
        self,
        db: AsyncSession,
        collection_name: str,
        is_active: bool = True
    ) -> Dict[str, Any]:
        """Create a new monitored collection.
        
        Args:
            db: Database session
            collection_name: Name of the collection
            is_active: Whether the collection is active
            
        Returns:
            Created collection data
        """
        try:
            if not collection_name or not collection_name.strip():
                raise ValueError('Collection name is required')
            
            collection_name = collection_name.strip()
            
            # Check if collection already exists
            existing_query = select(MonitoredCollection).where(
                MonitoredCollection.collection_name == collection_name
            )
            result = await db.execute(existing_query)
            existing_collection = result.scalar_one_or_none()
            
            if existing_collection:
                raise ValueError('Collection already exists')
            
            # Create new collection
            collection = MonitoredCollection(
                id=str(uuid.uuid4()),
                collection_name=collection_name,
                is_active=is_active,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(collection)
            await db.commit()
            await db.refresh(collection)
            
            return {
                'id': collection.id,
                'collection_name': collection.collection_name,
                'is_active': collection.is_active,
                'created_at': collection.created_at,
                'updated_at': collection.updated_at
            }
        
        except ValueError:
            raise
        except Exception as e:
            await db.rollback()
            self.logger.error(f'Error creating monitored collection: {e}')
            raise
    
    async def toggle_monitored_collection(
        self,
        db: AsyncSession,
        collection_id: str
    ) -> Dict[str, Any]:
        """Toggle monitored collection status.
        
        Args:
            db: Database session
            collection_id: ID of the collection
            
        Returns:
            Updated collection data
        """
        try:
            collection_query = select(MonitoredCollection).where(
                MonitoredCollection.id == collection_id
            )
            result = await db.execute(collection_query)
            collection = result.scalar_one_or_none()
            
            if not collection:
                raise ValueError('Collection not found')
            
            collection.is_active = not collection.is_active
            collection.updated_at = datetime.utcnow()
            
            await db.commit()
            await db.refresh(collection)
            
            return {
                'id': collection.id,
                'collection_name': collection.collection_name,
                'is_active': collection.is_active,
                'created_at': collection.created_at,
                'updated_at': collection.updated_at
            }
        
        except ValueError:
            raise
        except Exception as e:
            await db.rollback()
            self.logger.error(f'Error toggling collection status: {e}')
            raise
    
    async def delete_monitored_collection(
        self,
        db: AsyncSession,
        collection_id: str
    ) -> Dict[str, str]:
        """Delete a monitored collection.
        
        Args:
            db: Database session
            collection_id: ID of the collection to delete
            
        Returns:
            Success message
        """
        try:
            collection_query = select(MonitoredCollection).where(
                MonitoredCollection.id == collection_id
            )
            result = await db.execute(collection_query)
            collection = result.scalar_one_or_none()
            
            if not collection:
                raise ValueError('Collection not found')
            
            await db.delete(collection)
            await db.commit()
            
            return {'message': 'Collection deleted successfully'}
        
        except ValueError:
            raise
        except Exception as e:
            await db.rollback()
            self.logger.error(f'Error deleting collection: {e}')
            raise
    
    # System Settings Management
    
    async def get_system_settings(self) -> Dict[str, Any]:
        """Get system settings.
        
        Returns:
            Dict with system settings
        """
        try:
            # For now, return default settings
            # In production, this could be enhanced to read from a database table
            if self._cached_settings:
                return self._cached_settings
            
            return DEFAULT_SETTINGS.copy()
        
        except Exception as e:
            self.logger.error(f'Error fetching system settings: {e}')
            raise
    
    async def update_system_settings(
        self,
        confidence_threshold: Optional[float] = None,
        scraping_interval: Optional[int] = None,
        alert_thresholds: Optional[Dict[str, float]] = None,
        rate_limits: Optional[Dict[str, int]] = None,
        matching_settings: Optional[Dict[str, float]] = None,
        violation_settings: Optional[Dict[str, float]] = None,
        scraping_settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update system settings with validation.
        
        Args:
            confidence_threshold: Product matching confidence threshold
            scraping_interval: Scraping interval in hours
            alert_thresholds: Alert threshold settings
            rate_limits: Rate limiting settings
            matching_settings: Product matching algorithm settings
            violation_settings: Violation threshold settings
            scraping_settings: Scraping behavior settings
            
        Returns:
            Updated settings
        """
        try:
            # Validate settings
            if confidence_threshold is not None:
                if not (0.1 <= confidence_threshold <= 1.0):
                    raise ValueError('Confidence threshold must be between 0.1 and 1.0')
            
            if scraping_interval is not None:
                if scraping_interval < 1:
                    raise ValueError('Scraping interval must be at least 1 hour')
            
            if alert_thresholds:
                for key, value in alert_thresholds.items():
                    if not (0.0 <= value <= 1.0):
                        raise ValueError(f'Alert threshold {key} must be between 0.0 and 1.0')
            
            if rate_limits:
                if 'requests_per_minute' in rate_limits and rate_limits['requests_per_minute'] < 1:
                    raise ValueError('Requests per minute must be at least 1')
                if 'delay_between_requests' in rate_limits and rate_limits['delay_between_requests'] < 100:
                    raise ValueError('Delay between requests must be at least 100ms')
            
            if matching_settings:
                for key, value in matching_settings.items():
                    if 'similarity' in key or 'threshold' in key:
                        if not (0.0 <= value <= 1.0):
                            raise ValueError(f'Matching setting {key} must be between 0.0 and 1.0')
                    elif 'weight' in key:
                        if not (0.0 <= value <= 1.0):
                            raise ValueError(f'Weight setting {key} must be between 0.0 and 1.0')
            
            if violation_settings:
                thresholds = ['minor_threshold', 'moderate_threshold', 'severe_threshold']
                values = []
                for threshold in thresholds:
                    if threshold in violation_settings:
                        value = violation_settings[threshold]
                        if not (0.0 <= value <= 1.0):
                            raise ValueError(f'Violation threshold {threshold} must be between 0.0 and 1.0')
                        values.append(value)
                
                # Ensure thresholds are in ascending order
                if len(values) > 1 and not all(values[i] <= values[i+1] for i in range(len(values)-1)):
                    raise ValueError('Violation thresholds must be in ascending order (minor <= moderate <= severe)')
            
            if scraping_settings:
                if 'max_pages_per_collection' in scraping_settings:
                    if scraping_settings['max_pages_per_collection'] < 1:
                        raise ValueError('Max pages per collection must be at least 1')
                if 'timeout_seconds' in scraping_settings:
                    if scraping_settings['timeout_seconds'] < 5:
                        raise ValueError('Timeout must be at least 5 seconds')
                if 'retry_attempts' in scraping_settings:
                    if scraping_settings['retry_attempts'] < 1:
                        raise ValueError('Retry attempts must be at least 1')
            
            # Get current settings
            current_settings = await self.get_system_settings()
            
            # Update settings
            updated_settings = current_settings.copy()
            
            if confidence_threshold is not None:
                updated_settings['confidence_threshold'] = confidence_threshold
            
            if scraping_interval is not None:
                updated_settings['scraping_interval'] = scraping_interval
            
            if alert_thresholds:
                updated_settings['alert_thresholds'].update(alert_thresholds)
            
            if rate_limits:
                updated_settings['rate_limits'].update(rate_limits)
            
            if matching_settings:
                if 'matching_settings' not in updated_settings:
                    updated_settings['matching_settings'] = {}
                updated_settings['matching_settings'].update(matching_settings)
            
            if violation_settings:
                if 'violation_settings' not in updated_settings:
                    updated_settings['violation_settings'] = {}
                updated_settings['violation_settings'].update(violation_settings)
            
            if scraping_settings:
                if 'scraping_settings' not in updated_settings:
                    updated_settings['scraping_settings'] = {}
                updated_settings['scraping_settings'].update(scraping_settings)
            
            # Cache the updated settings
            self._cached_settings = updated_settings
            
            # In production, you would save these to a database table here
            # await self._save_settings_to_db(db, updated_settings)
            
            self.logger.info('System settings updated successfully')
            
            return {
                'message': 'Settings updated successfully',
                'settings': updated_settings
            }
        
        except ValueError:
            raise
        except Exception as e:
            self.logger.error(f'Error updating system settings: {e}')
            raise
    
    async def reset_system_settings(self) -> Dict[str, Any]:
        """Reset system settings to defaults.
        
        Returns:
            Reset settings
        """
        try:
            self._cached_settings = DEFAULT_SETTINGS.copy()
            
            self.logger.info('System settings reset to defaults')
            
            return {
                'message': 'Settings reset to defaults',
                'settings': self._cached_settings
            }
        
        except Exception as e:
            self.logger.error(f'Error resetting system settings: {e}')
            raise
    
    async def get_setting_value(self, setting_path: str) -> Any:
        """Get a specific setting value by path.
        
        Args:
            setting_path: Dot-separated path to setting (e.g., 'alert_thresholds.map_violation')
            
        Returns:
            Setting value
        """
        try:
            settings = await self.get_system_settings()
            
            # Navigate the setting path
            keys = setting_path.split('.')
            value = settings
            
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    raise ValueError(f'Setting path not found: {setting_path}')
            
            return value
        
        except Exception as e:
            self.logger.error(f'Error getting setting value {setting_path}: {e}')
            raise
    
    async def validate_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Validate settings configuration.
        
        Args:
            settings: Settings to validate
            
        Returns:
            Validation results
        """
        try:
            validation_results = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            # Validate confidence threshold
            if 'confidence_threshold' in settings:
                threshold = settings['confidence_threshold']
                if not isinstance(threshold, (int, float)) or not (0.1 <= threshold <= 1.0):
                    validation_results['errors'].append(
                        'Confidence threshold must be a number between 0.1 and 1.0'
                    )
                    validation_results['valid'] = False
            
            # Validate scraping interval
            if 'scraping_interval' in settings:
                interval = settings['scraping_interval']
                if not isinstance(interval, int) or interval < 1:
                    validation_results['errors'].append(
                        'Scraping interval must be an integer >= 1 hour'
                    )
                    validation_results['valid'] = False
                elif interval < 6:
                    validation_results['warnings'].append(
                        'Scraping interval less than 6 hours may cause rate limiting issues'
                    )
            
            # Validate rate limits
            if 'rate_limits' in settings:
                rate_limits = settings['rate_limits']
                if isinstance(rate_limits, dict):
                    if 'requests_per_minute' in rate_limits:
                        rpm = rate_limits['requests_per_minute']
                        if not isinstance(rpm, int) or rpm < 1:
                            validation_results['errors'].append(
                                'Requests per minute must be an integer >= 1'
                            )
                            validation_results['valid'] = False
                        elif rpm > 60:
                            validation_results['warnings'].append(
                                'High request rate may cause competitor sites to block requests'
                            )
            
            return validation_results
        
        except Exception as e:
            self.logger.error(f'Error validating settings: {e}')
            raise
