"""
Shopify Synchronization Service

Provides Shopify integration for syncing iDC products including:
- GraphQL API integration
- Product synchronization by brand
- Sync status tracking
- Health monitoring
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from decimal import Decimal
import asyncio
import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_, delete
from sqlalchemy.orm import selectinload
from app.database import (
    IdcProduct, MonitoredBrand
)
from app.database.session import AsyncSessionLocal
from uuid import uuid4
import os
import logging
import json

logger = logging.getLogger(__name__)

class ShopifySyncService:
    """Service for Shopify synchronization operations"""
    
    def __init__(self):
        self.session_local = AsyncSessionLocal
        self.shopify_admin_url = f"{os.getenv('SHOPIFY_SHOP_URL', '')}/admin/api/2024-01/graphql.json"
        self.shopify_access_token = os.getenv('SHOPIFY_ACCESS_TOKEN', '')
        
        # GraphQL query for fetching products by vendor
        self.products_by_vendor_query = """
        query getProductsByVendor($vendor: String!, $first: Int!, $after: String) {
            products(first: $first, after: $after, query: $vendor) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                edges {
                    node {
                        id
                        title
                        handle
                        vendor
                        productType
                        description
                        status
                        publishedAt
                        images(first: 1) {
                            edges {
                                node {
                                    url
                                    altText
                                }
                            }
                        }
                        variants(first: 1) {
                            edges {
                                node {
                                    id
                                    sku
                                    price
                                    compareAtPrice
                                    availableForSale
                                    inventoryQuantity
                                }
                            }
                        }
                        createdAt
                        updatedAt
                    }
                }
            }
        }
        """
    
    async def shopify_graphql_request(self, query: str, variables: Dict = None) -> Dict:
        """Make GraphQL request to Shopify Admin API"""
        if not self.shopify_admin_url or not self.shopify_access_token:
            raise ValueError("Shopify configuration not found. Check SHOPIFY_SHOP_URL and SHOPIFY_ACCESS_TOKEN")
        
        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.shopify_access_token,
        }
        
        payload = {
            'query': query,
            'variables': variables or {}
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.shopify_admin_url,
                json=payload,
                headers=headers
            ) as response:
                if response.status != 200:
                    raise Exception(f"Shopify API error: {response.status} {await response.text()}")
                
                data = await response.json()
                
                if data.get('errors'):
                    raise Exception(f"GraphQL errors: {data['errors']}")
                
                return data['data']
    
    async def sync_idc_products_safe(
        self,
        brands: Optional[List[str]] = None,
        force: bool = False
    ) -> Dict:
        """Safely sync iDC products for monitored brands (preserves manual matches)"""
        async with self.session_local() as session:
            try:
                # Get brands to sync
                brands_to_sync = brands
                if not brands_to_sync:
                    monitored_brands_result = await session.execute(
                        select(MonitoredBrand.brand_name).where(MonitoredBrand.is_active == True)
                    )
                    brands_to_sync = [row[0] for row in monitored_brands_result]
                
                if not brands_to_sync:
                    raise ValueError('No brands specified and no active monitored brands found')
                
                total_synced = 0
                total_errors = 0
                results = []
                
                for brand_name in brands_to_sync:
                    try:
                        logger.info(f"Syncing products for brand: {brand_name}")
                        
                        # Find or create monitored brand
                        monitored_brand_query = select(MonitoredBrand).where(MonitoredBrand.brand_name == brand_name)
                        monitored_brand_result = await session.execute(monitored_brand_query)
                        monitored_brand = monitored_brand_result.scalar_one_or_none()
                        if not monitored_brand:
                            monitored_brand = MonitoredBrand(
                                id=str(uuid4()),
                                brand_name=brand_name,
                                is_active=True,
                                created_at=datetime.utcnow(),
                                updated_at=datetime.utcnow()
                            )
                            session.add(monitored_brand)
                            await session.commit()
                        
                        # Sync products for this brand
                        brand_result = await self._sync_brand_products(
                            session, brand_name, monitored_brand.id
                        )
                        
                        results.append({
                            'brand': brand_name,
                            'products_synced': brand_result['products_synced'],
                            'errors': brand_result['errors'],
                            'success': brand_result['errors'] == 0
                        })
                        
                        total_synced += brand_result['products_synced']
                        total_errors += brand_result['errors']
                        
                        logger.info(
                            f"Synced {brand_result['products_synced']} products for {brand_name} "
                            f"({brand_result['errors']} errors)"
                        )
                        
                        # Rate limiting between brands
                        await asyncio.sleep(1)
                        
                    except Exception as brand_error:
                        logger.error(f"Error syncing brand {brand_name}: {brand_error}")
                        results.append({
                            'brand': brand_name,
                            'products_synced': 0,
                            'errors': 1,
                            'success': False,
                            'error': str(brand_error)
                        })
                        total_errors += 1
                
                return {
                    'message': f"Sync completed: {total_synced} products synced, {total_errors} errors",
                    'total_synced': total_synced,
                    'total_errors': total_errors,
                    'results': results
                }
                
            except Exception as e:
                await session.rollback()
                logger.error(f"Error syncing iDC products: {e}")
                raise
    
    async def _sync_brand_products(self, session: AsyncSession, brand_name: str, brand_id: str) -> Dict:
        """Sync products for a specific brand"""
        try:
            has_next_page = True
            cursor = None
            brand_product_count = 0
            brand_error_count = 0
            
            while has_next_page:
                try:
                    # Fetch products from Shopify
                    data = await self.shopify_graphql_request(
                        self.products_by_vendor_query,
                        {
                            'vendor': f'vendor:{brand_name} AND status:active',
                            'first': 50,
                            'after': cursor
                        }
                    )
                    
                    products = data['products']
                    has_next_page = products['pageInfo']['hasNextPage']
                    cursor = products['pageInfo']['endCursor']
                    
                    # Process each product
                    for edge in products['edges']:
                        product = edge['node']
                        
                        # Skip inactive products or those without published date
                        if product['status'] != 'ACTIVE' or not product['publishedAt']:
                            continue
                        
                        try:
                            # Extract product data
                            first_variant = product['variants']['edges'][0]['node'] if product['variants']['edges'] else None
                            first_image = product['images']['edges'][0]['node'] if product['images']['edges'] else None
                            
                            # Skip products without available variants or with no price
                            if (
                                not first_variant or 
                                not first_variant.get('availableForSale') or 
                                not first_variant.get('price') or 
                                float(first_variant['price']) <= 0
                            ):
                                continue
                            
                            # Prepare product data
                            now = datetime.utcnow()
                            product_data = {
                                'shopify_id': product['id'],
                                'title': product['title'],
                                'vendor': product['vendor'],
                                'product_type': product.get('productType'),
                                'handle': product.get('handle'),
                                'description': product.get('description'),
                                'image_url': first_image.get('url') if first_image else None,
                                'sku': first_variant.get('sku'),
                                'price': Decimal(str(first_variant['price'])) if first_variant.get('price') else None,
                                'compare_at_price': (
                                    Decimal(str(first_variant['compareAtPrice'])) 
                                    if first_variant.get('compareAtPrice') else None
                                ),
                                'available': first_variant.get('availableForSale', False),
                                'inventory_quantity': first_variant.get('inventoryQuantity', 0),
                                'brand_id': brand_id,
                                'last_synced_at': now,
                                'updated_at': now
                            }
                            
                            # Generate embedding for the product
                            from app.memory.embedding_service import get_embedding_service
                            embedding_service = get_embedding_service()
                            
                            # Create combined text for embedding
                            embedding_text = f"{product_data['title']} {product_data['vendor']} {product_data['product_type'] or ''} {product_data['description'] or ''}"
                            try:
                                embedding_result = await embedding_service.get_embedding(embedding_text)
                                # Store as JSON string for database compatibility
                                product_data['embedding'] = json.dumps(embedding_result.embedding)
                            except Exception as embedding_error:
                                logger.warning(f"Failed to generate embedding for product {product['id']}: {embedding_error}")
                                product_data['embedding'] = None
                            
                            # Upsert product
                            existing_product = await session.get(IdcProduct, product['id'])
                            if existing_product:
                                # Update existing product
                                for key, value in product_data.items():
                                    if key != 'id':  # Don't update the primary key
                                        setattr(existing_product, key, value)
                            else:
                                # Create new product
                                new_product = IdcProduct(
                                    id=product['id'],
                                    **product_data
                                )
                                session.add(new_product)
                            
                            brand_product_count += 1
                            
                        except Exception as product_error:
                            logger.error(f"Error syncing product {product['id']}: {product_error}")
                            brand_error_count += 1
                    
                    # Commit batch
                    await session.commit()
                    
                except Exception as page_error:
                    logger.error(f"Error fetching page for {brand_name}: {page_error}")
                    brand_error_count += 1
                    break
            
            return {
                'products_synced': brand_product_count,
                'errors': brand_error_count
            }
            
        except Exception as e:
            logger.error(f"Error syncing brand {brand_name}: {e}")
            return {
                'products_synced': 0,
                'errors': 1
            }
    
    async def get_sync_status(self) -> Dict:
        """Get synchronization status for all brands"""
        async with self.session_local() as session:
            try:
                # Get product counts by brand
                products_by_brand_result = await session.execute(
                    select(
                        IdcProduct.vendor,
                        func.count(IdcProduct.id).label('count')
                    ).group_by(IdcProduct.vendor).order_by(desc('count'))
                )
                products_by_brand = {row.vendor: row.count for row in products_by_brand_result}
                
                # Get monitored brands with sync times
                brands_result = await session.execute(
                    select(MonitoredBrand).options(
                        selectinload(MonitoredBrand.idc_products)
                    )
                )
                monitored_brands = brands_result.scalars().all()
                
                # Get total counts
                total_products = await session.scalar(select(func.count(IdcProduct.id)))
                active_brands = await session.scalar(
                    select(func.count(MonitoredBrand.id)).where(MonitoredBrand.is_active == True)
                )
                
                # Format brand statistics
                brand_stats = []
                for brand in monitored_brands:
                    last_synced_at = None
                    if brand.idc_products:
                        last_synced_at = max(
                            product.last_synced_at for product in brand.idc_products
                            if product.last_synced_at
                        )
                    
                    needs_sync = (
                        not last_synced_at or 
                        (datetime.utcnow() - last_synced_at) > timedelta(hours=24)
                    )
                    
                    brand_stats.append({
                        'brand_name': brand.brand_name,
                        'is_active': brand.is_active,
                        'product_count': products_by_brand.get(brand.brand_name, 0),
                        'last_synced_at': last_synced_at.isoformat() if last_synced_at else None,
                        'needs_sync': needs_sync
                    })
                
                return {
                    'total_products': total_products or 0,
                    'active_brands': active_brands or 0,
                    'brand_stats': brand_stats,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error fetching sync status: {e}")
                raise
    
    async def get_idc_products(
        self,
        brand: Optional[str] = None,
        search: Optional[str] = None,
        available: Optional[bool] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict:
        """Get iDC products with filtering and pagination"""
        async with self.session_local() as session:
            try:
                offset = (page - 1) * limit
                
                query = select(IdcProduct).options(
                    selectinload(IdcProduct.monitored_brand)
                )
                
                # Apply filters
                if brand:
                    query = query.where(IdcProduct.vendor == brand)
                
                if search:
                    query = query.where(
                        or_(
                            IdcProduct.title.icontains(search),
                            IdcProduct.sku.icontains(search)
                        )
                    )
                
                if available is not None:
                    query = query.where(IdcProduct.available == available)
                
                # Get paginated results
                products_result = await session.execute(
                    query.offset(offset).limit(limit).order_by(desc(IdcProduct.last_synced_at))
                )
                products = products_result.scalars().all()
                
                # Get total count
                count_query = select(func.count(IdcProduct.id))
                if brand:
                    count_query = count_query.where(IdcProduct.vendor == brand)
                if search:
                    count_query = count_query.where(
                        or_(
                            IdcProduct.title.icontains(search),
                            IdcProduct.sku.icontains(search)
                        )
                    )
                if available is not None:
                    count_query = count_query.where(IdcProduct.available == available)
                
                total_count = await session.scalar(count_query)
                
                # Format products
                formatted_products = []
                for product in products:
                    formatted_product = {
                        **product.__dict__,
                        'monitored_brands': product.monitored_brand.__dict__ if product.monitored_brand else None
                    }
                    formatted_products.append(formatted_product)
                
                return {
                    'products': formatted_products,
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total_count or 0,
                        'total_pages': ((total_count or 0) + limit - 1) // limit,
                        'has_next': offset + limit < (total_count or 0),
                        'has_prev': page > 1
                    }
                }
                
            except Exception as e:
                logger.error(f"Error fetching iDC products: {e}")
                raise
    
    async def sync_brand(self, brand_name: str) -> Dict:
        """Sync products for a specific brand"""
        return await self.sync_idc_products_safe(brands=[brand_name])
    
    async def auto_sync(self) -> Dict:
        """Auto-sync all monitored brands that need syncing"""
        async with self.session_local() as session:
            try:
                logger.info("Starting auto-sync for all monitored brands...")
                
                # Find brands that need syncing (older than 24 hours or never synced)
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                
                # Get brands with no products or old sync times
                brands_result = await session.execute(
                    select(MonitoredBrand.brand_name)
                    .where(MonitoredBrand.is_active == True)
                    .outerjoin(IdcProduct, MonitoredBrand.id == IdcProduct.brand_id)
                    .group_by(MonitoredBrand.brand_name)
                    .having(
                        or_(
                            func.count(IdcProduct.id) == 0,
                            func.max(IdcProduct.last_synced_at) < cutoff_time
                        )
                    )
                )
                
                brands_needing_sync = [row[0] for row in brands_result]
                
                if not brands_needing_sync:
                    return {
                        'message': 'No brands need syncing at this time',
                        'brands_checked': 0,
                        'brands_synced': 0
                    }
                
                logger.info(f"Found {len(brands_needing_sync)} brands needing sync: {', '.join(brands_needing_sync)}")
                
                # Sync the brands
                sync_result = await self.sync_idc_products_safe(brands=brands_needing_sync)
                
                return {
                    'message': 'Auto-sync completed',
                    'brands_checked': len(brands_needing_sync),
                    'brands_synced': len(brands_needing_sync),
                    'sync_results': sync_result
                }
                
            except Exception as e:
                logger.error(f"Error during auto-sync: {e}")
                raise
    
    async def get_products_by_brand(
        self,
        brand_name: str,
        search: Optional[str] = None,
        available: Optional[bool] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        page: int = 1,
        limit: int = 50
    ) -> Dict:
        """Get products for a specific brand with enhanced filtering"""
        async with self.session_local() as session:
            try:
                offset = (page - 1) * limit
                
                query = select(IdcProduct).options(
                    selectinload(IdcProduct.monitored_brand)
                ).where(IdcProduct.vendor == brand_name)
                
                # Apply filters
                if search:
                    query = query.where(
                        or_(
                            IdcProduct.title.icontains(search),
                            IdcProduct.sku.icontains(search),
                            IdcProduct.description.icontains(search)
                        )
                    )
                
                if available is not None:
                    query = query.where(IdcProduct.available == available)
                
                if price_min is not None or price_max is not None:
                    if price_min is not None:
                        query = query.where(IdcProduct.price >= Decimal(str(price_min)))
                    if price_max is not None:
                        query = query.where(IdcProduct.price <= Decimal(str(price_max)))
                
                # Get products and total count
                products_result = await session.execute(
                    query.offset(offset).limit(limit).order_by(
                        desc(IdcProduct.available), IdcProduct.price.asc()
                    )
                )
                products = products_result.scalars().all()
                
                total_count = await session.scalar(
                    select(func.count(IdcProduct.id)).where(IdcProduct.vendor == brand_name)
                )
                
                # Get brand statistics
                brand_stats = await session.execute(
                    select(
                        func.count(IdcProduct.id).label('total_products'),
                        func.avg(IdcProduct.price).label('avg_price'),
                        func.min(IdcProduct.price).label('min_price'),
                        func.max(IdcProduct.price).label('max_price')
                    ).where(IdcProduct.vendor == brand_name)
                )
                stats = brand_stats.first()
                
                available_count = await session.scalar(
                    select(func.count(IdcProduct.id)).where(
                        and_(IdcProduct.vendor == brand_name, IdcProduct.available == True)
                    )
                )
                
                # Format response
                formatted_products = []
                for product in products:
                    # Add match count if needed
                    formatted_product = {
                        **product.__dict__,
                        'monitored_brands': product.monitored_brand.__dict__ if product.monitored_brand else None
                    }
                    formatted_products.append(formatted_product)
                
                return {
                    'brand': brand_name,
                    'products': formatted_products,
                    'brand_stats': {
                        'total_products': stats.total_products or 0,
                        'avg_price': float(stats.avg_price) if stats.avg_price else 0,
                        'min_price': float(stats.min_price) if stats.min_price else 0,
                        'max_price': float(stats.max_price) if stats.max_price else 0,
                        'available_count': available_count or 0
                    },
                    'pagination': {
                        'page': page,
                        'limit': limit,
                        'total': total_count or 0,
                        'total_pages': ((total_count or 0) + limit - 1) // limit,
                        'has_next': offset + limit < (total_count or 0),
                        'has_prev': page > 1
                    }
                }
                
            except Exception as e:
                logger.error(f"Error fetching products for brand {brand_name}: {e}")
                raise
    
    async def health_check(self) -> Dict:
        """Check Shopify connection health"""
        try:
            # Test Shopify connection with a simple query
            test_query = """
            query {
                shop {
                    name
                    url
                }
            }
            """
            
            data = await self.shopify_graphql_request(test_query)
            
            return {
                'status': 'healthy',
                'shopify_connected': True,
                'shop': data['shop'],
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Shopify health check failed: {e}")
            return {
                'status': 'unhealthy',
                'shopify_connected': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
