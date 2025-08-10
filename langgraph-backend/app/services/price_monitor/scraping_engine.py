"""Scraping engine service for competitor price monitoring.

Provides comprehensive competitor scraping functionality including:
- Generic competitor scraping with multiple strategies
- Shopify-based product collection scraping with pagination
- HTML fallback parsing for non-Shopify sites
- Product data processing and storage
- Price history tracking
- Background job management and status monitoring
- Connection testing and validation

Ports functionality from scraping-engine.js with enhanced error handling.
"""

from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import logging
import asyncio
import aiohttp
import re
from urllib.parse import urlencode, quote
import json

from app.database.price_monitor_models import (
    Competitor, CompetitorProduct, ScrapeJob, PriceHistory
)
from app.database.session import get_db

logger = logging.getLogger(__name__)


class CompetitorScraper:
    """Generic competitor scraping service."""
    
    def __init__(self, competitor: Competitor):
        self.competitor = competitor
        self.base_url = f'https://{competitor.domain}'
        self.rate_limit_ms = competitor.rate_limit_ms or 2000
        self.max_retries = 3
        self.retry_delay = 5000  # 5 seconds
        self.logger = logger.getChild(f'{self.__class__.__name__}[{competitor.name}]')
    
    async def with_retry(self, operation, operation_name: str, max_retries: int = None):
        """Retry wrapper for network requests.
        
        Args:
            operation: Async function to execute
            operation_name: Name of operation for logging
            max_retries: Maximum retry attempts
            
        Returns:
            Result of operation
        """
        max_retries = max_retries or self.max_retries
        
        for attempt in range(1, max_retries + 1):
            try:
                return await operation()
            except Exception as error:
                self.logger.warning(
                    f'{operation_name} attempt {attempt}/{max_retries} failed: {error}'
                )
                
                if attempt == max_retries:
                    raise Exception(
                        f'{operation_name} failed after {max_retries} attempts: {error}'
                    )
                
                # Exponential backoff: 5s, 10s, 20s
                delay = (self.retry_delay * (2 ** (attempt - 1))) / 1000
                self.logger.info(f'Retrying in {delay}s...')
                await asyncio.sleep(delay)
    
    async def wait(self):
        """Wait for rate limiting."""
        await asyncio.sleep(self.rate_limit_ms / 1000)
    
    async def scrape_collection(self, collection: str) -> List[Dict[str, Any]]:
        """Scrape a single collection with pagination support.
        
        Args:
            collection: Collection name to scrape
            
        Returns:
            List of product data
        """
        async def _scrape_operation():
            all_products = []
            page = 1
            has_more_products = True
            detected_page_size = None
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            ) as session:
                
                while has_more_products:
                    # Try Shopify JSON API first
                    url = f'{self.base_url}/collections/{collection}/products.json?limit=250&page={page}'
                    self.logger.info(f'Scraping page {page}: {url}')
                    
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                
                                if not data.get('products') or not isinstance(data['products'], list):
                                    raise Exception('Invalid response format - no products array')
                                
                                products = data['products']
                                self.logger.info(
                                    f'Found {len(products)} products on page {page} of collection {collection}'
                                )
                                
                                # Detect actual page size
                                if page == 1 and products:
                                    detected_page_size = len(products)
                                    if detected_page_size < 250:
                                        self.logger.info(
                                            f'Detected page size: {detected_page_size} '
                                            f'(ignoring our limit=250 parameter)'
                                        )
                                
                                all_products.extend(products)
                                
                                # Check if we have more products
                                expected_page_size = detected_page_size or 250
                                if len(products) < expected_page_size:
                                    self.logger.info(
                                        f'End of pagination detected: got {len(products)} < '
                                        f'{expected_page_size} products on page {page}'
                                    )
                                    has_more_products = False
                                else:
                                    self.logger.info(
                                        f'Moving to page {page + 1} '
                                        f'(got full page of {len(products)} products)'
                                    )
                                    page += 1
                                    await self.wait()  # Rate limiting
                                
                                # Safety check
                                if page > 50:
                                    self.logger.warning(
                                        f'Safety break: Stopped pagination at page {page} '
                                        f'for collection {collection}'
                                    )
                                    break
                            
                            elif page == 1:
                                # Try HTML fallback on first page failure
                                self.logger.info(
                                    f'Shopify JSON failed ({response.status}), trying HTML parsing'
                                )
                                return await self._parse_html_collection(session, collection)
                            
                            else:
                                # Reached end on subsequent pages
                                self.logger.info(
                                    f'Reached end of pagination at page {page} ({response.status})'
                                )
                                break
                    
                    except Exception as e:
                        if page == 1:
                            raise e
                        else:
                            self.logger.info(f'Error on page {page}, assuming end of results: {e}')
                            break
            
            self.logger.info(
                f'Total products found in collection {collection}: '
                f'{len(all_products)} (across {page} pages)'
            )
            return all_products
        
        return await self.with_retry(_scrape_operation, f'Scraping collection {collection}')
    
    async def _parse_html_collection(
        self, 
        session: aiohttp.ClientSession, 
        collection: str
    ) -> List[Dict[str, Any]]:
        """Parse HTML for products when JSON API is not available.
        
        Args:
            session: HTTP session
            collection: Collection name
            
        Returns:
            List of parsed products
        """
        url = f'{self.base_url}/collections/{collection}'
        
        async with session.get(url, headers={'Accept': 'text/html'}) as response:
            if response.status != 200:
                raise Exception(f'HTTP {response.status}: {response.reason} for {url}')
            
            html = await response.text()
            return self._parse_html_for_products(html, collection)
    
    def _parse_html_for_products(self, html: str, collection: str) -> List[Dict[str, Any]]:
        """Parse HTML content for product information.
        
        Args:
            html: HTML content
            collection: Collection name
            
        Returns:
            List of parsed products
        """
        try:
            products = []
            
            # Look for common product patterns in HTML
            product_patterns = [
                r'(?:data-product-id|product-item|product-card)[^>]*>[\s\S]*?</[^>]+>',
                r'<div[^>]*class="[^"]*product[^"]*"[^>]*>[\s\S]*?</div>'
            ]
            
            product_matches = []
            for pattern in product_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    product_matches.extend(matches)
                    break
            
            for index, match in enumerate(product_matches):
                try:
                    # Extract product info
                    title_patterns = [
                        r'<h[23][^>]*[^>]*title[^>]*>([^<]+)',
                        r'product[_-]title[^>]*>([^<]+)',
                        r'>([^<]{10,80})<'  # Fallback
                    ]
                    
                    price_pattern = r'[\$£€](\d+(?:\.\d{2})?)'
                    link_pattern = r'href=[\'"](/products/[^\'"]+)[\'"]'
                    
                    title = None
                    for title_pattern in title_patterns:
                        title_match = re.search(title_pattern, match, re.IGNORECASE)
                        if title_match:
                            title = title_match.group(1).strip()
                            break
                    
                    price_match = re.search(price_pattern, match)
                    link_match = re.search(link_pattern, match, re.IGNORECASE)
                    
                    if title and price_match:
                        handle = link_match.group(1).replace('/products/', '') if link_match else f'product-{index}'
                        
                        products.append({
                            'id': f'html_{collection}_{index}',
                            'title': title,
                            'vendor': self.competitor.name,
                            'product_type': collection,
                            'handle': handle,
                            'variants': [{
                                'sku': f'{collection}-{index}',
                                'price': price_match.group(1)
                            }],
                            'available': True,
                            'images': []
                        })
                
                except Exception as parse_error:
                    self.logger.error(f'Error parsing product from HTML: {parse_error}')
            
            self.logger.info(f'Parsed {len(products)} products from HTML')
            return products
        
        except Exception as error:
            self.logger.error(f'Error parsing HTML for products: {error}')
            return []
    
    async def process_products(
        self, 
        db: AsyncSession,
        products: List[Dict[str, Any]], 
        collection_name: str
    ) -> Dict[str, Any]:
        """Process and store scraped products.
        
        Args:
            db: Database session
            products: List of product data
            collection_name: Name of collection
            
        Returns:
            Processing results with counts and errors
        """
        results = {
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }
        
        for product in products:
            try:
                await self._process_single_product(db, product, collection_name)
                
                # Check if product already exists
                existing_query = select(CompetitorProduct).where(
                    and_(
                        CompetitorProduct.external_id == str(product['id']),
                        CompetitorProduct.competitor_id == self.competitor.id
                    )
                )
                
                result = await db.execute(existing_query)
                existing = result.scalar_one_or_none()
                
                if existing:
                    results['updated'] += 1
                else:
                    results['created'] += 1
            
            except Exception as error:
                results['errors'] += 1
                results['error_details'].append({
                    'product_id': product['id'],
                    'error': str(error)
                })
                self.logger.error(f'Error processing product {product["id"]}: {error}')
        
        return results
    
    async def _process_single_product(
        self, 
        db: AsyncSession, 
        product: Dict[str, Any], 
        collection_name: str
    ):
        """Process a single product and store in database.
        
        Args:
            db: Database session
            product: Product data
            collection_name: Collection name
        """
        variants = product.get('variants', [])
        images = product.get('images', [])
        
        # Get lowest price from variants
        prices = [
            float(v.get('price', 0)) for v in variants 
            if v.get('price') and float(v.get('price', 0)) > 0
        ]
        lowest_price = min(prices) if prices else None
        
        # Get compare at price from first variant
        compare_at_price = None
        if variants and variants[0].get('compare_at_price'):
            compare_at_price = float(variants[0]['compare_at_price'])
        
        # Prepare product data
        product_data = {
            'external_id': str(product['id']),
            'competitor_id': self.competitor.id,
            'title': product.get('title', ''),
            'vendor': product.get('vendor', ''),
            'product_type': product.get('product_type', ''),
            'handle': product.get('handle', ''),
            'sku': variants[0].get('sku', '') if variants else '',
            'price': Decimal(str(lowest_price)) if lowest_price else None,
            'compare_at_price': Decimal(str(compare_at_price)) if compare_at_price else None,
            'available': product.get('available', True),
            'image_url': images[0].get('src', '') if images else '',
            'product_url': f'{self.base_url}/products/{product.get("handle", "")}',
            'description': product.get('body_html', ''),
            'scraped_at': datetime.utcnow()
        }
        
        # Generate embedding if embeddings service is available
        from app.memory.embedding_service import get_embedding_service
        embedding_service = get_embedding_service()
        
        # Create combined text for embedding
        embedding_text = f"{product_data['title']} {product_data['vendor']} {product_data['product_type']} {product_data['description']}"
        try:
            embedding_result = await embedding_service.get_embedding(embedding_text)
            # Store as JSON string for database compatibility
            product_data['embedding'] = json.dumps(embedding_result.embedding)
        except Exception as embedding_error:
            logger.warning(f"Failed to generate embedding for competitor product {product['id']}: {embedding_error}")
            product_data['embedding'] = None
        
        # Upsert product
        existing_query = select(CompetitorProduct).where(
            and_(
                CompetitorProduct.external_id == product_data['external_id'],
                CompetitorProduct.competitor_id == product_data['competitor_id']
            )
        )
        
        result = await db.execute(existing_query)
        existing_product = result.scalar_one_or_none()
        
        if existing_product:
            # Update existing product
            for key, value in product_data.items():
                setattr(existing_product, key, value)
            existing_product.updated_at = datetime.utcnow()
            competitor_product = existing_product
        else:
            # Create new product
            competitor_product = CompetitorProduct(
                id=str(uuid.uuid4()),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **product_data
            )
            db.add(competitor_product)
        
        await db.flush()  # Flush to get the ID
        
        # Store price history if price changed
        if lowest_price:
            # Get last price record
            last_price_query = select(PriceHistory).where(
                PriceHistory.competitor_product_id == competitor_product.id
            ).order_by(desc(PriceHistory.recorded_at)).limit(1)
            
            last_price_result = await db.execute(last_price_query)
            last_price = last_price_result.scalar_one_or_none()
            
            # Only store if price is different from last recorded price
            if not last_price or abs(float(last_price.price) - lowest_price) > 0.01:
                price_history = PriceHistory(
                    id=str(uuid.uuid4()),
                    competitor_product_id=competitor_product.id,
                    price=Decimal(str(lowest_price)),
                    compare_at_price=Decimal(str(compare_at_price)) if compare_at_price else None,
                    available=product_data['available'],
                    recorded_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(price_history)
    
    async def scrape(self, db: AsyncSession, collections: Optional[List[str]] = None) -> Dict[str, Any]:
        """Main scraping method with flexible strategies.
        
        Args:
            db: Database session
            collections: Optional list of collections to scrape
            
        Returns:
            Scraping results with counts and errors
        """
        strategy = self.competitor.scraping_strategy or 'collections'
        self.logger.info(f'Using scraping strategy: {strategy}')
        
        results = {
            'competitor': self.competitor.name,
            'strategy': strategy,
            'sources_scraped': 0,
            'total_products': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'error_details': []
        }
        
        try:
            all_products = []
            
            if strategy == 'collections':
                all_products = await self._scrape_by_collections(collections)
            elif strategy == 'url_patterns':
                all_products = await self._scrape_by_url_patterns()
            elif strategy == 'search_terms':
                all_products = await self._scrape_by_search_terms()
            else:
                raise Exception(f'Unknown scraping strategy: {strategy}')
            
            # Filter excluded products
            filtered_products = self._filter_excluded_products(all_products)
            self.logger.info(
                f'Found {len(all_products)} products, {len(filtered_products)} after exclusions'
            )
            
            # Process all products
            if filtered_products:
                processing_results = await self.process_products(
                    db, filtered_products, strategy
                )
                results.update({
                    'total_products': len(filtered_products),
                    'created': processing_results['created'],
                    'updated': processing_results['updated'],
                    'errors': processing_results['errors'],
                    'error_details': processing_results['error_details']
                })
            
            results['sources_scraped'] = 1
            self.logger.info(
                f'Strategy {strategy}: {results["total_products"]} products, '
                f'{results["created"]} created, {results["updated"]} updated, '
                f'{results["errors"]} errors'
            )
        
        except Exception as error:
            self.logger.error(f'Failed to scrape using strategy {strategy}: {error}')
            results['errors'] += 1
            results['error_details'].append({
                'strategy': strategy,
                'error': str(error)
            })
        
        return results
    
    async def _scrape_by_collections(self, collections: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Scrape using collections strategy."""
        collections_to_scrape = collections or self.competitor.collections
        
        if not collections_to_scrape:
            raise Exception('No collections specified for collections strategy')
        
        all_products = []
        
        for collection in collections_to_scrape:
            try:
                self.logger.info(f'Scraping collection: {collection}')
                products = await self.scrape_collection(collection)
                all_products.extend(products)
                
                # Rate limiting between collections
                if collection != collections_to_scrape[-1]:
                    await self.wait()
            
            except Exception as error:
                self.logger.error(f'Failed to scrape collection {collection}: {error}')
                raise
        
        return all_products
    
    async def _scrape_by_url_patterns(self) -> List[Dict[str, Any]]:
        """Scrape using URL patterns strategy."""
        patterns = self.competitor.url_patterns or []
        
        if not patterns:
            raise Exception('No URL patterns specified for url_patterns strategy')
        
        all_products = []
        
        for pattern in patterns:
            try:
                self.logger.info(f'Scraping URL pattern: {pattern}')
                
                if '/collections/' in pattern:
                    collection_name = self._extract_collection_from_pattern(pattern)
                    if collection_name:
                        self.logger.info(f'Extracted collection: {collection_name}')
                        products = await self.scrape_collection(collection_name)
                        all_products.extend(products)
                else:
                    self.logger.warning(f'Unsupported pattern format: {pattern}')
                
                await self.wait()
            
            except Exception as error:
                self.logger.error(f'Failed to scrape pattern {pattern}: {error}')
        
        return all_products
    
    async def _scrape_by_search_terms(self) -> List[Dict[str, Any]]:
        """Scrape using search terms strategy."""
        search_terms = self.competitor.search_terms or []
        
        if not search_terms:
            raise Exception('No search terms specified for search_terms strategy')
        
        all_products = []
        
        for term in search_terms:
            try:
                self.logger.info(f'Searching for: {term}')
                products = await self._search_products(term)
                all_products.extend(products)
                await self.wait()
            
            except Exception as error:
                self.logger.error(f'Failed to search for {term}: {error}')
        
        return self._remove_duplicate_products(all_products)
    
    def _extract_collection_from_pattern(self, pattern: str) -> Optional[str]:
        """Extract collection name from URL pattern."""
        match = re.search(r'/(?:collections|products)/([^-*]+)', pattern)
        return match.group(1) if match else None
    
    async def _search_products(self, term: str) -> List[Dict[str, Any]]:
        """Search for products by term."""
        # Try search term as collection name variations
        potential_collections = [
            term.lower(),
            term.lower().replace(' ', '-'),
            term.lower().replace(' ', ''),
            term.lower().split(' ')[0],
            f'{term.lower()}-espresso',
            f'{term.lower()}-machines',
            f'{term.lower()}-grinders',
            f'{term.lower()}-coffee'
        ]
        
        for collection_name in potential_collections:
            try:
                self.logger.info(f'Trying search term as collection: {collection_name}')
                products = await self.scrape_collection(collection_name)
                if products:
                    self.logger.info(
                        f'Found {len(products)} products for search term "{term}" '
                        f'via collection "{collection_name}"'
                    )
                    return products
            except Exception:
                continue
        
        self.logger.warning(f'No products found for search term: {term}')
        return []
    
    def _filter_excluded_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out excluded products based on patterns."""
        exclude_patterns = self.competitor.exclude_patterns or []
        
        if not exclude_patterns:
            return products
        
        filtered_products = []
        
        for product in products:
            product_url = f"/products/{product.get('handle', '')}"
            product_title = product.get('title', '').lower()
            
            # Check if product matches any exclude pattern
            should_exclude = False
            for pattern in exclude_patterns:
                regex_pattern = pattern.replace('*', '.*')
                if re.search(regex_pattern, product_url, re.IGNORECASE) or \
                   re.search(regex_pattern, product_title, re.IGNORECASE):
                    should_exclude = True
                    break
            
            if not should_exclude:
                filtered_products.append(product)
        
        return filtered_products
    
    def _remove_duplicate_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate products based on ID."""
        seen = set()
        unique_products = []
        
        for product in products:
            product_id = product.get('id')
            if product_id not in seen:
                seen.add(product_id)
                unique_products.append(product)
        
        return unique_products


class ScrapingEngineService:
    """Service for managing competitor scraping operations."""
    
    def __init__(self):
        self.logger = logger.getChild(self.__class__.__name__)
    
    async def start_scrape_job(
        self,
        db: AsyncSession,
        competitor_id: str,
        collections: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Start scraping job for a competitor.
        
        Args:
            db: Database session
            competitor_id: ID of competitor to scrape
            collections: Optional list of collections to scrape
            
        Returns:
            Job information
        """
        try:
            self.logger.info(f'Starting scrape job for competitor: {competitor_id}')
            
            # Get competitor details
            competitor_query = select(Competitor).where(Competitor.id == competitor_id)
            result = await db.execute(competitor_query)
            competitor = result.scalar_one_or_none()
            
            if not competitor:
                raise ValueError('Competitor not found')
            
            if not competitor.is_active:
                raise ValueError('Competitor is not active')
            
            self.logger.info(f'Competitor found: {competitor.name}')
            
            # Create scrape job
            scrape_job = ScrapeJob(
                id=str(uuid.uuid4()),
                competitor_id=competitor_id,
                collections=collections or competitor.collections,
                status='running',
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(scrape_job)
            await db.commit()
            
            self.logger.info(f'Scrape job created: {scrape_job.id}')
            
            # Start scraping in background
            asyncio.create_task(
                self._scrape_competitor_background(db, competitor, scrape_job, collections)
            )
            
            return {
                'message': 'Scraping job started',
                'job_id': scrape_job.id,
                'competitor': competitor.name,
                'collections': collections or competitor.collections
            }
        
        except Exception as e:
            self.logger.error(f'Error starting scrape job: {e}')
            raise
    
    async def _scrape_competitor_background(
        self,
        db: AsyncSession,
        competitor: Competitor,
        scrape_job: ScrapeJob,
        collections: Optional[List[str]] = None
    ):
        """Background scraping function.
        
        Args:
            db: Database session
            competitor: Competitor to scrape
            scrape_job: Scrape job record
            collections: Optional collections to scrape
        """
        start_time = datetime.utcnow()
        
        try:
            self.logger.info(f'Starting background scrape for {competitor.name}')
            
            scraper = CompetitorScraper(competitor)
            results = await scraper.scrape(db, collections)
            
            end_time = datetime.utcnow()
            duration_seconds = int((end_time - start_time).total_seconds())
            
            # Update scrape job with results
            scrape_job.status = 'completed'
            scrape_job.products_found = results['total_products']
            scrape_job.products_created = results['created']
            scrape_job.products_updated = results['updated']
            scrape_job.errors = json.dumps(results['error_details']) if results['errors'] > 0 else None
            scrape_job.completed_at = end_time
            scrape_job.duration_seconds = duration_seconds
            
            # Update competitor last scraped time
            competitor.last_scraped_at = end_time
            competitor.total_products = results['created'] + results['updated']
            
            await db.commit()
            
            self.logger.info(
                f'Completed scrape job {scrape_job.id}: {results["total_products"]} products, '
                f'{results["created"]} created, {results["updated"]} updated, '
                f'{results["errors"]} errors ({duration_seconds}s)'
            )
        
        except Exception as error:
            self.logger.error(f'Scrape job {scrape_job.id} failed: {error}')
            
            end_time = datetime.utcnow()
            duration_seconds = int((end_time - start_time).total_seconds())
            
            scrape_job.status = 'failed'
            scrape_job.errors = json.dumps([{'error': str(error)}])
            scrape_job.completed_at = end_time
            scrape_job.duration_seconds = duration_seconds
            
            await db.commit()
    
    async def get_job_status(self, db: AsyncSession, job_id: str) -> Optional[Dict[str, Any]]:
        """Get scrape job status.
        
        Args:
            db: Database session
            job_id: Job ID
            
        Returns:
            Job status information or None if not found
        """
        try:
            query = select(ScrapeJob).options(
                selectinload(ScrapeJob.competitor)
            ).where(ScrapeJob.id == job_id)
            
            result = await db.execute(query)
            job = result.scalar_one_or_none()
            
            if not job:
                return None
            
            return {
                'id': job.id,
                'competitor': {
                    'name': job.competitor.name,
                    'domain': job.competitor.domain
                } if job.competitor else None,
                'status': job.status,
                'collections': job.collections,
                'products_found': job.products_found,
                'products_created': job.products_created,
                'products_updated': job.products_updated,
                'errors': json.loads(job.errors) if job.errors else None,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'duration_seconds': job.duration_seconds,
                'created_at': job.created_at
            }
        
        except Exception as e:
            self.logger.error(f'Error fetching job status: {e}')
            raise
    
    async def get_recent_jobs(
        self,
        db: AsyncSession,
        limit: int = 20,
        status: Optional[str] = None,
        competitor_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get recent scrape jobs.
        
        Args:
            db: Database session
            limit: Maximum jobs to return
            status: Optional status filter
            competitor_id: Optional competitor filter
            
        Returns:
            List of recent jobs
        """
        try:
            conditions = []
            
            if status:
                conditions.append(ScrapeJob.status == status)
            if competitor_id:
                conditions.append(ScrapeJob.competitor_id == competitor_id)
            
            query = select(ScrapeJob).options(
                selectinload(ScrapeJob.competitor)
            ).order_by(desc(ScrapeJob.created_at)).limit(limit)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            result = await db.execute(query)
            jobs = result.scalars().all()
            
            formatted_jobs = []
            for job in jobs:
                formatted_jobs.append({
                    'id': job.id,
                    'competitor': {
                        'name': job.competitor.name,
                        'domain': job.competitor.domain
                    } if job.competitor else None,
                    'status': job.status,
                    'collections': job.collections,
                    'products_found': job.products_found,
                    'products_created': job.products_created,
                    'products_updated': job.products_updated,
                    'error_count': len(json.loads(job.errors)) if job.errors else 0,
                    'started_at': job.started_at,
                    'completed_at': job.completed_at,
                    'duration_seconds': job.duration_seconds,
                    'created_at': job.created_at
                })
            
            return {'jobs': formatted_jobs}
        
        except Exception as e:
            self.logger.error(f'Error fetching scrape jobs: {e}')
            raise
    
    async def test_connection(
        self,
        db: AsyncSession,
        competitor_id: str,
        collection: Optional[str] = None
    ) -> Dict[str, Any]:
        """Test competitor connection.
        
        Args:
            db: Database session
            competitor_id: Competitor ID
            collection: Optional collection to test
            
        Returns:
            Connection test results
        """
        try:
            competitor_query = select(Competitor).where(Competitor.id == competitor_id)
            result = await db.execute(competitor_query)
            competitor = result.scalar_one_or_none()
            
            if not competitor:
                raise ValueError('Competitor not found')
            
            test_collection = collection or (competitor.collections[0] if competitor.collections else None)
            if not test_collection:
                raise ValueError('No collection specified for testing')
            
            scraper = CompetitorScraper(competitor)
            
            try:
                products = await scraper.scrape_collection(test_collection)
                
                sample_products = []
                for product in products[:3]:
                    variants = product.get('variants', [])
                    sample_products.append({
                        'id': product.get('id'),
                        'title': product.get('title'),
                        'vendor': product.get('vendor'),
                        'price': variants[0].get('price') if variants else None
                    })
                
                return {
                    'success': True,
                    'competitor': competitor.name,
                    'collection': test_collection,
                    'products_found': len(products),
                    'sample_products': sample_products
                }
            
            except Exception as scrape_error:
                return {
                    'success': False,
                    'competitor': competitor.name,
                    'collection': test_collection,
                    'error': str(scrape_error)
                }
        
        except Exception as e:
            self.logger.error(f'Error testing connection: {e}')
            raise
