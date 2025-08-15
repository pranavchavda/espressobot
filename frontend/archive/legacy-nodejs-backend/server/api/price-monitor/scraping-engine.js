import express from 'express';
import { db, withRetry, ensureConnection } from '../../config/database.js';

const prisma = db;
import embeddingsService from '../../services/embeddings-service.js';
import { randomUUID } from 'crypto';

const router = express.Router();

// Generic competitor scraping service
class CompetitorScraper {
  constructor(competitor) {
    this.competitor = competitor;
    this.baseUrl = `https://${competitor.domain}`;
    this.rateLimitMs = competitor.rate_limit_ms || 2000;
    this.maxRetries = 3;
    this.retryDelay = 5000; // 5 seconds
  }

  // Retry wrapper for network requests
  async withRetry(operation, operationName, maxRetries = this.maxRetries) {
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        console.log(`⚠️  ${operationName} attempt ${attempt}/${maxRetries} failed:`, error.message);
        
        if (attempt === maxRetries) {
          throw new Error(`${operationName} failed after ${maxRetries} attempts: ${error.message}`);
        }
        
        // Exponential backoff: 5s, 10s, 20s
        const delay = this.retryDelay * Math.pow(2, attempt - 1);
        console.log(`⏳ Retrying in ${delay/1000}s...`);
        await new Promise(resolve => setTimeout(resolve, delay));
      }
    }
  }

  // Wait for rate limiting
  async wait() {
    return new Promise(resolve => setTimeout(resolve, this.rateLimitMs));
  }

  // Scrape a single collection - enhanced to handle different site types with pagination
  async scrapeCollection(collection) {
    return await this.withRetry(async () => {
      let allProducts = [];
      let page = 1;
      let hasMoreProducts = true;
      let detectedPageSize = null; // Track what page size the competitor actually returns
      
      while (hasMoreProducts) {
        // Try Shopify JSON API first (most common for coffee retailers)
        // Use limit=250 (Shopify max) and page parameter for pagination
        let url = `${this.baseUrl}/collections/${collection}/products.json?limit=250&page=${page}`;
        console.log(`🔍 [${this.competitor.name}] Scraping page ${page}: ${url}`);

        let response = await fetch(url, {
          headers: {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
          },
          timeout: 30000,
        });

        // If Shopify JSON fails, try alternative approaches (only on first page)
        if (!response.ok && page === 1) {
          console.log(`Shopify JSON failed (${response.status}), trying alternative methods...`);
          
          // Try collection page scraping
          url = `${this.baseUrl}/collections/${collection}`;
          response = await fetch(url, {
            headers: {
              'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Accept-Language': 'en-US,en;q=0.9',
            },
            timeout: 30000,
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText} for ${url}`);
          }

          // Parse HTML for product data (basic implementation)
          const html = await response.text();
          return this.parseHTMLForProducts(html, collection);
        }

        if (!response.ok) {
          // If we're on page > 1 and get an error, we've probably reached the end
          if (page > 1) {
            console.log(`📄 Reached end of pagination at page ${page} (${response.status})`);
            break;
          }
          throw new Error(`HTTP ${response.status}: ${response.statusText} for ${url}`);
        }

        const data = await response.json();
        
        if (!data.products || !Array.isArray(data.products)) {
          throw new Error('Invalid response format - no products array');
        }

        console.log(`✅ [${this.competitor.name}] Found ${data.products.length} products on page ${page} of collection ${collection}`);
        
        // Detect the actual page size this competitor uses
        if (page === 1 && data.products.length > 0) {
          detectedPageSize = data.products.length;
          if (detectedPageSize < 250) {
            console.log(`🔍 [${this.competitor.name}] Detected page size: ${detectedPageSize} (ignoring our limit=250 parameter)`);
          }
        }
        
        // Add products from this page
        allProducts.push(...data.products);
        
        // Check if we have more products to fetch
        // Use detected page size or fall back to 250
        const expectedPageSize = detectedPageSize || 250;
        if (data.products.length < expectedPageSize) {
          // If we got fewer than expected products, we've reached the end
          console.log(`📄 [${this.competitor.name}] End of pagination detected: got ${data.products.length} < ${expectedPageSize} products on page ${page}`);
          hasMoreProducts = false;
        } else {
          // Move to next page and add rate limiting
          console.log(`➡️  [${this.competitor.name}] Moving to page ${page + 1} (got full page of ${data.products.length} products)`);
          page++;
          await this.wait(); // Rate limiting between pages
        }
        
        // Safety check to prevent infinite loops
        if (page > 50) {
          console.log(`⚠️  Safety break: Stopped pagination at page ${page} for collection ${collection}`);
          break;
        }
      }

      console.log(`🎉 [${this.competitor.name}] Total products found in collection ${collection}: ${allProducts.length} (across ${page} pages)`);
      return allProducts;
    }, `Scraping collection ${collection}`);
  }

  // Parse HTML for products (fallback when JSON API is not available)
  parseHTMLForProducts(html, collection) {
    try {
      // This is a basic implementation - in practice, you'd want more sophisticated parsing
      // based on the specific structure of different competitor sites
      const products = [];
      
      // Look for common product patterns in HTML
      const productMatches = html.match(/(?:data-product-id|product-item|product-card)[^>]*>[\s\S]*?<\/[^>]+>/gi) || [];
      
      productMatches.forEach((match, index) => {
        try {
          // Extract basic product info from HTML
          const titleMatch = match.match(/<h[23][^>]*[^>]*title[^>]*>([^<]+)</i) || 
                           match.match(/product[_-]title[^>]*>([^<]+)</i) ||
                           match.match(/>([^<]{10,80})</); // Fallback to any text
          
          const priceMatch = match.match(/[\$£€](\d+(?:\.\d{2})?)/);
          const linkMatch = match.match(/href=['"](\/products\/[^'"]+)['"]/i);
          
          if (titleMatch && priceMatch) {
            products.push({
              id: `html_${collection}_${index}`,
              title: titleMatch[1].trim(),
              vendor: this.competitor.name,
              product_type: collection,
              handle: linkMatch ? linkMatch[1].replace('/products/', '') : `product-${index}`,
              variants: [{
                sku: `${collection}-${index}`,
                price: priceMatch[1]
              }],
              available: true,
              images: []
            });
          }
        } catch (parseError) {
          console.error(`Error parsing product from HTML:`, parseError);
        }
      });
      
      console.log(`🔍 Parsed ${products.length} products from HTML`);
      return products;
    } catch (error) {
      console.error('Error parsing HTML for products:', error);
      return [];
    }
  }

  // Process and store scraped products
  async processProducts(products, collectionName) {
    const results = {
      created: 0,
      updated: 0,
      errors: 0,
      errorDetails: []
    };

    for (const product of products) {
      try {
        await this.processProduct(product, collectionName);
        
        // Check if product already exists
        const existing = await withRetry(async (client) => {
          return await client.competitor_products.findUnique({
            where: {
              external_id_competitor_id: {
                external_id: product.id.toString(),
                competitor_id: this.competitor.id
              }
            }
          });
        });

        if (existing) {
          results.updated++;
        } else {
          results.created++;
        }
      } catch (error) {
        results.errors++;
        results.errorDetails.push({
          product_id: product.id,
          error: error.message
        });
        console.error(`Error processing product ${product.id}:`, error);
      }
    }

    return results;
  }

  // Process a single product
  async processProduct(product, collectionName) {
    const variants = product.variants || [];
    const images = product.images || [];
    
    // Get the lowest price from variants
    const prices = variants
      .map(v => parseFloat(v.price))
      .filter(p => !isNaN(p) && p > 0);
    const lowestPrice = prices.length > 0 ? Math.min(...prices) : null;
    
    // Get compare at price from first variant
    const compareAtPrice = variants[0]?.compare_at_price ? 
      parseFloat(variants[0].compare_at_price) : null;

    const productData = {
      external_id: product.id.toString(),
      competitor_id: this.competitor.id,
      title: product.title || '',
      vendor: product.vendor || '',
      product_type: product.product_type || '',
      handle: product.handle || '',
      sku: variants[0]?.sku || '',
      price: lowestPrice,
      compare_at_price: compareAtPrice,
      available: product.available !== false,
      image_url: images[0]?.src || '',
      product_url: `${this.baseUrl}/products/${product.handle}`,
      description: product.body_html || '',
      scraped_at: new Date()
    };

    // Generate embedding for the competitor product
    let embedding = null;
    try {
      embedding = await embeddingsService.generateEmbedding(productData);
    } catch (embeddingError) {
      console.warn(`Failed to generate embedding for competitor product ${product.id}:`, embeddingError.message);
    }

    // Add embedding to product data
    productData.embedding = embedding;

    // Upsert the product with retry logic
    await withRetry(async (client) => {
      return await client.competitor_products.upsert({
      where: {
        external_id_competitor_id: {
          external_id: productData.external_id,
          competitor_id: productData.competitor_id
        }
      },
      create: {
        id: randomUUID(),
        ...productData,
        created_at: new Date()
      },
      update: {
        ...productData
      }
      });
    });

    // Store price history if price changed
    if (lowestPrice) {
      await withRetry(async (client) => {
        // First find the competitor product to get its ID
        const competitorProduct = await client.competitor_products.findUnique({
        where: {
          external_id_competitor_id: {
            external_id: productData.external_id,
            competitor_id: productData.competitor_id
          }
        },
        select: { id: true }
      });

        const lastPrice = competitorProduct ? await client.price_history.findFirst({
          where: {
            competitor_product_id: competitorProduct.id
          },
          orderBy: { recorded_at: 'desc' }
        }) : null;

        // Only store if price is different from last recorded price
        if (!lastPrice || Math.abs(lastPrice.price - lowestPrice) > 0.01) {
          await client.price_history.create({
          data: {
            id: randomUUID(),
            competitor_product_id: competitorProduct.id,
            price: lowestPrice,
            compare_at_price: compareAtPrice,
            available: productData.available,
            recorded_at: new Date()
          }
          });
        }
      });
    }
  }

  // Main scraping method - supports flexible strategies
  async scrape(collections = null) {
    const strategy = this.competitor.scraping_strategy || 'collections';
    console.log(`🎯 Using scraping strategy: ${strategy} for ${this.competitor.name}`);

    const results = {
      competitor: this.competitor.name,
      strategy: strategy,
      sources_scraped: 0,
      total_products: 0,
      created: 0,
      updated: 0,
      errors: 0,
      error_details: []
    };

    try {
      let allProducts = [];

      switch (strategy) {
        case 'collections':
          allProducts = await this.scrapeByCollections(collections);
          break;
        
        case 'url_patterns':
          allProducts = await this.scrapeByUrlPatterns();
          break;
        
        case 'search_terms':
          allProducts = await this.scrapeBySearchTerms();
          break;
        
        default:
          throw new Error(`Unknown scraping strategy: ${strategy}`);
      }

      // Filter out excluded products
      const filteredProducts = this.filterExcludedProducts(allProducts);
      console.log(`🔍 Found ${allProducts.length} products, ${filteredProducts.length} after exclusions`);

      // Process all products
      if (filteredProducts.length > 0) {
        const processingResults = await this.processProducts(filteredProducts, strategy);
        results.total_products = filteredProducts.length;
        results.created = processingResults.created;
        results.updated = processingResults.updated;
        results.errors = processingResults.errors;
        results.error_details = processingResults.errorDetails;
      }

      results.sources_scraped = 1; // One strategy executed
      console.log(`✅ Strategy ${strategy}: ${results.total_products} products, ${results.created} created, ${results.updated} updated, ${results.errors} errors`);

    } catch (error) {
      console.error(`❌ Failed to scrape using strategy ${strategy}:`, error);
      results.errors++;
      results.error_details.push({
        strategy,
        error: error.message
      });
    }

    return results;
  }

  // Scrape using collections strategy
  async scrapeByCollections(collections = null) {
    const collectionsToScrape = collections || this.competitor.collections;
    
    if (!collectionsToScrape || collectionsToScrape.length === 0) {
      throw new Error('No collections specified for collections strategy');
    }

    let allProducts = [];
    
    for (const collection of collectionsToScrape) {
      try {
        console.log(`📦 Scraping collection: ${collection}`);
        const products = await this.scrapeCollection(collection);
        allProducts.push(...products);
        
        // Rate limiting between collections
        if (collectionsToScrape.indexOf(collection) < collectionsToScrape.length - 1) {
          await this.wait();
        }
      } catch (error) {
        console.error(`❌ Failed to scrape collection ${collection}:`, error);
        throw error;
      }
    }

    return allProducts;
  }

  // Scrape using URL patterns strategy
  async scrapeByUrlPatterns() {
    const patterns = this.competitor.url_patterns || [];
    
    if (patterns.length === 0) {
      throw new Error('No URL patterns specified for url_patterns strategy');
    }

    let allProducts = [];
    
    for (const pattern of patterns) {
      try {
        console.log(`🔍 Scraping URL pattern: ${pattern}`);
        
        // Try different approaches based on pattern type
        if (pattern.includes('/collections/')) {
          // Handle collection-style patterns
          const collectionName = this.extractCollectionFromPattern(pattern);
          if (collectionName) {
            console.log(`📦 Extracted collection: ${collectionName}`);
            const products = await this.scrapeCollection(collectionName);
            allProducts.push(...products);
          }
        } else if (pattern.includes('/products/')) {
          // Handle product-style patterns - try to find a collection equivalent
          const collectionName = this.extractCollectionFromPattern(pattern);
          if (collectionName) {
            console.log(`📦 Trying collection equivalent: ${collectionName}`);
            try {
              const products = await this.scrapeCollection(collectionName);
              allProducts.push(...products);
            } catch (error) {
              // If collection doesn't exist, try common brand collections
              console.log(`⚠️  Collection ${collectionName} not found, trying brand-based collections`);
              const brandCollections = await this.tryBrandCollections(collectionName);
              allProducts.push(...brandCollections);
            }
          }
        } else {
          console.log(`⚠️  Unsupported pattern format: ${pattern}`);
        }
        
        await this.wait();
      } catch (error) {
        console.error(`❌ Failed to scrape pattern ${pattern}:`, error);
        // Continue with other patterns instead of throwing
      }
    }

    return allProducts;
  }

  // Try common brand-based collection names
  async tryBrandCollections(brandName) {
    const commonCollectionVariations = [
      brandName.toLowerCase(),
      brandName.toLowerCase().replace('-', ''),
      brandName.toLowerCase() + '-espresso',
      brandName.toLowerCase() + '-machines',
      brandName.toLowerCase() + '-grinders'
    ];

    let allProducts = [];
    
    for (const variation of commonCollectionVariations) {
      try {
        console.log(`🔍 Trying collection variation: ${variation}`);
        const products = await this.scrapeCollection(variation);
        if (products.length > 0) {
          console.log(`✅ Found ${products.length} products in collection: ${variation}`);
          allProducts.push(...products);
          break; // Stop on first successful collection
        }
      } catch (error) {
        // Continue trying other variations
        console.log(`⚠️  Collection ${variation} not found`);
      }
    }

    return allProducts;
  }

  // Scrape using search terms strategy  
  async scrapeBySearchTerms() {
    const searchTerms = this.competitor.search_terms || [];
    
    if (searchTerms.length === 0) {
      throw new Error('No search terms specified for search_terms strategy');
    }

    let allProducts = [];
    
    for (const term of searchTerms) {
      try {
        console.log(`🔍 Searching for: ${term}`);
        const products = await this.searchProducts(term);
        allProducts.push(...products);
        
        await this.wait();
      } catch (error) {
        console.error(`❌ Failed to search for ${term}:`, error);
        // Continue with other terms instead of throwing
      }
    }

    // Remove duplicates based on product ID
    return this.removeDuplicateProducts(allProducts);
  }

  // Extract collection name from URL pattern (simplified)
  extractCollectionFromPattern(pattern) {
    // Handle patterns like '/products/ecm-*' -> 'ecm'
    // This is a simplified implementation
    const match = pattern.match(/\/(?:collections|products)\/([^-*]+)/);
    return match ? match[1] : null;
  }

  // Search for products by term (comprehensive implementation)
  async searchProducts(term) {
    console.log(`🔍 Searching for products matching: ${term}`);
    
    let allProducts = [];
    
    // Strategy 1: Try Shopify search API (if available)
    try {
      const searchProducts = await this.searchViaShopifyAPI(term);
      if (searchProducts.length > 0) {
        console.log(`✅ Found ${searchProducts.length} products via Shopify search API for: ${term}`);
        allProducts.push(...searchProducts);
        return allProducts; // Return immediately if search API works
      }
    } catch (error) {
      console.log(`⚠️  Shopify search API failed for ${term}:`, error.message);
    }

    // Strategy 2: Try search term as collection name variations
    const potentialCollections = [
      term.toLowerCase(),
      term.toLowerCase().replace(/\s+/g, '-'),
      term.toLowerCase().replace(/\s+/g, ''),
      term.toLowerCase().split(' ')[0], // First word only
      // Brand-specific variations
      term.toLowerCase() + '-espresso',
      term.toLowerCase() + '-machines', 
      term.toLowerCase() + '-grinders',
      term.toLowerCase() + '-coffee'
    ];

    for (const collectionName of potentialCollections) {
      try {
        console.log(`🔍 Trying search term as collection: ${collectionName}`);
        const products = await this.scrapeCollection(collectionName);
        if (products.length > 0) {
          console.log(`✅ Found ${products.length} products for search term "${term}" via collection "${collectionName}"`);
          allProducts.push(...products);
          break; // Stop on first successful match
        }
      } catch (error) {
        // Continue trying other variations
      }
    }

    // Strategy 3: Crawl all products and filter by search term (expensive fallback)
    if (allProducts.length === 0) {
      try {
        console.log(`🔍 Attempting full product crawl and filter for: ${term}`);
        const crawledProducts = await this.crawlAndFilterProducts(term);
        allProducts.push(...crawledProducts);
      } catch (error) {
        console.log(`⚠️  Product crawling failed for ${term}:`, error.message);
      }
    }

    if (allProducts.length === 0) {
      console.log(`⚠️  No products found for search term: ${term}`);
    }

    return allProducts;
  }

  // Search via Shopify search API (if available)
  async searchViaShopifyAPI(term) {
    const searchUrl = `${this.baseUrl}/search.json?q=${encodeURIComponent(term)}&type=product`;
    
    return await this.withRetry(async () => {
      console.log(`🔍 Shopify API search: ${searchUrl}`);
      
      const response = await fetch(searchUrl, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (compatible; PriceMonitor/1.0)',
          'Accept': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`Search API returned ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      
      if (data.results && Array.isArray(data.results)) {
        return data.results;
      } else if (data.products && Array.isArray(data.products)) {
        return data.products;
      } else {
        throw new Error('No search results found in response');
      }
    }, `Shopify search for "${term}"`);
  }

  // Crawl products from common paths and filter by search term
  async crawlAndFilterProducts(term) {
    console.log(`🕷️  Crawling products and filtering by: ${term}`);
    
    // Common product listing paths to try
    const commonPaths = [
      'products',      // /products.json
      'all',           // /collections/all/products.json  
      'all-products',  // /collections/all-products/products.json
      'catalog',       // /collections/catalog/products.json
      'shop'           // /collections/shop/products.json
    ];

    let allProducts = [];
    const termLower = term.toLowerCase();
    
    for (const path of commonPaths) {
      try {
        console.log(`🔍 Crawling path: ${path}`);
        let products = [];
        
        if (path === 'products') {
          // Try direct products endpoint with pagination
          let page = 1;
          let hasMoreProducts = true;
          
          while (hasMoreProducts && page <= 10) { // Limit to 10 pages for direct products
            const url = `${this.baseUrl}/products.json?limit=250&page=${page}`;
            const response = await fetch(url);
            if (response.ok) {
              const data = await response.json();
              const pageProducts = data.products || [];
              products.push(...pageProducts);
              
              if (pageProducts.length < 250) {
                hasMoreProducts = false;
              } else {
                page++;
                await this.wait(); // Rate limiting
              }
            } else {
              break;
            }
          }
          console.log(`📦 Found ${products.length} products via direct products endpoint (${page} pages)`);
        } else {
          // Try collection-based endpoint
          products = await this.scrapeCollection(path);
        }

        // Filter products by search term
        const matchingProducts = products.filter(product => {
          const title = (product.title || '').toLowerCase();
          const vendor = (product.vendor || '').toLowerCase();
          const type = (product.product_type || '').toLowerCase();
          const tags = (product.tags || []).join(' ').toLowerCase();
          
          return title.includes(termLower) || 
                 vendor.includes(termLower) || 
                 type.includes(termLower) ||
                 tags.includes(termLower);
        });

        if (matchingProducts.length > 0) {
          console.log(`✅ Found ${matchingProducts.length} matching products in ${path}`);
          allProducts.push(...matchingProducts);
          break; // Stop on first successful path
        }

        await this.wait(); // Rate limiting
      } catch (error) {
        console.log(`⚠️  Failed to crawl ${path}:`, error.message);
        continue;
      }
    }

    return allProducts;
  }

  // Filter out excluded products
  filterExcludedProducts(products) {
    const excludePatterns = this.competitor.exclude_patterns || [];
    
    if (excludePatterns.length === 0) {
      return products;
    }

    return products.filter(product => {
      const productUrl = `/products/${product.handle}`;
      const productTitle = product.title?.toLowerCase() || '';
      
      // Check if product matches any exclude pattern
      const shouldExclude = excludePatterns.some(pattern => {
        const regex = new RegExp(pattern.replace(/\*/g, '.*'), 'i');
        return regex.test(productUrl) || regex.test(productTitle);
      });

      return !shouldExclude;
    });
  }

  // Remove duplicate products based on ID
  removeDuplicateProducts(products) {
    const seen = new Set();
    return products.filter(product => {
      if (seen.has(product.id)) {
        return false;
      }
      seen.add(product.id);
      return true;
    });
  }
}

// Start scraping job for a competitor
router.post('/start-scrape', async (req, res) => {
  try {
    console.log('🔍 Start scrape request received:', req.body);
    const { competitor_id, collections } = req.body;
    
    if (!competitor_id) {
      console.log('❌ No competitor_id provided');
      return res.status(400).json({ error: 'competitor_id is required' });
    }

    console.log('🔍 Looking up competitor:', competitor_id);
    // Get competitor details
    const competitor = await prisma.competitors.findUnique({
      where: { id: competitor_id }
    });

    if (!competitor) {
      console.log('❌ Competitor not found');
      return res.status(404).json({ error: 'Competitor not found' });
    }

    if (!competitor.is_active) {
      console.log('❌ Competitor is not active');
      return res.status(400).json({ error: 'Competitor is not active' });
    }

    console.log('✅ Competitor found:', competitor.name);
    console.log('🔍 Creating scrape job...');

    // Create scrape job
    const scrapeJob = await prisma.scrape_jobs.create({
      data: {
        id: randomUUID(),
        competitor_id,
        collections: collections || competitor.collections,
        status: 'running',
        started_at: new Date()
      }
    });

    console.log('✅ Scrape job created:', scrapeJob.id);

    // Start scraping in background (don't await)
    console.log('🚀 Starting background scrape...');
    setImmediate(() => {
      scrapeCompetitorInBackground(competitor, scrapeJob, collections)
        .catch(error => {
          console.error('❌ Background scrape error:', error);
        });
    });

    console.log('✅ Returning success response');
    res.json({
      message: 'Scraping job started',
      job_id: scrapeJob.id,
      competitor: competitor.name,
      collections: collections || competitor.collections
    });
  } catch (error) {
    console.error('❌ Error starting scrape job:', error);
    res.status(500).json({ error: 'Failed to start scraping job', details: error.message });
  }
});

// Background scraping function
async function scrapeCompetitorInBackground(competitor, scrapeJob, collections = null) {
  const startTime = new Date();
  
  try {
    console.log(`🚀 Starting background scrape for ${competitor.name}`);
    
    const scraper = new CompetitorScraper(competitor);
    const results = await scraper.scrape(collections);
    
    const endTime = new Date();
    const durationSeconds = Math.round((endTime - startTime) / 1000);

    // Update scrape job with results
    await prisma.scrape_jobs.update({
      where: { id: scrapeJob.id },
      data: {
        status: 'completed',
        products_found: results.total_products,
        products_created: results.created,  
        products_updated: results.updated,
        errors: results.errors > 0 ? JSON.stringify(results.error_details) : null,
        completed_at: endTime,
        duration_seconds: durationSeconds
      }
    });

    // Update competitor last scraped time
    await prisma.competitors.update({
      where: { id: competitor.id },
      data: { 
        last_scraped_at: endTime,
        total_products: results.created + results.updated
      }
    });

    console.log(`✅ Completed scrape job ${scrapeJob.id}: ${results.total_products} products, ${results.created} created, ${results.updated} updated, ${results.errors} errors (${durationSeconds}s)`);
    
  } catch (error) {
    console.error(`❌ Scrape job ${scrapeJob.id} failed:`, error);
    
    const endTime = new Date();
    const durationSeconds = Math.round((endTime - startTime) / 1000);
    
    await prisma.scrape_jobs.update({
      where: { id: scrapeJob.id },
      data: {
        status: 'failed',
        errors: JSON.stringify([{ error: error.message }]),
        completed_at: endTime,
        duration_seconds: durationSeconds
      }
    });
  }
}

// Get scrape job status
router.get('/job/:jobId/status', async (req, res) => {
  try {
    const { jobId } = req.params;
    
    const job = await prisma.scrape_jobs.findUnique({
      where: { id: jobId },
      include: {
        competitors: {
          select: { name: true, domain: true }
        }
      }
    });

    if (!job) {
      return res.status(404).json({ error: 'Scrape job not found' });
    }

    res.json({
      id: job.id,
      competitor: job.competitors,
      status: job.status,
      collections: job.collections,
      products_found: job.products_found,
      products_created: job.products_created,
      products_updated: job.products_updated,
      errors: job.errors ? JSON.parse(job.errors) : null,
      started_at: job.started_at,
      completed_at: job.completed_at,
      duration_seconds: job.duration_seconds,
      created_at: job.created_at
    });
  } catch (error) {
    console.error('Error fetching job status:', error);
    res.status(500).json({ error: 'Failed to fetch job status' });
  }
});

// Get recent scrape jobs
router.get('/jobs', async (req, res) => {
  try {
    const { limit = 20, status, competitor_id } = req.query;
    
    const where = {};
    if (status) where.status = status;
    if (competitor_id) where.competitor_id = competitor_id;

    const jobs = await prisma.scrape_jobs.findMany({
      where,
      take: parseInt(limit),
      orderBy: { created_at: 'desc' },
      include: {
        competitors: {
          select: { name: true, domain: true }
        }
      }
    });

    const formattedJobs = jobs.map(job => ({
      id: job.id,
      competitor: job.competitors,
      status: job.status,
      collections: job.collections,
      products_found: job.products_found,
      products_created: job.products_created,
      products_updated: job.products_updated,
      error_count: job.errors ? JSON.parse(job.errors).length : 0,
      started_at: job.started_at,
      completed_at: job.completed_at,
      duration_seconds: job.duration_seconds,
      created_at: job.created_at
    }));

    res.json({ jobs: formattedJobs });
  } catch (error) {
    console.error('Error fetching scrape jobs:', error);
    res.status(500).json({ error: 'Failed to fetch scrape jobs' });
  }
});

// Test competitor connection
router.post('/test-connection', async (req, res) => {
  try {
    const { competitor_id, collection } = req.body;
    
    const competitor = await prisma.competitors.findUnique({
      where: { id: competitor_id }
    });

    if (!competitor) {
      return res.status(404).json({ error: 'Competitor not found' });
    }

    const testCollection = collection || competitor.collections[0];
    if (!testCollection) {
      return res.status(400).json({ error: 'No collection specified for testing' });
    }

    const scraper = new CompetitorScraper(competitor);
    
    try {
      const products = await scraper.scrapeCollection(testCollection);
      
      res.json({
        success: true,
        competitor: competitor.name,
        collection: testCollection,
        products_found: products.length,
        sample_products: products.slice(0, 3).map(p => ({
          id: p.id,
          title: p.title,
          vendor: p.vendor,
          price: p.variants[0]?.price
        }))
      });
    } catch (scrapeError) {
      res.status(400).json({
        success: false,
        competitor: competitor.name,
        collection: testCollection,
        error: scrapeError.message
      });
    }
  } catch (error) {
    console.error('Error testing connection:', error);
    res.status(500).json({ error: 'Failed to test connection' });
  }
});

// Bulk scrape multiple competitors
router.post('/bulk-scrape', async (req, res) => {
  try {
    const { competitor_ids, collections } = req.body;
    
    if (!competitor_ids || !Array.isArray(competitor_ids) || competitor_ids.length === 0) {
      return res.status(400).json({ error: 'competitor_ids array is required' });
    }

    // Get active competitors
    const competitors = await prisma.competitors.findMany({
      where: {
        id: { in: competitor_ids },
        is_active: true
      }
    });

    if (competitors.length === 0) {
      return res.status(404).json({ error: 'No active competitors found' });
    }

    const jobs = [];

    // Start scraping jobs for each competitor
    for (const competitor of competitors) {
      try {
        const scrapeJob = await prisma.scrape_jobs.create({
          data: {
            id: randomUUID(),
            competitor_id: competitor.id,
            collections: collections || competitor.collections,
            status: 'running',
            started_at: new Date(),
            updated_at: new Date()
          }
        });

        // Start scraping in background
        scrapeCompetitorInBackground(competitor, scrapeJob, collections);
        
        jobs.push({
          job_id: scrapeJob.id,
          competitor: competitor.name,
          collections: collections || competitor.collections
        });
      } catch (error) {
        console.error(`Error starting job for ${competitor.name}:`, error);
      }
    }

    res.json({
      message: `Started ${jobs.length} scraping jobs`,
      jobs: jobs
    });
  } catch (error) {
    console.error('Error starting bulk scrape:', error);
    res.status(500).json({ error: 'Failed to start bulk scraping' });
  }
});

// Scrape all active competitors
router.post('/scrape-all', async (req, res) => {
  try {
    const { collections } = req.body;

    // Get all active competitors
    const competitors = await prisma.competitors.findMany({
      where: { is_active: true }
    });

    if (competitors.length === 0) {
      return res.status(404).json({ error: 'No active competitors found' });
    }

    const jobs = [];

    // Start scraping jobs for all active competitors
    for (const competitor of competitors) {
      try {
        const scrapeJob = await prisma.scrape_jobs.create({
          data: {
            id: randomUUID(),
            competitor_id: competitor.id,
            collections: collections || competitor.collections,
            status: 'running',
            started_at: new Date(),
            updated_at: new Date()
          }
        });

        // Start scraping in background
        scrapeCompetitorInBackground(competitor, scrapeJob, collections);
        
        jobs.push({
          job_id: scrapeJob.id,
          competitor: competitor.name,
          collections: collections || competitor.collections
        });
      } catch (error) {
        console.error(`Error starting job for ${competitor.name}:`, error);
      }
    }

    res.json({
      message: `Started scraping all ${jobs.length} active competitors`,
      jobs: jobs
    });
  } catch (error) {
    console.error('Error starting scrape all:', error);
    res.status(500).json({ error: 'Failed to start scraping all competitors' });
  }
});

export default router;