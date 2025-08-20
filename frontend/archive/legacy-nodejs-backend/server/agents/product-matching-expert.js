/**
 * Product Matching Expert Agent - Specialized agent for intelligent product matching
 * Uses advanced reasoning to match products based on specifications, not just text similarity
 */

import { Agent } from '@openai/agents';
import { createModelProvider } from '../espressobot1.js';
import { db } from '../config/database.js';

const prisma = db;

/**
 * Create Product Matching Expert Agent
 */
export async function createProductMatchingExpert(task, conversationId, richContext = {}) {
  // Use the most capable model for this complex task
  const modelProvider = createModelProvider('gpt-4.1-turbo');
  
  const instructions = `You are an expert product matching specialist for coffee equipment. Your role is to accurately match products between iDrinkCoffee.com and competitor sites.

## Your Expertise:
- Deep knowledge of coffee equipment brands, models, and specifications
- Understanding of product naming conventions and model variations
- Ability to identify equivalent products despite different titles or descriptions
- Knowledge of common product aliases and regional variations

## Product Matching Rules:

### EXACT MATCHES Required:
1. **Same Model Number**: Products must have the same manufacturer model number
2. **Same Product Type**: Don't match grinders with machines, accessories with equipment, etc.
3. **Same Specifications**: Key specs must match (boiler type, grinder burrs, capacity, etc.)

### Common Matching Challenges:
- **Color Variants**: "Breville Barista Express Black" = "Breville BES870XL Barista Express" (same model)
- **Regional Names**: "Rocket Appartamento" = "Rocket Espresso Appartamento" 
- **Bundle Differences**: Don't match bundles with individual products
- **Generation Differences**: "ECM Synchronika" ≠ "ECM Synchronika II" (different generations)
- **Size Variants**: "Acaia Pearl" ≠ "Acaia Pearl S" (different models)

### Critical Distinctions:
- **ECM Mechanika V Slim** ≠ **ECM Synchronika** (different models, different features)
- **Eureka Mignon Specialita** ≠ **Eureka Mignon Silenzio** (different grinder models)
- **Profitec Pro 500** ≠ **Profitec Pro 600** (different machines)
- **Baratza Encore** ≠ **Baratza Virtuoso+** (different grinder tiers)

## Matching Process:
1. Extract the exact model number/name from both products
2. Verify they are the same product type (machine, grinder, accessory)
3. Check key specifications match
4. Consider color/finish as variants of the same model
5. Flag any uncertainty for human review

## Task Context:
${JSON.stringify(richContext, null, 2)}

## Important:
- Only create matches when you are highly confident they are the same product
- When in doubt, don't create the match
- Explain your reasoning for each match
- Flag products that seem similar but have important differences

Your task: ${task}`;

  const agent = new Agent({
    name: 'Product Matching Expert',
    instructions,
    model: modelProvider,
    toolUseBehavior: 'never' // This agent uses reasoning, not tools
  });
  
  return agent;
}

/**
 * Analyze products for matching
 */
export async function analyzeProductMatch(idcProductId, competitorProductId) {
  try {
    // Fetch both products
    const [idcProduct, competitorProduct] = await Promise.all([
      prisma.idc_products.findUnique({
        where: { id: idcProductId },
        include: { monitored_brands: true }
      }),
      prisma.competitor_products.findUnique({
        where: { id: competitorProductId },
        include: { competitors: true }
      })
    ]);

    if (!idcProduct || !competitorProduct) {
      throw new Error('One or both products not found');
    }

    // Create analysis task
    const task = `Analyze if these two products are an exact match:

IDC Product:
- Title: ${idcProduct.title}
- Brand: ${idcProduct.vendor}
- SKU: ${idcProduct.sku}
- Price: $${idcProduct.price}
- Type: ${idcProduct.product_type || 'Unknown'}
- Description: ${idcProduct.description ? idcProduct.description.substring(0, 500) + '...' : 'No description'}

Competitor Product (${competitorProduct.competitors.name}):
- Title: ${competitorProduct.title}
- Brand: ${competitorProduct.vendor || 'Unknown'}
- SKU: ${competitorProduct.sku || 'Unknown'}
- Price: $${competitorProduct.price}
- URL: ${competitorProduct.url}

Please analyze:
1. Are these the exact same product model?
2. What is your confidence level (0-100%)?
3. What evidence supports or contradicts the match?
4. Any important notes or warnings?

Respond in JSON format:
{
  "is_match": boolean,
  "confidence": number (0-100),
  "model_extracted": {
    "idc": "extracted model",
    "competitor": "extracted model"
  },
  "reasoning": "detailed explanation",
  "warnings": ["any concerns or notes"]
}`;

    const agent = await createProductMatchingExpert(task, 'matching-analysis');
    const { run } = await import('@openai/agents');
    
    const result = await run(agent, task, { maxTurns: 1 });
    
    // Parse the response
    try {
      const analysis = JSON.parse(result.output);
      return {
        success: true,
        analysis,
        idc_product: idcProduct,
        competitor_product: competitorProduct
      };
    } catch (parseError) {
      // If JSON parsing fails, return the raw analysis
      return {
        success: true,
        analysis: {
          is_match: false,
          confidence: 0,
          reasoning: result.output,
          warnings: ['Failed to parse structured response']
        },
        idc_product: idcProduct,
        competitor_product: competitorProduct
      };
    }
  } catch (error) {
    console.error('Error analyzing product match:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Find best matches for a product
 */
export async function findBestMatches(idcProductId, options = {}) {
  const {
    competitor_id = null,
    limit = 10,
    min_confidence = 70
  } = options;

  try {
    // Get the IDC product
    const idcProduct = await prisma.idc_products.findUnique({
      where: { id: idcProductId }
    });

    if (!idcProduct) {
      throw new Error('IDC product not found');
    }

    // Build search query for competitor products
    const whereClause = {};
    if (competitor_id) {
      whereClause.competitor_id = competitor_id;
    }

    // Search for potential matches using text similarity first
    const searchTerms = [
      idcProduct.vendor,
      ...idcProduct.title.split(' ').filter(term => 
        term.length > 3 && 
        !['with', 'and', 'for', 'the'].includes(term.toLowerCase())
      )
    ];

    whereClause.OR = searchTerms.map(term => ({
      title: { contains: term, mode: 'insensitive' }
    }));

    const candidates = await prisma.competitor_products.findMany({
      where: whereClause,
      include: { competitors: true },
      take: limit * 2 // Get more candidates than needed
    });

    // Analyze each candidate
    const analyses = [];
    for (const candidate of candidates) {
      const result = await analyzeProductMatch(idcProductId, candidate.id);
      if (result.success && result.analysis.confidence >= min_confidence) {
        analyses.push({
          ...result,
          competitor_product: candidate
        });
      }
    }

    // Sort by confidence
    analyses.sort((a, b) => b.analysis.confidence - a.analysis.confidence);

    return {
      success: true,
      idc_product: idcProduct,
      matches: analyses.slice(0, limit)
    };
  } catch (error) {
    console.error('Error finding best matches:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Bulk analyze potential matches
 */
export async function bulkAnalyzeMatches(matchPairs) {
  const results = [];
  
  for (const pair of matchPairs) {
    const result = await analyzeProductMatch(pair.idc_product_id, pair.competitor_product_id);
    results.push({
      ...pair,
      ...result
    });
    
    // Small delay to avoid rate limits
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  return results;
}

// Export for use in API routes
export {
  createProductMatchingExpert as createAgent
};