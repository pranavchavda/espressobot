import express from 'express';
import prisma from '../../lib/prisma.js';
import embeddingsService from '../../services/embeddings-service.js';

const router = express.Router();

// Product matching algorithm with multi-factor similarity scoring
class ProductMatcher {
  constructor() {
    // Hybrid approach: 40% embeddings + 60% traditional factors
    this.weights = {
      embedding: 0.4,    // 40% weight on semantic similarity  
      title: 0.18,       // 18% weight on title similarity (30% of 60%)
      vendor: 0.24,      // 24% weight on vendor matching (40% of 60%) 
      price: 0.06,       // 6% weight on price proximity (10% of 60%)
      sku: 0,            // Disabled
      type: 0.12         // 12% weight on product type (20% of 60%)
    };
    
    this.thresholds = {
      high_confidence: 0.80,    // 80%+ = very likely match
      medium_confidence: 0.70,  // 70-79% = possible match (matching original app)
      low_confidence: 0.60      // 60-69% = weak match
    };
  }

  // Calculate string similarity using Levenshtein distance
  calculateStringSimilarity(str1, str2) {
    if (!str1 || !str2) return 0;
    
    str1 = str1.toLowerCase().trim();
    str2 = str2.toLowerCase().trim();
    
    if (str1 === str2) return 1;
    
    const matrix = [];
    const len1 = str1.length;
    const len2 = str2.length;

    for (let i = 0; i <= len2; i++) {
      matrix[i] = [i];
    }

    for (let j = 0; j <= len1; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= len2; i++) {
      for (let j = 1; j <= len1; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }

    const maxLen = Math.max(len1, len2);
    return (maxLen - matrix[len2][len1]) / maxLen;
  }

  // Enhanced title similarity with brand and model extraction
  calculateTitleSimilarity(title1, title2) {
    if (!title1 || !title2) return 0;

    // Basic string similarity
    const basicSimilarity = this.calculateStringSimilarity(title1, title2);
    
    // Extract key terms (remove common words)
    const stopWords = ['the', 'and', 'or', 'with', 'for', 'espresso', 'coffee', 'machine', 'grinder'];
    const extractKeyTerms = (title) => {
      return title.toLowerCase()
        .replace(/[^\w\s]/g, ' ')
        .split(/\s+/)
        .filter(word => word.length > 2 && !stopWords.includes(word))
        .sort();
    };

    const terms1 = extractKeyTerms(title1);
    const terms2 = extractKeyTerms(title2);
    
    // Calculate term overlap
    const commonTerms = terms1.filter(term => terms2.includes(term));
    const termSimilarity = commonTerms.length / Math.max(terms1.length, terms2.length, 1);
    
    // Weighted combination
    return (basicSimilarity * 0.6) + (termSimilarity * 0.4);
  }

  // Vendor similarity (exact match gets higher score)
  calculateVendorSimilarity(vendor1, vendor2) {
    if (!vendor1 || !vendor2) return 0;
    
    const v1 = vendor1.toLowerCase().trim();
    const v2 = vendor2.toLowerCase().trim();
    
    // Exact match
    if (v1 === v2) return 1;
    
    // Check if one vendor contains the other
    if (v1.includes(v2) || v2.includes(v1)) return 0.8;
    
    // String similarity fallback
    return this.calculateStringSimilarity(v1, v2);
  }

  // Price similarity based on relative difference
  calculatePriceSimilarity(price1, price2) {
    if (!price1 || !price2 || price1 <= 0 || price2 <= 0) return 0;
    
    const priceDiff = Math.abs(price1 - price2);
    const avgPrice = (price1 + price2) / 2;
    const relativeError = priceDiff / avgPrice;
    
    // More generous similarity for price matching
    if (relativeError <= 0.05) return 1;      // 5% difference = perfect
    if (relativeError <= 0.15) return 0.8;    // 15% difference = good
    if (relativeError <= 0.30) return 0.6;    // 30% difference = fair
    if (relativeError <= 0.50) return 0.4;    // 50% difference = poor
    
    return Math.max(0, 1 - relativeError);
  }

  // SKU similarity
  calculateSkuSimilarity(sku1, sku2) {
    if (!sku1 || !sku2) return 0;
    
    // Exact match
    if (sku1.toLowerCase() === sku2.toLowerCase()) return 1;
    
    // Extract alphanumeric parts
    const extractAlphaNumeric = (sku) => {
      return sku.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
    };
    
    const clean1 = extractAlphaNumeric(sku1);
    const clean2 = extractAlphaNumeric(sku2);
    
    if (clean1 === clean2) return 0.9;
    
    return this.calculateStringSimilarity(clean1, clean2);
  }

  // Product type similarity
  calculateTypeSimilarity(type1, type2) {
    if (!type1 || !type2) return 0;
    
    const t1 = type1.toLowerCase().trim();
    const t2 = type2.toLowerCase().trim();
    
    if (t1 === t2) return 1;
    
    // Category matching
    const categories = {
      'espresso': ['espresso-machines', 'coffee-machines', 'automatic', 'semi-automatic'],
      'grinder': ['grinders', 'burr-grinder', 'coffee-grinder'],
      'accessory': ['accessories', 'parts', 'cleaning']
    };
    
    for (const [category, terms] of Object.entries(categories)) {
      if (terms.some(term => t1.includes(term)) && terms.some(term => t2.includes(term))) {
        return 0.8;
      }
    }
    
    return this.calculateStringSimilarity(t1, t2);
  }

  // Calculate embedding similarity using cosine similarity
  calculateEmbeddingSimilarity(embedding1, embedding2) {
    if (!embedding1 || !embedding2) return 0;
    
    try {
      return embeddingsService.calculateCosineSimilarity(embedding1, embedding2);
    } catch (error) {
      console.warn('Error calculating embedding similarity:', error);
      return 0;
    }
  }

  // Calculate overall similarity score
  calculateSimilarity(idcProduct, competitorProduct) {
    const titleScore = this.calculateTitleSimilarity(idcProduct.title, competitorProduct.title);
    const vendorScore = this.calculateVendorSimilarity(idcProduct.vendor, competitorProduct.vendor);
    const priceScore = this.calculatePriceSimilarity(idcProduct.price, competitorProduct.price);
    const skuScore = this.calculateSkuSimilarity(idcProduct.sku, competitorProduct.sku);
    const typeScore = this.calculateTypeSimilarity(idcProduct.product_type, competitorProduct.product_type);
    const embeddingScore = this.calculateEmbeddingSimilarity(idcProduct.embedding, competitorProduct.embedding);

    // Ensure all scores are between 0 and 1
    const clampedScores = {
      titleScore: Math.max(0, Math.min(1, titleScore)),
      vendorScore: Math.max(0, Math.min(1, vendorScore)),
      priceScore: Math.max(0, Math.min(1, priceScore)),
      skuScore: Math.max(0, Math.min(1, skuScore)),
      typeScore: Math.max(0, Math.min(1, typeScore)),
      embeddingScore: Math.max(0, Math.min(1, embeddingScore))
    };

    const overallScore = 
      (clampedScores.embeddingScore * this.weights.embedding) +
      (clampedScores.titleScore * this.weights.title) +
      (clampedScores.vendorScore * this.weights.vendor) +
      (clampedScores.priceScore * this.weights.price) +
      (clampedScores.skuScore * this.weights.sku) +
      (clampedScores.typeScore * this.weights.type);

    // Debug logging for problematic scores
    if (overallScore > 1.0) {
      console.log(`⚠️  Score > 1.0 detected:`, {
        title1: idcProduct.title,
        title2: competitorProduct.title,
        scores: {
          title: titleScore,
          vendor: vendorScore,
          price: priceScore,
          sku: skuScore,
          type: typeScore,
          embedding: embeddingScore
        },
        weighted: {
          title: clampedScores.titleScore * this.weights.title,
          vendor: clampedScores.vendorScore * this.weights.vendor,
          price: clampedScores.priceScore * this.weights.price,
          sku: clampedScores.skuScore * this.weights.sku,
          type: clampedScores.typeScore * this.weights.type,
          embedding: clampedScores.embeddingScore * this.weights.embedding
        },
        overall: overallScore
      });
    }

    return {
      overall_score: Math.max(0, Math.min(1, overallScore)), // Clamp final score too
      embedding_similarity: clampedScores.embeddingScore,
      title_similarity: clampedScores.titleScore,
      brand_similarity: clampedScores.vendorScore,
      price_similarity: clampedScores.priceScore,
      sku_similarity: clampedScores.skuScore,
      type_similarity: clampedScores.typeScore,
      confidence_level: this.getConfidenceLevel(Math.max(0, Math.min(1, overallScore)))
    };
  }

  // Get confidence level based on score
  getConfidenceLevel(score) {
    if (score >= this.thresholds.high_confidence) return 'high';
    if (score >= this.thresholds.medium_confidence) return 'medium';
    if (score >= this.thresholds.low_confidence) return 'low';
    return 'very_low';
  }
}

// Match products automatically
router.post('/auto-match', async (req, res) => {
  try {
    const { 
      brands, 
      min_confidence = 'medium',
      dry_run = false,
      limit = 100 
    } = req.body;

    console.log('🔍 Starting automatic product matching...');
    
    const matcher = new ProductMatcher();
    const results = {
      total_processed: 0,
      matches_found: 0,
      high_confidence: 0,
      medium_confidence: 0,
      low_confidence: 0,
      matches: []
    };

    // Get iDC products to match
    const whereClause = brands ? { vendor: { in: brands } } : {};
    const idcProducts = await prisma.idc_products.findMany({
      where: whereClause,
      take: parseInt(limit)
    });

    console.log(`📦 Processing ${idcProducts.length} iDC products`);

    for (const idcProduct of idcProducts) {
      // Get all competitor products for embedding comparison
      const competitorProducts = await prisma.competitor_products.findMany({
        take: 100 // Increased limit since we're only using embeddings
      });

      let bestMatch = null;
      let bestScore = 0;

      for (const competitorProduct of competitorProducts) {
        const similarity = matcher.calculateSimilarity(idcProduct, competitorProduct);
        
        // Debug logging for first few products
        if (results.total_processed < 5) {
          console.log(`🔍 Debug: "${idcProduct.title}" vs "${competitorProduct.title}" = ${(similarity.overall_score * 100).toFixed(1)}% (${similarity.confidence_level})`);
        }
        
        if (similarity.overall_score > bestScore && 
            similarity.confidence_level !== 'very_low') {
          bestMatch = {
            competitor_product: competitorProduct,
            similarity: similarity
          };
          bestScore = similarity.overall_score;
        }
      }

      if (bestMatch && meetsMinConfidence(bestMatch.similarity.confidence_level, min_confidence)) {
        results.matches_found++;
        results[bestMatch.similarity.confidence_level + '_confidence']++;

        console.log(`✅ Creating match: "${idcProduct.title}" → "${bestMatch.competitor_product.title}" (${(bestMatch.similarity.overall_score * 100).toFixed(1)}%)`);

        const matchData = {
          idc_product_id: idcProduct.id,
          competitor_product_id: bestMatch.competitor_product.id,
          overall_score: bestMatch.similarity.overall_score,
          embedding_similarity: bestMatch.similarity.embedding_similarity,
          title_similarity: bestMatch.similarity.title_similarity,
          brand_similarity: bestMatch.similarity.brand_similarity,
          price_similarity: bestMatch.similarity.price_similarity,
          confidence_level: bestMatch.similarity.confidence_level,
          created_at: new Date()
        };

        if (!dry_run) {
          // Save the match to database
          await prisma.product_matches.upsert({
            where: {
              idc_product_id_competitor_product_id: {
                idc_product_id: idcProduct.id,
                competitor_product_id: bestMatch.competitor_product.id
              }
            },
            create: matchData,
            update: {
              ...matchData,
              updated_at: new Date()
            }
          });
        }

        results.matches.push({
          idc_product: {
            title: idcProduct.title,
            vendor: idcProduct.vendor,
            sku: idcProduct.sku,
            price: idcProduct.price
          },
          competitor_product: {
            title: bestMatch.competitor_product.title,
            vendor: bestMatch.competitor_product.vendor,
            sku: bestMatch.competitor_product.sku,
            price: bestMatch.competitor_product.price,
            competitor: bestMatch.competitor_product.competitor_id
          },
          similarity: bestMatch.similarity
        });
      }

      results.total_processed++;
    }

    console.log(`✅ Matching completed: ${results.matches_found} matches found from ${results.total_processed} products`);

    res.json({
      message: `Product matching completed${dry_run ? ' (dry run)' : ''}`,
      ...results
    });

  } catch (error) {
    console.error('Error in automatic product matching:', error);
    res.status(500).json({ error: 'Failed to match products automatically' });
  }
});

// Helper method to check minimum confidence
function meetsMinConfidence(level, minLevel) {
  const levels = { 'low': 1, 'medium': 2, 'high': 3 };
  return levels[level] >= levels[minLevel];
}

// Manual product matching
router.post('/manual-match', async (req, res) => {
  try {
    const { idc_product_id, competitor_product_id, confidence_override } = req.body;

    if (!idc_product_id || !competitor_product_id) {
      return res.status(400).json({ 
        error: 'Both idc_product_id and competitor_product_id are required' 
      });
    }

    // Get products
    const [idcProduct, competitorProduct] = await Promise.all([
      prisma.idc_products.findUnique({ where: { id: idc_product_id } }),
      prisma.competitor_products.findUnique({ where: { id: competitor_product_id } })
    ]);

    if (!idcProduct || !competitorProduct) {
      return res.status(404).json({ error: 'One or both products not found' });
    }

    // Calculate similarity
    const matcher = new ProductMatcher();
    const similarity = matcher.calculateSimilarity(idcProduct, competitorProduct);

    // Create manual match
    const matchData = {
      idc_product_id,
      competitor_product_id,
      overall_score: similarity.overall_score,
      embedding_similarity: similarity.embedding_similarity,
      title_similarity: similarity.title_similarity,
      brand_similarity: similarity.brand_similarity,
      price_similarity: similarity.price_similarity,
      confidence_level: confidence_override || similarity.confidence_level,
      is_manual_match: true,
      created_at: new Date()
    };

    const match = await prisma.product_matches.upsert({
      where: {
        idc_product_id_competitor_product_id: {
          idc_product_id,
          competitor_product_id
        }
      },
      create: matchData,
      update: {
        ...matchData,
        updated_at: new Date()
      }
    });

    res.json({
      message: 'Manual product match created successfully',
      match,
      similarity
    });

  } catch (error) {
    console.error('Error creating manual product match:', error);
    res.status(500).json({ error: 'Failed to create manual product match' });
  }
});

// Get product matches with filtering
router.get('/matches', async (req, res) => {
  try {
    const { 
      confidence_level, 
      brand,
      has_violations,
      page = 1, 
      limit = 50 
    } = req.query;

    const skip = (parseInt(page) - 1) * parseInt(limit);
    const where = {};

    if (confidence_level) {
      where.confidence_level = confidence_level;
    }

    if (brand) {
      where.idc_product = { vendor: brand };
    }

    if (has_violations === 'true') {
      where.price_alerts = { some: {} };
    }

    const [matches, totalCount] = await Promise.all([
      prisma.product_matches.findMany({
        where,
        skip,
        take: parseInt(limit),
        include: {
          idc_product: true,
          competitor_product: {
            include: {
              competitor: true
            }
          },
          price_alerts: {
            where: { 
              status: { 
                notIn: ['resolved', 'dismissed'] 
              } 
            },
            take: 1
          }
        },
        orderBy: [
          { confidence_level: 'desc' },
          { overall_score: 'desc' }
        ]
      }),
      prisma.product_matches.count({ where })
    ]);

    res.json({
      matches,
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
    console.error('Error fetching product matches:', error);
    res.status(500).json({ error: 'Failed to fetch product matches' });
  }
});

// Delete a product match
router.delete('/matches/:matchId', async (req, res) => {
  try {
    const { matchId } = req.params;

    const match = await prisma.product_matches.findUnique({
      where: { id: matchId }
    });

    if (!match) {
      return res.status(404).json({ error: 'Product match not found' });
    }

    await prisma.product_matches.delete({
      where: { id: matchId }
    });

    res.json({ message: 'Product match deleted successfully' });

  } catch (error) {
    console.error('Error deleting product match:', error);
    res.status(500).json({ error: 'Failed to delete product match' });
  }
});

// Clear all product matches
router.post('/clear-all-matches', async (req, res) => {
  try {
    const result = await prisma.product_matches.deleteMany({});
    console.log(`🗑️  Cleared ${result.count} existing product matches`);
    
    res.json({ 
      message: `Cleared ${result.count} existing product matches`,
      cleared_count: result.count
    });

  } catch (error) {
    console.error('Error clearing product matches:', error);
    res.status(500).json({ error: 'Failed to clear product matches' });
  }
});

// Regenerate embeddings for all products
router.post('/regenerate-embeddings', async (req, res) => {
  try {
    console.log('🔄 Starting embedding regeneration...');
    
    // Get all products that need embeddings
    const [idcProducts, competitorProducts] = await Promise.all([
      prisma.idc_products.findMany(),
      prisma.competitor_products.findMany()
    ]);

    let updatedCount = 0;
    const embeddingsService = (await import('../../services/embeddings-service.js')).default;

    // Update iDC products
    for (const product of idcProducts) {
      try {
        const embedding = await embeddingsService.generateEmbedding(product);
        if (embedding) {
          await prisma.idc_products.update({
            where: { id: product.id },
            data: { embedding }
          });
          updatedCount++;
          console.log(`✓ Updated iDC embedding: ${product.title}`);
        }
      } catch (error) {
        console.error(`Failed to update iDC embedding for ${product.title}:`, error);
      }
    }

    // Update competitor products  
    for (const product of competitorProducts) {
      try {
        const embedding = await embeddingsService.generateEmbedding(product);
        if (embedding) {
          await prisma.competitor_products.update({
            where: { id: product.id },
            data: { embedding }
          });
          updatedCount++;
          console.log(`✓ Updated competitor embedding: ${product.title}`);
        }
      } catch (error) {
        console.error(`Failed to update competitor embedding for ${product.title}:`, error);
      }
    }

    console.log(`✅ Embedding regeneration completed: ${updatedCount} products updated`);
    
    res.json({
      message: `Regenerated embeddings for ${updatedCount} products`,
      updated_count: updatedCount,
      total_products: idcProducts.length + competitorProducts.length
    });

  } catch (error) {
    console.error('Error regenerating embeddings:', error);
    res.status(500).json({ error: 'Failed to regenerate embeddings' });
  }
});

export default router;