import express from 'express';
import { db } from '../../config/database.js';

const prisma = db;
import embeddingsService from '../../services/embeddings-service.js';

const router = express.Router();

// Shopify GraphQL client configuration
const SHOPIFY_ADMIN_URL = process.env.SHOPIFY_SHOP_URL + '/admin/api/2024-01/graphql.json';
const SHOPIFY_ACCESS_TOKEN = process.env.SHOPIFY_ACCESS_TOKEN;

// GraphQL query to fetch products by vendor (active products only)
const PRODUCTS_BY_VENDOR_QUERY = `
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
`;

// Helper function to make GraphQL requests to Shopify
async function shopifyGraphQL(query, variables = {}) {
  const response = await fetch(SHOPIFY_ADMIN_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Shopify-Access-Token': SHOPIFY_ACCESS_TOKEN,
    },
    body: JSON.stringify({
      query,
      variables,
    }),
  });

  if (!response.ok) {
    throw new Error(`Shopify API error: ${response.status} ${response.statusText}`);
  }

  const data = await response.json();
  
  if (data.errors) {
    throw new Error(`GraphQL errors: ${JSON.stringify(data.errors)}`);
  }

  return data.data;
}

// Sync iDC products for monitored brands
router.post('/sync-idc-products', async (req, res) => {
  try {
    const { brands, force = false } = req.body;
    
    // Get monitored brands if none specified
    let brandsToSync = brands;
    if (!brandsToSync) {
      const monitoredBrands = await prisma.monitored_brands.findMany({
        where: { is_active: true }
      });
      brandsToSync = monitoredBrands.map(b => b.brand_name);
    }
    
    if (brandsToSync.length === 0) {
      return res.status(400).json({ 
        error: 'No brands specified and no active monitored brands found' 
      });
    }

    let totalSynced = 0;
    let totalErrors = 0;
    const results = [];

    for (const brandName of brandsToSync) {
      try {
        console.log(`🔄 Syncing products for brand: ${brandName}`);
        
        // Find or create monitored brand
        let monitoredBrand = await prisma.monitored_brands.findUnique({
          where: { brand_name: brandName }
        });
        
        if (!monitoredBrand) {
          monitoredBrand = await prisma.monitored_brands.create({
            data: { 
              brand_name: brandName, 
              is_active: true,
              updated_at: new Date()
            }
          });
        }

        // Delete existing products for this brand to replace with fresh data
        const deletedCount = await prisma.idc_products.deleteMany({
          where: { vendor: brandName }
        });
        console.log(`🗑️  Deleted ${deletedCount.count} existing products for ${brandName}`);

        let hasNextPage = true;
        let cursor = null;
        let brandProductCount = 0;
        let brandErrorCount = 0;

        while (hasNextPage) {
          try {
            const data = await shopifyGraphQL(PRODUCTS_BY_VENDOR_QUERY, {
              vendor: `vendor:${brandName} AND status:active`,
              first: 50,
              after: cursor
            });

            const { products } = data;
            hasNextPage = products.pageInfo.hasNextPage;
            cursor = products.pageInfo.endCursor;

            for (const edge of products.edges) {
              const product = edge.node;
              
              // Skip inactive products or those without published date
              if (product.status !== 'ACTIVE' || !product.publishedAt) {
                continue;
              }
              
              try {
                // Extract product data
                const firstVariant = product.variants.edges[0]?.node;
                const firstImage = product.images.edges[0]?.node;
                
                // Skip products without available variants or with no price
                if (!firstVariant?.availableForSale || !firstVariant?.price || parseFloat(firstVariant.price) <= 0) {
                  continue;
                }
                
                const productData = {
                  id: product.id, // Use shopify_id as the primary key id
                  shopify_id: product.id,
                  title: product.title,
                  vendor: product.vendor,
                  product_type: product.productType,
                  handle: product.handle,
                  description: product.description,
                  image_url: firstImage?.url,
                  sku: firstVariant?.sku,
                  price: firstVariant?.price ? parseFloat(firstVariant.price) : null,
                  compare_at_price: firstVariant?.compareAtPrice ? parseFloat(firstVariant.compareAtPrice) : null,
                  available: firstVariant?.availableForSale || false,
                  inventory_quantity: firstVariant?.inventoryQuantity || 0,
                  brand_id: monitoredBrand.id,
                  last_synced_at: new Date(),
                  updated_at: new Date()
                };

                // Generate embedding for the product
                let embedding = null;
                try {
                  embedding = await embeddingsService.generateEmbedding(productData);
                } catch (embeddingError) {
                  console.warn(`Failed to generate embedding for ${product.id}:`, embeddingError.message);
                }

                // Add embedding to product data
                productData.embedding = embedding;

                // Upsert product (handles both create and update)
                await prisma.idc_products.upsert({
                  where: { shopify_id: product.id },
                  create: productData,
                  update: productData
                });

                brandProductCount++;
              } catch (productError) {
                console.error(`Error syncing product ${product.id}:`, productError);
                brandErrorCount++;
              }
            }
          } catch (pageError) {
            console.error(`Error fetching page for ${brandName}:`, pageError);
            brandErrorCount++;
            break;
          }
        }

        results.push({
          brand: brandName,
          products_synced: brandProductCount,
          errors: brandErrorCount,
          success: brandErrorCount === 0
        });

        totalSynced += brandProductCount;
        totalErrors += brandErrorCount;

        console.log(`✅ Synced ${brandProductCount} products for ${brandName} (${brandErrorCount} errors)`);
        
        // Rate limiting - wait between brands
        await new Promise(resolve => setTimeout(resolve, 1000));
        
      } catch (brandError) {
        console.error(`Error syncing brand ${brandName}:`, brandError);
        results.push({
          brand: brandName,
          products_synced: 0,
          errors: 1,
          success: false,
          error: brandError.message
        });
        totalErrors++;
      }
    }

    res.json({
      message: `Sync completed: ${totalSynced} products synced, ${totalErrors} errors`,
      total_synced: totalSynced,
      total_errors: totalErrors,
      results
    });

  } catch (error) {
    console.error('Error syncing iDC products:', error);
    res.status(500).json({ error: 'Failed to sync iDC products' });
  }
});

