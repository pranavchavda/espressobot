import express from 'express';
import { analyzeProductMatch, findBestMatches, bulkAnalyzeMatches } from '../../agents/product-matching-expert.js';
import { db } from '../../config/database.js';

const prisma = db;
const router = express.Router();

/**
 * Analyze if two products match using AI
 */
router.post('/analyze-match', async (req, res) => {
  try {
    const { idc_product_id, competitor_product_id } = req.body;
    
    if (!idc_product_id || !competitor_product_id) {
      return res.status(400).json({
        error: 'Both idc_product_id and competitor_product_id are required'
      });
    }
    
    console.log('🤖 Analyzing product match with AI...');
    const result = await analyzeProductMatch(idc_product_id, competitor_product_id);
    
    res.json(result);
  } catch (error) {
    console.error('Error analyzing match:', error);
    res.status(500).json({ error: 'Failed to analyze match' });
  }
});

/**
 * Find best matches for an IDC product
 */
router.post('/find-matches', async (req, res) => {
  try {
    const { 
      idc_product_id, 
      competitor_id = null,
      limit = 10,
      min_confidence = 70 
    } = req.body;
    
    if (!idc_product_id) {
      return res.status(400).json({
        error: 'idc_product_id is required'
      });
    }
    
    console.log('🔍 Finding best matches with AI...');
    const result = await findBestMatches(idc_product_id, {
      competitor_id,
      limit,
      min_confidence
    });
    
    res.json(result);
  } catch (error) {
    console.error('Error finding matches:', error);
    res.status(500).json({ error: 'Failed to find matches' });
  }
});

/**
 * Create a match after AI verification
 */
router.post('/create-verified-match', async (req, res) => {
  try {
    const { idc_product_id, competitor_product_id, require_confidence = 80 } = req.body;
    
    if (!idc_product_id || !competitor_product_id) {
      return res.status(400).json({
        error: 'Both idc_product_id and competitor_product_id are required'
      });
    }
    
    // First analyze the match
    console.log('🤖 Verifying match with AI before creation...');
    const analysis = await analyzeProductMatch(idc_product_id, competitor_product_id);
    
    if (!analysis.success) {
      return res.status(500).json({
        error: 'Failed to analyze match',
        details: analysis.error
      });
    }
    
    // Check confidence threshold
    if (analysis.analysis.confidence < require_confidence) {
      return res.status(400).json({
        error: 'Match confidence too low',
        analysis: analysis.analysis,
        required_confidence: require_confidence
      });
    }
    
    if (!analysis.analysis.is_match) {
      return res.status(400).json({
        error: 'Products do not match according to AI analysis',
        analysis: analysis.analysis
      });
    }
    
    // Create the match
    const matchData = {
      id: `${idc_product_id}_${competitor_product_id}`,
      idc_product_id,
      competitor_product_id,
      overall_score: analysis.analysis.confidence / 100,
      embedding_similarity: 0.9, // High but not perfect since AI verified
      title_similarity: 0.9,
      brand_similarity: 1.0,
      price_similarity: 0.8,
      confidence_level: 'high',
      is_manual_match: true,
      created_at: new Date(),
      updated_at: new Date()
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
      message: 'AI-verified match created successfully',
      match,
      analysis: analysis.analysis
    });
    
  } catch (error) {
    console.error('Error creating verified match:', error);
    res.status(500).json({ error: 'Failed to create verified match' });
  }
});

/**
 * Bulk analyze potential matches
 */
router.post('/bulk-analyze', async (req, res) => {
  try {
    const { match_pairs } = req.body;
    
    if (!match_pairs || !Array.isArray(match_pairs) || match_pairs.length === 0) {
      return res.status(400).json({
        error: 'match_pairs array is required'
      });
    }
    
    if (match_pairs.length > 50) {
      return res.status(400).json({
        error: 'Maximum 50 pairs can be analyzed at once'
      });
    }
    
    console.log(`🤖 Bulk analyzing ${match_pairs.length} potential matches...`);
    const results = await bulkAnalyzeMatches(match_pairs);
    
    // Separate matches and non-matches
    const verified_matches = results.filter(r => 
      r.success && r.analysis.is_match && r.analysis.confidence >= 70
    );
    const rejected_matches = results.filter(r => 
      r.success && (!r.analysis.is_match || r.analysis.confidence < 70)
    );
    const errors = results.filter(r => !r.success);
    
    res.json({
      total_analyzed: match_pairs.length,
      verified_matches: verified_matches.length,
      rejected_matches: rejected_matches.length,
      errors: errors.length,
      results: {
        verified: verified_matches,
        rejected: rejected_matches,
        errors: errors
      }
    });
    
  } catch (error) {
    console.error('Error in bulk analysis:', error);
    res.status(500).json({ error: 'Failed to perform bulk analysis' });
  }
});

/**
 * Get AI matching suggestions for unmatched products
 */
router.get('/suggestions', async (req, res) => {
  try {
    const { brand, limit = 20 } = req.query;
    
    // Get unmatched IDC products
    const unmatchedProducts = await prisma.idc_products.findMany({
      where: {
        vendor: brand || undefined,
        product_matches: {
          none: {}
        }
      },
      take: parseInt(limit),
      orderBy: { price: 'desc' } // Start with higher value products
    });
    
    res.json({
      unmatched_count: unmatchedProducts.length,
      products: unmatchedProducts,
      message: `Found ${unmatchedProducts.length} unmatched products${brand ? ` for ${brand}` : ''}`
    });
    
  } catch (error) {
    console.error('Error getting suggestions:', error);
    res.status(500).json({ error: 'Failed to get matching suggestions' });
  }
});

export default router;