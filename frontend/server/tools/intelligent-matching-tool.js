/**
 * Intelligent Product Matching Tool for EspressoBot Orchestrator
 * Uses advanced AI reasoning to match products accurately
 */

import { z } from 'zod';
import { analyzeProductMatch, findBestMatches } from '../agents/product-matching-expert.js';
import { db } from '../config/database.js';

const prisma = db;

export const intelligentMatchingTool = {
  name: 'intelligent_product_match',
  description: 'Use advanced AI to intelligently match coffee equipment products between iDrinkCoffee and competitors. This tool understands product specifications, model variations, and can distinguish between similar but different products.',
  
  inputSchema: z.object({
    action: z.enum(['analyze', 'find_matches', 'create_matches', 'get_unmatched']).describe('Action to perform'),
    idc_product_id: z.string().optional().describe('IDC product ID (for analyze/find_matches)'),
    competitor_product_id: z.string().optional().describe('Competitor product ID (for analyze)'),
    brand: z.string().optional().describe('Filter by brand (for get_unmatched)'),
    limit: z.number().optional().default(10).describe('Maximum results to return'),
    min_confidence: z.number().optional().default(80).describe('Minimum confidence threshold (0-100)'),
    auto_create: z.boolean().optional().default(false).describe('Automatically create high-confidence matches')
  }),
  
  execute: async (input) => {
    try {
      switch (input.action) {
        case 'analyze': {
          if (!input.idc_product_id || !input.competitor_product_id) {
            return {
              success: false,
              error: 'Both idc_product_id and competitor_product_id required for analysis'
            };
          }
          
          const result = await analyzeProductMatch(input.idc_product_id, input.competitor_product_id);
          
          if (result.success) {
            return {
              success: true,
              is_match: result.analysis.is_match,
              confidence: result.analysis.confidence,
              reasoning: result.analysis.reasoning,
              model_comparison: result.analysis.model_extracted,
              warnings: result.analysis.warnings,
              idc_product: {
                title: result.idc_product.title,
                vendor: result.idc_product.vendor,
                price: result.idc_product.price
              },
              competitor_product: {
                title: result.competitor_product.title,
                vendor: result.competitor_product.vendor,
                price: result.competitor_product.price,
                competitor: result.competitor_product.competitors.name
              }
            };
          }
          
          return result;
        }
        
        case 'find_matches': {
          if (!input.idc_product_id) {
            return {
              success: false,
              error: 'idc_product_id required for finding matches'
            };
          }
          
          const result = await findBestMatches(input.idc_product_id, {
            limit: input.limit,
            min_confidence: input.min_confidence
          });
          
          if (result.success) {
            const matches = result.matches.map(m => ({
              competitor_product: {
                id: m.competitor_product.id,
                title: m.competitor_product.title,
                vendor: m.competitor_product.vendor,
                price: m.competitor_product.price,
                competitor: m.competitor_product.competitors.name,
                url: m.competitor_product.url
              },
              analysis: {
                is_match: m.analysis.is_match,
                confidence: m.analysis.confidence,
                reasoning: m.analysis.reasoning,
                warnings: m.analysis.warnings
              }
            }));
            
            // Auto-create matches if requested
            if (input.auto_create) {
              const created = [];
              for (const match of matches) {
                if (match.analysis.confidence >= 90 && match.analysis.is_match) {
                  try {
                    const matchData = {
                      id: `${input.idc_product_id}_${match.competitor_product.id}`,
                      idc_product_id: input.idc_product_id,
                      competitor_product_id: match.competitor_product.id,
                      overall_score: match.analysis.confidence / 100,
                      embedding_similarity: 0.95,
                      title_similarity: 0.95,
                      brand_similarity: 1.0,
                      price_similarity: 0.9,
                      confidence_level: 'high',
                      is_manual_match: true,
                      created_at: new Date(),
                      updated_at: new Date()
                    };
                    
                    await prisma.product_matches.upsert({
                      where: {
                        idc_product_id_competitor_product_id: {
                          idc_product_id: input.idc_product_id,
                          competitor_product_id: match.competitor_product.id
                        }
                      },
                      create: matchData,
                      update: matchData
                    });
                    
                    created.push(match.competitor_product.id);
                  } catch (error) {
                    console.error('Error creating match:', error);
                  }
                }
              }
              
              return {
                success: true,
                idc_product: {
                  id: result.idc_product.id,
                  title: result.idc_product.title,
                  vendor: result.idc_product.vendor,
                  price: result.idc_product.price
                },
                matches_found: matches.length,
                matches_created: created.length,
                matches: matches,
                created_ids: created
              };
            }
            
            return {
              success: true,
              idc_product: {
                id: result.idc_product.id,
                title: result.idc_product.title,
                vendor: result.idc_product.vendor,
                price: result.idc_product.price
              },
              matches_found: matches.length,
              matches: matches
            };
          }
          
          return result;
        }
        
        case 'create_matches': {
          // Batch create matches for a brand
          if (!input.brand) {
            return {
              success: false,
              error: 'Brand required for batch match creation'
            };
          }
          
          // Get unmatched products
          const unmatchedProducts = await prisma.idc_products.findMany({
            where: {
              vendor: input.brand,
              product_matches: {
                none: {}
              }
            },
            take: input.limit,
            orderBy: { price: 'desc' }
          });
          
          const results = {
            total_processed: 0,
            matches_created: 0,
            matches_found: 0,
            errors: 0,
            details: []
          };
          
          for (const product of unmatchedProducts) {
            results.total_processed++;
            
            try {
              const matchResult = await findBestMatches(product.id, {
                limit: 5,
                min_confidence: input.min_confidence
              });
              
              if (matchResult.success && matchResult.matches.length > 0) {
                results.matches_found += matchResult.matches.length;
                
                // Only create the highest confidence match if it meets threshold
                const bestMatch = matchResult.matches[0];
                if (bestMatch.analysis.confidence >= input.min_confidence && bestMatch.analysis.is_match) {
                  const matchData = {
                    id: `${product.id}_${bestMatch.competitor_product.id}`,
                    idc_product_id: product.id,
                    competitor_product_id: bestMatch.competitor_product.id,
                    overall_score: bestMatch.analysis.confidence / 100,
                    embedding_similarity: 0.9,
                    title_similarity: 0.9,
                    brand_similarity: 1.0,
                    price_similarity: 0.8,
                    confidence_level: 'high',
                    is_manual_match: true,
                    created_at: new Date(),
                    updated_at: new Date()
                  };
                  
                  await prisma.product_matches.upsert({
                    where: {
                      idc_product_id_competitor_product_id: {
                        idc_product_id: product.id,
                        competitor_product_id: bestMatch.competitor_product.id
                      }
                    },
                    create: matchData,
                    update: matchData
                  });
                  
                  results.matches_created++;
                  results.details.push({
                    idc_product: product.title,
                    matched_to: bestMatch.competitor_product.title,
                    confidence: bestMatch.analysis.confidence,
                    competitor: bestMatch.competitor_product.competitors.name
                  });
                }
              }
            } catch (error) {
              results.errors++;
              console.error(`Error processing ${product.title}:`, error);
            }
            
            // Rate limiting
            await new Promise(resolve => setTimeout(resolve, 500));
          }
          
          return {
            success: true,
            ...results
          };
        }
        
        case 'get_unmatched': {
          const whereClause = {
            product_matches: {
              none: {}
            }
          };
          
          if (input.brand) {
            whereClause.vendor = input.brand;
          }
          
          const unmatchedProducts = await prisma.idc_products.findMany({
            where: whereClause,
            take: input.limit,
            orderBy: { price: 'desc' },
            select: {
              id: true,
              title: true,
              vendor: true,
              sku: true,
              price: true,
              product_type: true
            }
          });
          
          const totalUnmatched = await prisma.idc_products.count({
            where: whereClause
          });
          
          return {
            success: true,
            total_unmatched: totalUnmatched,
            products: unmatchedProducts,
            showing: unmatchedProducts.length
          };
        }
        
        default:
          return {
            success: false,
            error: `Unknown action: ${input.action}`
          };
      }
    } catch (error) {
      console.error('Intelligent matching tool error:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
};