// Get sync status
router.get('/sync-status', async (req, res) => {
  try {
    const stats = await Promise.all([
      // Total iDC products by brand
      prisma.idc_products.groupBy({
        by: ['vendor'],
        _count: { id: true },
        orderBy: { _count: { id: 'desc' } }
      }),
      
      // Last sync times by brand
      prisma.monitored_brands.findMany({
        include: {
          idc_products: {
            select: { last_synced_at: true },
            orderBy: { last_synced_at: 'desc' }
            // No limit - get all products sync times for accurate brand status
          }
        }
      }),
      
      // Total counts
      prisma.idc_products.count(),
      prisma.monitored_brands.count({ where: { is_active: true } })
    ]);

    const [productsByBrand, brandsWithLastSync, totalProducts, activeBrands] = stats;

    const brandStats = brandsWithLastSync.map(brand => ({
      brand_name: brand.brand_name,
      is_active: brand.is_active,
      product_count: productsByBrand.find(p => p.vendor === brand.brand_name)?._count.id || 0,
      last_synced_at: brand.idc_products[0]?.last_synced_at || null,
      needs_sync: !brand.idc_products[0]?.last_synced_at || 
                  (new Date() - new Date(brand.idc_products[0].last_synced_at)) > 24 * 60 * 60 * 1000 // 24 hours
    }));

    res.json({
      total_products: totalProducts,
      active_brands: activeBrands,
      brand_stats: brandStats,
      last_updated: new Date().toISOString()
    });
  } catch (error) {
    console.error('Error fetching sync status:', error);
    res.status(500).json({ error: 'Failed to fetch sync status' });
  }
});

// Get iDC products with filtering
router.get('/idc-products', async (req, res) => {
  try {
    const { 
      brand, 
      search, 
      available, 
      page = 1, 
      limit = 50 
    } = req.query;

    const skip = (parseInt(page) - 1) * parseInt(limit);
    const where = {};

    if (brand) {
      where.vendor = brand;
    }

    if (search) {
      where.OR = [
        { title: { contains: search, mode: 'insensitive' } },
        { sku: { contains: search, mode: 'insensitive' } }
      ];
    }

    if (available !== undefined) {
      where.available = available === 'true';
    }

    const [products, totalCount] = await Promise.all([
      prisma.idc_products.findMany({
        where,
        skip,
        take: parseInt(limit),
        include: {
          monitored_brands: true
        },
        orderBy: { last_synced_at: 'desc' }
      }),
      prisma.idc_products.count({ where })
    ]);

    res.json({
      products,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: totalCount,
        total_pages: Math.ceil(totalCount / parseInt(limit)),
        has_next: skip + parseInt(limit) < totalCount,
        has_prev: parseInt(page) > 1
      }
    });
  } catch (error) {
    console.error('Error fetching iDC products:', error);
    res.status(500).json({ error: 'Failed to fetch iDC products' });
  }
});

// Manual sync trigger for specific brand
router.post('/sync-brand/:brandName', async (req, res) => {
  try {
    const { brandName } = req.params;
    
    // Trigger sync for single brand
    const syncResponse = await fetch(`${req.protocol}://${req.get('host')}/api/price-monitor/shopify-sync/sync-idc-products`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        brands: [brandName]
      })
    });

    const syncResult = await syncResponse.json();
    res.json(syncResult);
  } catch (error) {
    console.error(`Error syncing brand ${req.params.brandName}:`, error);
    res.status(500).json({ error: 'Failed to sync brand' });
  }
});

