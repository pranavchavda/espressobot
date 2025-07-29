#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';

const client = new PrismaClient();

async function debugProfitecMatching() {
  try {
    console.log('🔍 Debugging Profitec Product Matching Issues...\n');
    
    // Get sample Profitec products from both tables
    const idcProfitecProducts = await client.idc_products.findMany({
      where: {
        vendor: 'Profitec'
      },
      take: 10,
      select: {
        id: true,
        title: true,
        vendor: true,
        product_type: true,
        price: true,
        sku: true,
        embedding: true,
        features: true
      }
    });
    
    const competitorProfitecProducts = await client.competitor_products.findMany({
      where: {
        vendor: 'Profitec'
      },
      take: 10,
      select: {
        id: true,
        title: true,
        vendor: true,
        product_type: true,
        price: true,
        sku: true,
        embedding: true,
        features: true,
        competitor_id: true
      }
    });
    
    console.log('📦 Sample IDC Profitec Products:');
    console.log('================================');
    idcProfitecProducts.forEach((product, index) => {
      console.log(`${index + 1}. "${product.title}"`);
      console.log(`   Type: ${product.product_type || 'N/A'}`);
      console.log(`   Price: $${product.price || 'N/A'}`);
      console.log(`   SKU: ${product.sku || 'N/A'}`);
      console.log(`   Has embedding: ${product.embedding ? 'Yes' : 'No'}`);
      console.log(`   Has features: ${product.features ? 'Yes' : 'No'}`);
      console.log('');
    });
    
    console.log('🏪 Sample Competitor Profitec Products:');
    console.log('=======================================');
    competitorProfitecProducts.forEach((product, index) => {
      console.log(`${index + 1}. "${product.title}"`);
      console.log(`   Type: ${product.product_type || 'N/A'}`);
      console.log(`   Price: $${product.price || 'N/A'}`);
      console.log(`   SKU: ${product.sku || 'N/A'}`);
      console.log(`   Has embedding: ${product.embedding ? 'Yes' : 'No'}`);
      console.log(`   Has features: ${product.features ? 'Yes' : 'No'}`);
      console.log('');
    });
    
    // Check if there are any existing Profitec matches
    const existingProfitecMatches = await client.product_matches.findMany({
      where: {
        idc_product: {
          vendor: 'Profitec'
        }
      },
      include: {
        idc_product: {
          select: {
            title: true,
            vendor: true
          }
        },
        competitor_product: {
          select: {
            title: true,
            vendor: true
          }
        }
      }
    });
    
    console.log(`🎯 Existing Profitec Matches: ${existingProfitecMatches.length}`);
    console.log('==========================================');
    if (existingProfitecMatches.length > 0) {
      existingProfitecMatches.forEach((match, index) => {
        console.log(`${index + 1}. "${match.idc_product.title}" ↔ "${match.competitor_product.title}"`);
        console.log(`   Confidence: ${match.confidence_level}`);
        console.log(`   Score: ${(match.overall_score * 100).toFixed(1)}%`);
        console.log('');
      });
    } else {
      console.log('No existing Profitec matches found.\n');
    }
    
    // Check embedding status
    const idcEmbeddingStats = await client.idc_products.aggregate({
      where: { vendor: 'Profitec' },
      _count: {
        embedding: true,
        id: true
      }
    });
    
    const competitorEmbeddingStats = await client.competitor_products.aggregate({
      where: { vendor: 'Profitec' },
      _count: {
        embedding: true,
        id: true
      }
    });
    
    console.log('📊 Embedding Status:');
    console.log('====================');
    console.log(`IDC Profitec products with embeddings: ${idcEmbeddingStats._count.embedding}/${idcEmbeddingStats._count.id}`);
    console.log(`Competitor Profitec products with embeddings: ${competitorEmbeddingStats._count.embedding}/${competitorEmbeddingStats._count.id}`);
    
    if (idcEmbeddingStats._count.embedding === 0 || competitorEmbeddingStats._count.embedding === 0) {
      console.log('\n⚠️  WARNING: Missing embeddings detected!');
      console.log('This could be the primary reason for no Profitec matches.');
      console.log('Embeddings are crucial for the product matching algorithm.');
    }
    
    // Manual similarity test between first products
    if (idcProfitecProducts.length > 0 && competitorProfitecProducts.length > 0) {
      console.log('\n🧪 Manual Similarity Test:');
      console.log('==========================');
      
      const testIdcProduct = idcProfitecProducts[0];
      const testCompetitorProduct = competitorProfitecProducts[0];
      
      console.log(`Testing: "${testIdcProduct.title}" vs "${testCompetitorProduct.title}"`);
      
      // Calculate basic string similarity
      const calculateStringSimilarity = (str1, str2) => {
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
      };
      
      const titleSimilarity = calculateStringSimilarity(testIdcProduct.title, testCompetitorProduct.title);
      const vendorMatch = testIdcProduct.vendor?.toLowerCase() === testCompetitorProduct.vendor?.toLowerCase();
      
      console.log(`Title similarity: ${(titleSimilarity * 100).toFixed(1)}%`);
      console.log(`Vendor match: ${vendorMatch ? 'Yes' : 'No'}`);
      console.log(`Price similarity: IDC=$${testIdcProduct.price || 'N/A'}, Competitor=$${testCompetitorProduct.price || 'N/A'}`);
      
      if (titleSimilarity < 0.6) {
        console.log('\n⚠️  Low title similarity detected!');
        console.log('Product titles may be significantly different between IDC and competitor.');
      }
    }
    
    // Check competitor sources for Profitec
    const profitecCompetitorSources = await client.competitor_products.groupBy({
      by: ['competitor_id'],
      where: { vendor: 'Profitec' },
      _count: {
        competitor_id: true
      }
    });
    
    console.log('\n🏢 Profitec Competitor Sources:');
    console.log('===============================');
    
    for (const source of profitecCompetitorSources) {
      const competitor = await client.competitors.findUnique({
        where: { id: source.competitor_id },
        select: { name: true, domain: true }
      });
      
      console.log(`${competitor?.name || 'Unknown'} (${competitor?.domain}): ${source._count.competitor_id} products`);
    }
    
    console.log('\n📋 Diagnostic Summary:');
    console.log('======================');
    console.log('Potential reasons for no Profitec matches:');
    console.log('1. Missing or invalid embeddings');
    console.log('2. Product title differences between IDC and competitors');
    console.log('3. Similarity thresholds too strict for Profitec products');
    console.log('4. Price differences causing overall scores to drop');
    console.log('5. Product type mismatches');
    
    console.log('\nRecommended Actions:');
    console.log('1. Regenerate embeddings for all Profitec products');
    console.log('2. Run manual matching with lower confidence thresholds');
    console.log('3. Check product title normalization');
    console.log('4. Verify product type consistency');
    
  } catch (error) {
    console.error('❌ Error debugging Profitec matching:', error);
  } finally {
    await client.$disconnect();
  }
}

debugProfitecMatching();