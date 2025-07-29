#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';

const client = new PrismaClient();

async function analyzePriceMonitorBrands() {
  try {
    console.log('🔍 Analyzing price monitoring brand distribution...\n');
    
    // Get brand distribution in idc_products
    console.log('📊 IDC Products Brand Distribution:');
    console.log('===================================');
    
    const idcBrandCounts = await client.idc_products.groupBy({
      by: ['vendor'],
      _count: {
        vendor: true
      },
      orderBy: {
        _count: {
          vendor: 'desc'
        }
      }
    });
    
    let totalIdcProducts = 0;
    idcBrandCounts.forEach(brand => {
      console.log(`${brand.vendor}: ${brand._count.vendor} products`);
      totalIdcProducts += brand._count.vendor;
    });
    console.log(`\nTotal IDC Products: ${totalIdcProducts}\n`);
    
    // Get brand distribution in competitor_products
    console.log('🏪 Competitor Products Brand Distribution:');
    console.log('=========================================');
    
    const competitorBrandCounts = await client.competitor_products.groupBy({
      by: ['vendor'],
      _count: {
        vendor: true
      },
      orderBy: {
        _count: {
          vendor: 'desc'
        }
      }
    });
    
    let totalCompetitorProducts = 0;
    competitorBrandCounts.forEach(brand => {
      if (brand.vendor) {
        console.log(`${brand.vendor}: ${brand._count.vendor} products`);
        totalCompetitorProducts += brand._count.vendor;
      } else {
        console.log(`[NULL/Empty]: ${brand._count.vendor} products`);
        totalCompetitorProducts += brand._count.vendor;
      }
    });
    console.log(`\nTotal Competitor Products: ${totalCompetitorProducts}\n`);
    
    // Find brand overlaps
    console.log('🔗 Brand Overlap Analysis:');
    console.log('==========================');
    
    const idcBrands = new Set(idcBrandCounts.map(b => b.vendor?.toLowerCase()?.trim()));
    const competitorBrands = new Set(competitorBrandCounts.map(b => b.vendor?.toLowerCase()?.trim()).filter(Boolean));
    
    const commonBrands = [...idcBrands].filter(brand => competitorBrands.has(brand));
    const idcOnlyBrands = [...idcBrands].filter(brand => !competitorBrands.has(brand));
    const competitorOnlyBrands = [...competitorBrands].filter(brand => !idcBrands.has(brand));
    
    console.log('Common Brands (appear in both tables):');
    commonBrands.forEach(brand => {
      const idcCount = idcBrandCounts.find(b => b.vendor?.toLowerCase()?.trim() === brand)?._count.vendor || 0;
      const compCount = competitorBrandCounts.find(b => b.vendor?.toLowerCase()?.trim() === brand)?._count.vendor || 0;
      console.log(`  - ${brand}: IDC=${idcCount}, Competitor=${compCount}`);
    });
    
    console.log('\nIDC-Only Brands:');
    idcOnlyBrands.forEach(brand => {
      const count = idcBrandCounts.find(b => b.vendor?.toLowerCase()?.trim() === brand)?._count.vendor || 0;
      console.log(`  - ${brand}: ${count} products`);
    });
    
    console.log('\nCompetitor-Only Brands:');
    competitorOnlyBrands.forEach(brand => {
      const count = competitorBrandCounts.find(b => b.vendor?.toLowerCase()?.trim() === brand)?._count.vendor || 0;
      console.log(`  - ${brand}: ${count} products`);
    });
    
    // Check product matches by brand
    console.log('\n🎯 Product Matches by Brand:');
    console.log('============================');
    
    const matchesByBrand = await client.product_matches.groupBy({
      by: ['idc_product_id'],
      _count: {
        id: true
      },
      where: {
        confidence_level: {
          in: ['medium', 'high']
        }
      }
    });
    
    // Get details for matches
    const matchDetails = await client.product_matches.findMany({
      where: {
        confidence_level: {
          in: ['medium', 'high']
        }
      },
      include: {
        idc_product: {
          select: {
            vendor: true,
            title: true
          }
        },
        competitor_product: {
          select: {
            vendor: true,
            title: true
          }
        }
      }
    });
    
    const matchesByVendor = {};
    matchDetails.forEach(match => {
      const vendor = match.idc_product.vendor;
      if (!matchesByVendor[vendor]) {
        matchesByVendor[vendor] = [];
      }
      matchesByVendor[vendor].push({
        idcTitle: match.idc_product.title,
        competitorVendor: match.competitor_product.vendor,
        competitorTitle: match.competitor_product.title,
        confidenceLevel: match.confidence_level,
        overallScore: match.overall_score
      });
    });
    
    Object.keys(matchesByVendor).sort().forEach(vendor => {
      console.log(`\n${vendor}: ${matchesByVendor[vendor].length} matches`);
      matchesByVendor[vendor].slice(0, 3).forEach(match => {
        console.log(`  → "${match.idcTitle}" ↔ "${match.competitorTitle}" (${match.competitorVendor}) [${match.confidenceLevel}, ${(match.overallScore * 100).toFixed(1)}%]`);
      });
      if (matchesByVendor[vendor].length > 3) {
        console.log(`  ... and ${matchesByVendor[vendor].length - 3} more`);
      }
    });
    
    // Check monitored brands
    console.log('\n🎯 Monitored Brands Configuration:');
    console.log('==================================');
    
    const monitoredBrands = await client.monitored_brands.findMany({
      orderBy: {
        brand_name: 'asc'
      }
    });
    
    monitoredBrands.forEach(brand => {
      const status = brand.is_active ? '✅ Active' : '❌ Inactive';
      console.log(`${brand.brand_name}: ${status}`);
    });
    
    // Summary insights
    console.log('\n📋 Summary & Insights:');
    console.log('======================');
    console.log(`• Total IDC Brands: ${idcBrands.size}`);
    console.log(`• Total Competitor Brands: ${competitorBrands.size}`);
    console.log(`• Common Brands: ${commonBrands.length}`);
    console.log(`• Brands with Matches: ${Object.keys(matchesByVendor).length}`);
    console.log(`• Total Product Matches: ${matchDetails.length}`);
    
    if (commonBrands.length < idcBrands.size) {
      console.log('\n⚠️  Potential Issues:');
      console.log('• Some IDC brands have no competitor data');
      console.log('• Brand name inconsistencies may prevent matching');
      console.log('• Consider normalizing brand names in matching algorithm');
    }
    
    if (Object.keys(matchesByVendor).length < commonBrands.length) {
      console.log('• Some common brands have no matches - embedding/similarity thresholds may be too strict');
    }
    
  } catch (error) {
    console.error('❌ Error analyzing brands:', error);
  } finally {
    await client.$disconnect();
  }
}

analyzePriceMonitorBrands();