import express from 'express';
import prisma from '../../lib/prisma.js';
import embeddingsService from '../../services/embeddings-service.js';

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

  // Scrape a single collection - enhanced to handle different site types
  async scrapeCollection(collection) {
    return await this.withRetry(async () => {
      // Try Shopify JSON API first (most common for coffee retailers)
      let url = `${this.baseUrl}/collections/${collection}/products.json`;
      console.log(`🔍 Scraping: ${url}`);

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

      // If Shopify JSON fails, try alternative approaches
      if (!response.ok) {
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

      const data = await response.json();
      
      if (!data.products || !Array.isArray(data.products)) {
        throw new Error('Invalid response format - no products array');
      }

      console.log(`✅ Found ${data.products.length} products in collection ${collection}`);
      return data.products;
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
        const existing = await prisma.competitor_products.findUnique({
          where: {
            external_id_competitor_id: {
              external_id: product.id.toString(),
              competitor_id: this.competitor.id
            }
          }
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
      scraped_at: new Date(),
      updated_at: new Date()
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

    // Upsert the product
    await prisma.competitor_products.upsert({
      where: {
        external_id_competitor_id: {
          external_id: productData.external_id,
          competitor_id: productData.competitor_id
        }
      },
      create: {
        ...productData,
        created_at: new Date()
      },
      update: productData
    });

    // Store price history if price changed
    if (lowestPrice) {
      const lastPrice = await prisma.price_history.findFirst({
        where: {
          competitor_product: {
            external_id: productData.external_id,
            competitor_id: productData.competitor_id
          }
        },
        orderBy: { recorded_at: 'desc' }
      });

      // Only store if price is different from last recorded price
      if (!lastPrice || Math.abs(lastPrice.price - lowestPrice) > 0.01) {
        await prisma.price_history.create({
          data: {
            competitor_product_id: (await prisma.competitor_products.findUnique({
              where: {
                external_id_competitor_id: {
                  external_id: productData.external_id,
                  competitor_id: productData.competitor_id
                }
              }
            })).id,
            price: lowestPrice,
            compare_at_price: compareAtPrice,
            available: productData.available,
            recorded_at: new Date()
          }
        });
      }
    }
  }

  // Main scraping method
  async scrape(collections = null) {
    const collectionsToScrape = collections || this.competitor.collections;
    
    if (!collectionsToScrape || collectionsToScrape.length === 0) {
      throw new Error('No collections specified for scraping');
    }

    const results = {
      competitor: this.competitor.name,
      collections_scraped: 0,
      total_products: 0,
      created: 0,
      updated: 0,
      errors: 0,
      error_details: []
    };

    for (const collection of collectionsToScrape) {
      try {
        console.log(`📦 Scraping collection: ${collection} for ${this.competitor.name}`);
        
        const products = await this.scrapeCollection(collection);
        const collectionResults = await this.processProducts(products, collection);
        
        results.collections_scraped++;
        results.total_products += products.length;
        results.created += collectionResults.created;
        results.updated += collectionResults.updated;
        results.errors += collectionResults.errors;
        results.error_details.push(...collectionResults.errorDetails);

        console.log(`✅ Collection ${collection}: ${products.length} products, ${collectionResults.created} created, ${collectionResults.updated} updated, ${collectionResults.errors} errors`);
        
        // Rate limiting between collections
        if (collectionsToScrape.indexOf(collection) < collectionsToScrape.length - 1) {
          await this.wait();
        }
      } catch (error) {
        console.error(`❌ Failed to scrape collection ${collection}:`, error);
        results.errors++;
        results.error_details.push({
          collection,
          error: error.message
        });
      }
    }

    return results;
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
        competitor: {
          select: { name: true, domain: true }
        }
      }
    });

    if (!job) {
      return res.status(404).json({ error: 'Scrape job not found' });
    }

    res.json({
      id: job.id,
      competitor: job.competitor,
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
        competitor: {
          select: { name: true, domain: true }
        }
      }
    });

    const formattedJobs = jobs.map(job => ({
      id: job.id,
      competitor: job.competitor,
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
            competitor_id: competitor.id,
            collections: collections || competitor.collections,
            status: 'running',
            started_at: new Date()
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
            competitor_id: competitor.id,
            collections: collections || competitor.collections,
            status: 'running',
            started_at: new Date()
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