// Auto-sync all monitored brands (for scheduled tasks)
router.post('/auto-sync', async (req, res) => {
  try {
    console.log('🔄 Starting auto-sync for all monitored brands...');
    
    // Get all active monitored brands that need syncing (older than 24 hours or never synced)
    const brandsNeedingSync = await prisma.monitored_brands.findMany({
      where: {
        is_active: true,
        OR: [
          {
            idc_products: {
              none: {}
            }
          },
          {
            idc_products: {
              every: {
                last_synced_at: {
                  lt: new Date(Date.now() - 24 * 60 * 60 * 1000) // 24 hours ago
                }
              }
            }
          }
        ]
      }
    });

    if (brandsNeedingSync.length === 0) {
      return res.json({
        message: 'No brands need syncing at this time',
        brands_checked: 0,
        brands_synced: 0
      });
    }

    const brandNames = brandsNeedingSync.map(b => b.brand_name);
    console.log(`📦 Found ${brandNames.length} brands needing sync: ${brandNames.join(', ')}`);

    // Trigger sync for brands that need it
    const syncResponse = await fetch(`${req.protocol}://${req.get('host')}/api/price-monitor/shopify-sync/sync-idc-products`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        brands: brandNames
      })
    });

    const syncResult = await syncResponse.json();
    
    res.json({
      message: 'Auto-sync completed',
      brands_checked: brandsNeedingSync.length,
      brands_synced: brandNames.length,
      sync_results: syncResult
    });
  } catch (error) {
    console.error('Error during auto-sync:', error);
    res.status(500).json({ error: 'Failed to perform auto-sync' });
  }
});

// Get products by brand with enhanced filtering
router.get('/products-by-brand/:brandName', async (req, res) => {
  try {
    const { brandName } = req.params;
    const { 
      search, 
      available, 
      price_min, 
      price_max,
      page = 1, 
      limit = 50 
    } = req.query;

    const skip = (parseInt(page) - 1) * parseInt(limit);
    const where = { vendor: brandName };

    if (search) {
      where.OR = [
        { title: { contains: search, mode: 'insensitive' } },
        { sku: { contains: search, mode: 'insensitive' } },
        { description: { contains: search, mode: 'insensitive' } }
      ];
    }

    if (available !== undefined) {
      where.available = available === 'true';
    }

    if (price_min || price_max) {
      where.price = {};
      if (price_min) where.price.gte = parseFloat(price_min);
      if (price_max) where.price.lte = parseFloat(price_max);
    }

    const [products, totalCount, brandStats] = await Promise.all([
      prisma.idc_products.findMany({
        where,
        skip,
        take: parseInt(limit),
        include: {
          monitored_brands: true,
          _count: {
            select: {
              product_matches: true
            }
          }
        },
        orderBy: [
          { available: 'desc' },  // Available products first
          { price: 'asc' }        // Then by price
        ]
      }),
      prisma.idc_products.count({ where }),
      // Get brand statistics
      prisma.idc_products.aggregate({
        where: { vendor: brandName },
        _count: { id: true },
        _avg: { price: true },
        _min: { price: true },
        _max: { price: true }
      })
    ]);

    res.json({
      brand: brandName,
      products,
      brand_stats: {
        total_products: brandStats._count.id,
        avg_price: brandStats._avg.price,
        min_price: brandStats._min.price,
        max_price: brandStats._max.price,
        available_count: await prisma.idc_products.count({
          where: { vendor: brandName, available: true }
        })
      },
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: totalCount,
        total_pages: Math.ceil(totalCount / parseInt(limit)),
        has_next: skip + parseInt(limit) < totalCount,
        has_prev: parseInt(page) > 1
      }
    });
  } catch (error) {
    console.error(`Error fetching products for brand ${req.params.brandName}:`, error);
    res.status(500).json({ error: 'Failed to fetch brand products' });
  }
});

// Health check for Shopify connection
router.get('/health', async (req, res) => {
  try {
    // Test Shopify connection with a simple query
    const testQuery = `
      query {
        shop {
          name
          url
        }
      }
    `;

    const data = await shopifyGraphQL(testQuery);
    
    res.json({
      status: 'healthy',
      shopify_connected: true,
      shop: data.shop,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Shopify health check failed:', error);
    res.status(500).json({
      status: 'unhealthy',
      shopify_connected: false,
      error: error.message,
      timestamp: new Date().toISOString()
    });
  }
});

export default router;