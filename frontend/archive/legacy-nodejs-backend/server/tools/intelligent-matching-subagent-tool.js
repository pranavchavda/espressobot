/**
 * Intelligent Product Matching using Claude Sub-Agent
 * Leverages Claude's advanced reasoning through the Task tool
 */

import { z } from 'zod';
import { db } from '../config/database.js';

const prisma = db;

export const intelligentMatchingSubAgentTool = {
  name: 'intelligent_product_match_subagent',
  description: 'Use Claude sub-agent for intelligent product matching. This leverages advanced AI reasoning to accurately match coffee equipment products based on specifications, model numbers, and deep product knowledge.',
  
  inputSchema: z.object({
    action: z.enum(['analyze_match', 'find_matches', 'batch_analyze']).describe('Action to perform'),
    idc_product_id: z.string().optional().describe('IDC product ID'),
    competitor_product_id: z.string().optional().describe('Competitor product ID'),
    product_ids: z.array(z.string()).optional().describe('Array of IDC product IDs for batch operations'),
    limit: z.number().optional().default(5).describe('Maximum matches to find per product')
  }),
  
  execute: async (input, { task: taskTool }) => {
    try {
      switch (input.action) {
        case 'analyze_match': {
          if (!input.idc_product_id || !input.competitor_product_id) {
            return {
              success: false,
              error: 'Both idc_product_id and competitor_product_id required'
            };
          }
          
          // Fetch both products
          const [idcProduct, competitorProduct] = await Promise.all([
            prisma.idc_products.findUnique({
              where: { id: input.idc_product_id }
            }),
            prisma.competitor_products.findUnique({
              where: { id: input.competitor_product_id },
              include: { competitors: true }
            })
          ]);
          
          if (!idcProduct || !competitorProduct) {
            return {
              success: false,
              error: 'One or both products not found'
            };
          }
          
          // Create task for Claude sub-agent
          const analysisTask = `You are an expert coffee equipment product matcher. Analyze if these two products are an EXACT match:

IDC Product:
- Title: ${idcProduct.title}
- Brand: ${idcProduct.vendor}
- SKU: ${idcProduct.sku}
- Price: $${idcProduct.price}
- Type: ${idcProduct.product_type || 'Unknown'}

Competitor Product (${competitorProduct.competitors.name}):
- Title: ${competitorProduct.title}
- Brand: ${competitorProduct.vendor || 'Unknown'}
- SKU: ${competitorProduct.sku || 'Unknown'}
- Price: $${competitorProduct.price}

CRITICAL MATCHING RULES:
1. Products must be the EXACT same model (not just similar)
2. Different generations/versions are NOT matches (e.g., v1 vs v2)
3. Different sizes/capacities are NOT matches
4. Color variants of the same model ARE matches
5. Bundle vs individual product are NOT matches

Known distinctions to watch for:
- ECM Mechanika V Slim ≠ ECM Synchronika (different models)
- Eureka Mignon Specialita ≠ Eureka Mignon Silenzio (different grinders)
- Baratza Encore ≠ Baratza Virtuoso+ (different tiers)
- Acaia Pearl ≠ Acaia Pearl S (different models)

Analyze and respond with:
1. Are these the EXACT same product model? (YES/NO)
2. Confidence level (0-100%)
3. Key evidence supporting your decision
4. Any warnings or concerns

Be extremely strict - when in doubt, say NO.`;

          // Execute sub-agent task
          const result = await taskTool({
            description: "Analyze product match",
            prompt: analysisTask,
            subagent_type: "general-purpose"
          });
          
          // Parse the result
          const output = result.output || result;
          const lines = output.split('\n');
          
          // Extract key information from response
          const isMatch = output.toLowerCase().includes('yes') && !output.toLowerCase().includes('no');
          const confidenceMatch = output.match(/(\d+)\s*%/);
          const confidence = confidenceMatch ? parseInt(confidenceMatch[1]) : 0;
          
          return {
            success: true,
            is_match: isMatch && confidence >= 70,
            confidence: confidence,
            analysis: output,
            idc_product: {
              id: idcProduct.id,
              title: idcProduct.title,
              vendor: idcProduct.vendor,
              price: idcProduct.price
            },
            competitor_product: {
              id: competitorProduct.id,
              title: competitorProduct.title,
              vendor: competitorProduct.vendor,
              price: competitorProduct.price,
              competitor: competitorProduct.competitors.name
            }
          };
        }
        
        case 'find_matches': {
          if (!input.idc_product_id) {
            return {
              success: false,
              error: 'idc_product_id required'
            };
          }
          
          // Get the IDC product
          const idcProduct = await prisma.idc_products.findUnique({
            where: { id: input.idc_product_id }
          });
          
          if (!idcProduct) {
            return {
              success: false,
              error: 'IDC product not found'
            };
          }
          
          // Find potential competitors to check
          const searchTerms = [idcProduct.vendor];
          const titleWords = idcProduct.title.split(' ').filter(w => w.length > 3);
          searchTerms.push(...titleWords.slice(0, 3));
          
          const competitorProducts = await prisma.competitor_products.findMany({
            where: {
              OR: searchTerms.map(term => ({
                title: { contains: term, mode: 'insensitive' }
              }))
            },
            include: { competitors: true },
            take: input.limit * 2 // Get more candidates
          });
          
          if (competitorProducts.length === 0) {
            return {
              success: true,
              idc_product: idcProduct,
              matches: [],
              message: 'No potential matches found'
            };
          }
          
          // Create batch analysis task
          const batchTask = `You are an expert coffee equipment product matcher. Find which of these competitor products match the IDC product:

TARGET IDC PRODUCT:
- Title: ${idcProduct.title}
- Brand: ${idcProduct.vendor}
- SKU: ${idcProduct.sku}
- Price: $${idcProduct.price}

COMPETITOR PRODUCTS TO CHECK:
${competitorProducts.map((cp, i) => `
${i + 1}. ${cp.title}
   - Brand: ${cp.vendor || 'Unknown'}
   - Price: $${cp.price}
   - Store: ${cp.competitors.name}
   - ID: ${cp.id}
`).join('')}

For each competitor product, determine:
1. Is it an EXACT match? (YES/NO)
2. Confidence (0-100%)
3. Brief reason

Use the same strict matching rules as before. Format your response as:
Product 1: [YES/NO] - [Confidence]% - [Reason]
Product 2: [YES/NO] - [Confidence]% - [Reason]
etc.`;

          const result = await taskTool({
            description: "Find product matches",
            prompt: batchTask,
            subagent_type: "general-purpose"
          });
          
          // Parse results
          const output = result.output || result;
          const matches = [];
          const lines = output.split('\n');
          
          competitorProducts.forEach((cp, index) => {
            const productLine = lines.find(line => 
              line.toLowerCase().includes(`product ${index + 1}:`) ||
              line.toLowerCase().includes(`${index + 1}.`)
            );
            
            if (productLine) {
              const isMatch = productLine.toLowerCase().includes('yes');
              const confidenceMatch = productLine.match(/(\d+)\s*%/);
              const confidence = confidenceMatch ? parseInt(confidenceMatch[1]) : 0;
              
              if (isMatch && confidence >= 70) {
                matches.push({
                  competitor_product: {
                    id: cp.id,
                    title: cp.title,
                    vendor: cp.vendor,
                    price: cp.price,
                    competitor: cp.competitors.name,
                    url: cp.url
                  },
                  confidence: confidence,
                  reasoning: productLine
                });
              }
            }
          });
          
          // Sort by confidence
          matches.sort((a, b) => b.confidence - a.confidence);
          
          return {
            success: true,
            idc_product: idcProduct,
            matches: matches.slice(0, input.limit),
            total_analyzed: competitorProducts.length,
            raw_analysis: output
          };
        }
        
        case 'batch_analyze': {
          if (!input.product_ids || input.product_ids.length === 0) {
            return {
              success: false,
              error: 'product_ids array required'
            };
          }
          
          // For batch analysis, we'll process in smaller groups
          const batchSize = 3;
          const results = [];
          
          for (let i = 0; i < input.product_ids.length; i += batchSize) {
            const batchIds = input.product_ids.slice(i, i + batchSize);
            
            // Process each product in the batch
            for (const productId of batchIds) {
              const matchResult = await this.execute({
                action: 'find_matches',
                idc_product_id: productId,
                limit: 3
              }, { task: taskTool });
              
              if (matchResult.success) {
                results.push({
                  product_id: productId,
                  product_title: matchResult.idc_product.title,
                  matches_found: matchResult.matches.length,
                  best_match: matchResult.matches[0] || null
                });
              }
            }
          }
          
          return {
            success: true,
            total_analyzed: input.product_ids.length,
            results: results
          };
        }
        
        default:
          return {
            success: false,
            error: `Unknown action: ${input.action}`
          };
      }
    } catch (error) {
      console.error('Intelligent matching sub-agent error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
};