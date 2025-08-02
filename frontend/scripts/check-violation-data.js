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

async function checkViolationData() {
  try {
    console.log('🔍 Checking violation history data...\n');

    // 1. Check if violation_history table has any records
    const violationCount = await prisma.violation_history.count();
    console.log(`📊 Total violation history records: ${violationCount}`);

    // 2. Check active violations in product_matches
    const activeViolations = await prisma.product_matches.count({
      where: { is_map_violation: true }
    });
    console.log(`⚠️  Active MAP violations: ${activeViolations}`);

    // 3. Get sample violations
    if (violationCount > 0) {
      const sampleViolations = await prisma.violation_history.findMany({
        take: 5,
        orderBy: { detected_at: 'desc' },
        include: {
          product_matches: {
            include: {
              idc_products: true,
              competitor_products: {
                include: {
                  competitors: true
                }
              }
            }
          }
        }
      });

      console.log('\n📋 Recent violations:');
      sampleViolations.forEach(v => {
        console.log(`\n- ${v.product_matches.idc_products.title}`);
        console.log(`  Date: ${v.detected_at}`);
        console.log(`  Competitor: ${v.product_matches.competitor_products.competitors.name}`);
        console.log(`  Violation: ${v.violation_percent.toFixed(2)}% below MAP`);
      });
    } else {
      console.log('\n❌ No violation history found!');
      console.log('Run "node scripts/scan-violations-now.js" to scan for violations');
    }

    // 4. Check if there are any price differences that could be violations
    const potentialViolations = await prisma.product_matches.findMany({
      where: {
        is_manual_match: true
      },
      include: {
        idc_products: true,
        competitor_products: true
      },
      take: 10
    });

    let violationsFound = 0;
    console.log('\n🔍 Checking manual matches for potential violations:');
    
    for (const match of potentialViolations) {
      const idcPrice = parseFloat(match.idc_products.price || 0);
      const compPrice = parseFloat(match.competitor_products.price || 0);
      
      if (idcPrice > 0 && compPrice > 0 && compPrice < idcPrice) {
        const pctBelow = ((idcPrice - compPrice) / idcPrice * 100).toFixed(2);
        console.log(`\n⚠️  VIOLATION: ${match.idc_products.title}`);
        console.log(`  MAP: $${idcPrice}, Competitor: $${compPrice}`);
        console.log(`  ${pctBelow}% below MAP`);
        violationsFound++;
      }
    }

    if (violationsFound === 0 && violationCount === 0) {
      console.log('\n✅ No violations found in manual matches either!');
      console.log('This suggests competitors are respecting MAP pricing.');
    }

  } catch (error) {
    console.error('❌ Error:', error);
  } finally {
    await prisma.$disconnect();
  }
}

checkViolationData();