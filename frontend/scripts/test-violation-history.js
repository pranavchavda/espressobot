#!/usr/bin/env node

import fetch from 'node-fetch';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables
dotenv.config({ path: join(__dirname, '..', '.env') });

const API_BASE = 'http://localhost:5173/api/price-monitor/violation-history';

async function testViolationHistory() {
  console.log('🧪 Testing Violation History API...\n');

  try {
    // 1. Scan and record violations
    console.log('1️⃣ Scanning for violations and recording history...');
    const scanResponse = await fetch(`${API_BASE}/scan-and-record`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brands: ['Profitec', 'Eureka'],
        record_history: true,
        dry_run: false
      })
    });

    const scanResult = await scanResponse.json();
    console.log(`✅ Scan complete:`, {
      total_scanned: scanResult.total_matches_scanned,
      violations_found: scanResult.violations_found,
      history_recorded: scanResult.history_recorded,
      by_severity: scanResult.by_severity
    });

    if (scanResult.violations.length > 0) {
      console.log('\n📋 Sample violations:');
      scanResult.violations.slice(0, 3).forEach(v => {
        console.log(`  - ${v.idc_product.title}`);
        console.log(`    MAP: $${v.idc_product.price}, Competitor: $${v.competitor_product.price}`);
        console.log(`    Violation: ${v.violation.percentage}% below MAP (${v.violation.severity})`);
        console.log(`    At: ${v.competitor_product.competitor}`);
      });
    }

    // 2. Get violation history for a specific product
    if (scanResult.violations.length > 0) {
      const sampleMatchId = scanResult.violations[0].match_id;
      
      console.log('\n2️⃣ Getting violation history for product match:', sampleMatchId);
      const historyResponse = await fetch(`${API_BASE}/history/${sampleMatchId}`);
      const historyResult = await historyResponse.json();

      console.log(`✅ History entries: ${historyResult.pagination.total}`);
      if (historyResult.history.length > 0) {
        console.log('\n📜 Recent history:');
        historyResult.history.slice(0, 5).forEach(h => {
          console.log(`  - ${new Date(h.detected_at).toLocaleString()}`);
          console.log(`    Price: $${h.competitor_price} (${h.violation_percent.toFixed(2)}% below MAP)`);
          if (h.price_change) {
            console.log(`    Change: $${h.price_change > 0 ? '+' : ''}${h.price_change.toFixed(2)}`);
          }
          console.log(`    Notes: ${h.notes || 'None'}`);
        });
      }
    }

    // 3. Get aggregated statistics
    console.log('\n3️⃣ Getting violation statistics...');
    const statsResponse = await fetch(`${API_BASE}/statistics?group_by=day`);
    const statsResult = await statsResponse.json();

    console.log(`✅ Violation Statistics:`);
    console.log(`  - Total violations: ${statsResult.summary.total_violations}`);
    console.log(`  - Active violations: ${statsResult.summary.active_violations}`);
    console.log(`  - Average violation: ${statsResult.summary.average_violation_percent?.toFixed(2)}%`);
    console.log(`  - Max violation: ${statsResult.summary.max_violation_percent?.toFixed(2)}%`);

    if (statsResult.by_type.length > 0) {
      console.log('\n📊 By violation type:');
      statsResult.by_type.forEach(t => {
        console.log(`  - ${t.violation_type}: ${t._count.id} violations`);
        console.log(`    Avg: ${t._avg.violation_percent?.toFixed(2)}%, Total impact: $${t._sum.violation_amount?.toFixed(2)}`);
      });
    }

    // 4. Test CSV export
    console.log('\n4️⃣ Testing CSV export...');
    const exportResponse = await fetch(`${API_BASE}/export?format=csv`);
    
    if (exportResponse.ok) {
      const contentType = exportResponse.headers.get('content-type');
      const contentDisposition = exportResponse.headers.get('content-disposition');
      console.log(`✅ CSV export available:`, {
        contentType,
        filename: contentDisposition?.match(/filename="(.+)"/)?.[1]
      });
    }

    console.log('\n✅ All tests completed successfully!');

  } catch (error) {
    console.error('❌ Test failed:', error);
    process.exit(1);
  }
}

// Run the test
testViolationHistory();