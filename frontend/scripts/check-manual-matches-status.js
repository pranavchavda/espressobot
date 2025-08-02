#!/usr/bin/env node

import { PrismaClient } from '@prisma/client';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables
dotenv.config({ path: join(__dirname, '..', '.env') });

const prisma = new PrismaClient();

async function checkManualMatches() {
  try {
    console.log('🔍 Checking manual matches status...\n');

    // Get all manual matches
    const manualMatches = await prisma.product_matches.findMany({
      where: { is_manual_match: true },
      include: {
        idc_products: true,
        competitor_products: {
          include: {
            competitors: true
          }
        }
      }
    });

    console.log(`📊 Total manual matches: ${manualMatches.length}`);

    // Group by brand
    const matchesByBrand = {};
    const matchesByCompetitor = {};
    
    manualMatches.forEach(match => {
      const brand = match.idc_products.vendor;
      const competitor = match.competitor_products.competitors.name;
      
      if (!matchesByBrand[brand]) {
        matchesByBrand[brand] = 0;
      }
      matchesByBrand[brand]++;
      
      if (!matchesByCompetitor[competitor]) {
        matchesByCompetitor[competitor] = 0;
      }
      matchesByCompetitor[competitor]++;
    });

    console.log('\n📦 Manual matches by brand:');
    Object.entries(matchesByBrand)
      .sort((a, b) => b[1] - a[1])
      .forEach(([brand, count]) => {
        console.log(`  - ${brand}: ${count} matches`);
      });

    console.log('\n🏪 Manual matches by competitor:');
    Object.entries(matchesByCompetitor)
      .sort((a, b) => b[1] - a[1])
      .forEach(([competitor, count]) => {
        console.log(`  - ${competitor}: ${count} matches`);
      });

    // Check for orphaned matches (where IDC product might have been deleted)
    const orphanedMatches = await prisma.product_matches.findMany({
      where: {
        is_manual_match: true,
        idc_products: {
          available: false
        }
      },
      include: {
        idc_products: true,
        competitor_products: {
          include: {
            competitors: true
          }
        }
      }
    });

    if (orphanedMatches.length > 0) {
      console.log(`\n⚠️  WARNING: Found ${orphanedMatches.length} manual matches for unavailable products:`);
      orphanedMatches.forEach(match => {
        console.log(`  - ${match.idc_products.title} (${match.idc_products.vendor})`);
      });
    }

    // Check last sync times
    const brandsWithMatches = Object.keys(matchesByBrand);
    console.log('\n📅 Last sync times for brands with manual matches:');
    
    for (const brand of brandsWithMatches) {
      const lastSyncedProduct = await prisma.idc_products.findFirst({
        where: { vendor: brand },
        orderBy: { last_synced_at: 'desc' },
        select: { last_synced_at: true }
      });
      
      if (lastSyncedProduct?.last_synced_at) {
        const hoursSinceSync = (Date.now() - new Date(lastSyncedProduct.last_synced_at).getTime()) / (1000 * 60 * 60);
        console.log(`  - ${brand}: ${new Date(lastSyncedProduct.last_synced_at).toLocaleString()} (${hoursSinceSync.toFixed(1)} hours ago)`);
      } else {
        console.log(`  - ${brand}: Never synced`);
      }
    }

    // Safety recommendation
    console.log('\n🚨 IMPORTANT SAFETY RECOMMENDATIONS:');
    console.log('1. STOP using /api/price-monitor/shopify-sync/sync-idc-products immediately');
    console.log('2. Use /api/price-monitor/shopify-sync-safe/sync-idc-products-safe instead');
    console.log('3. The safe sync will preserve manual matches by:');
    console.log('   - Updating existing products instead of deleting/recreating');
    console.log('   - Marking missing products as unavailable instead of deleting');
    console.log('   - Preserving all product relationships');
    console.log('\n4. Consider backing up manual matches regularly:');
    console.log('   SELECT * FROM product_matches WHERE is_manual_match = true;');

  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

checkManualMatches();