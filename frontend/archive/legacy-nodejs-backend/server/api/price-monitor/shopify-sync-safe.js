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

// SAFE sync that preserves manual matches
router.post('/sync-idc-products-safe', async (req, res) => {
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
      return res.status(400).json({ error: 'No brands to sync' });
    }

    console.log(`🔄 Starting SAFE sync for ${brandsToSync.length} brands: ${brandsToSync.join(', ')}`);
    
    const results = {
      brands_synced: [],
      total_products_created: 0,
      total_products_updated: 0,
      total_products_deactivated: 0,
      manual_matches_preserved: 0,
      errors: []
    };

    for (const brandName of brandsToSync) {
      console.log(`\n📦 Syncing brand: ${brandName}`);
      
      try {
        // Ensure brand exists in monitored brands
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

        // CRITICAL CHANGE: Get all manual matches for this brand BEFORE any deletes
        const manualMatchesForBrand = await prisma.product_matches.findMany({
          where: {
            idc_products: { vendor: brandName },
            is_manual_match: true
          },
          include: {
            idc_products: true,
            competitor_products: true
          }
        });
        
        console.log(`🔒 Found ${manualMatchesForBrand.length} manual matches to preserve for ${brandName}`);
        results.manual_matches_preserved += manualMatchesForBrand.length;

        // Track which products we've seen in this sync
        const seenProductIds = new Set();
        
        let hasNextPage = true;
        let cursor = null;
        let brandProductCount = 0;
        let brandUpdatedCount = 0;
        let brandCreatedCount = 0;

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
                  shopify_id: product.id,
                  title: product.title,
                  vendor: product.vendor,
                  product_type: product.productType || null,
                  handle: product.handle,
                  sku: firstVariant.sku || null,
                  price: parseFloat(firstVariant.price),
                  compare_at_price: firstVariant.compareAtPrice ? parseFloat(firstVariant.compareAtPrice) : null,
                  available: firstVariant.availableForSale,
                  inventory_quantity: firstVariant.inventoryQuantity || 0,
                  image_url: firstImage?.url || null,
                  description: product.description || null,
                  last_synced_at: new Date(),
                  updated_at: new Date(),
                  brand_id: monitoredBrand.id
                };

                // Check if product exists
                const existingProduct = await prisma.idc_products.findUnique({
                  where: { shopify_id: product.id }
                });

                if (existingProduct) {
                  // Update existing product
                  await prisma.idc_products.update({
                    where: { id: existingProduct.id },
                    data: productData
                  });
                  brandUpdatedCount++;
                } else {
                  // Create new product
                  await prisma.idc_products.create({
                    data: {
                      id: product.id, // Use Shopify ID as our ID
                      ...productData
                    }
                  });
                  brandCreatedCount++;
                }

                seenProductIds.add(product.id);
                brandProductCount++;
                
              } catch (productError) {
                console.error(`❌ Error processing product ${product.title}:`, productError);
                results.errors.push({
                  brand: brandName,
                  product: product.title,
                  error: productError.message
                });
              }
            }
            
          } catch (pageError) {
            console.error(`❌ Error fetching page for ${brandName}:`, pageError);
            results.errors.push({
              brand: brandName,
              error: pageError.message
            });
            hasNextPage = false;
          }
        }

        // CRITICAL: Instead of deleting, mark products as unavailable
        const productsToDeactivate = await prisma.idc_products.findMany({
          where: {
            vendor: brandName,
            id: { notIn: Array.from(seenProductIds) }
          },
          select: { id: true }
        });

        if (productsToDeactivate.length > 0) {
          await prisma.idc_products.updateMany({
            where: {
              id: { in: productsToDeactivate.map(p => p.id) }
            },
            data: {
              available: false,
              last_synced_at: new Date()
            }
          });
          
          console.log(`📴 Marked ${productsToDeactivate.length} products as unavailable (not deleted!)`);
          results.total_products_deactivated += productsToDeactivate.length;
        }

        // Update embeddings for new/updated products
        const productsNeedingEmbeddings = await prisma.idc_products.findMany({
          where: {
            vendor: brandName,
            OR: [
              { embedding: null },
              { embedding: '' }
            ]
          }
        });

        console.log(`🧮 Generating embeddings for ${productsNeedingEmbeddings.length} products...`);
        
        for (const product of productsNeedingEmbeddings) {
          try {
            const textToEmbed = `${product.title} ${product.vendor} ${product.product_type || ''} ${product.description || ''}`.trim();
            const embedding = await embeddingsService.generateEmbedding(textToEmbed);
            
            await prisma.idc_products.update({
              where: { id: product.id },
              data: { 
                embedding: JSON.stringify(embedding),
                updated_at: new Date()
              }
            });
          } catch (embError) {
            console.error(`Error generating embedding for ${product.title}:`, embError);
          }
        }

        results.brands_synced.push({
          brand: brandName,
          products_created: brandCreatedCount,
          products_updated: brandUpdatedCount,
          products_deactivated: productsToDeactivate.length,
          total_active: brandProductCount
        });

        results.total_products_created += brandCreatedCount;
        results.total_products_updated += brandUpdatedCount;

        console.log(`✅ ${brandName}: ${brandCreatedCount} created, ${brandUpdatedCount} updated, ${productsToDeactivate.length} deactivated`);
        
      } catch (brandError) {
        console.error(`❌ Error syncing brand ${brandName}:`, brandError);
        results.errors.push({
          brand: brandName,
          error: brandError.message
        });
      }
    }

    console.log('\n✅ SAFE sync completed!');
    console.log(`📊 Summary: ${results.total_products_created} created, ${results.total_products_updated} updated, ${results.total_products_deactivated} deactivated`);
    console.log(`🔒 Preserved ${results.manual_matches_preserved} manual matches`);

    res.json({
      message: 'SAFE sync completed successfully',
      ...results
    });

  } catch (error) {
    console.error('Error in SAFE sync:', error);
    res.status(500).json({ error: error.message });
  }
});

// Migration endpoint to restore manual matches if they were deleted
router.post('/restore-manual-matches', async (req, res) => {
  try {
    console.log('🔍 Checking for orphaned manual match data...');
    
    // This would need to be implemented based on your backup strategy
    // For now, return status
    res.json({
      message: 'Manual match restoration would need to be implemented based on backups',
      suggestion: 'Use the database backup to identify and restore lost manual matches'
    });

  } catch (error) {
    console.error('Error restoring matches:', error);
    res.status(500).json({ error: error.message });
  }
});

export default router;