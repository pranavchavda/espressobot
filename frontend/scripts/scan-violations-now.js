#!/usr/bin/env node

import fetch from 'node-fetch';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables
dotenv.config({ path: join(__dirname, '..', '.env') });

const API_BASE = 'http://localhost:5173/api/price-monitor';

async function scanViolations() {
  console.log('🔍 Scanning for MAP violations and recording history...\n');

  try {
    // Scan and record violations
    const response = await fetch(`${API_BASE}/violation-history/scan-and-record`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        brands: ['Profitec', 'Eureka'],
        record_history: true,
        dry_run: false
      })
    });

    if (response.ok) {
      const result = await response.json();
      console.log('✅ Scan complete:', {
        total_scanned: result.total_matches_scanned,
        violations_found: result.violations_found,
        history_recorded: result.history_recorded,
        by_severity: result.by_severity
      });

      if (result.violations.length > 0) {
        console.log('\n📋 Violations found:');
        result.violations.forEach(v => {
          console.log(`\n- ${v.idc_product.title} (${v.idc_product.vendor})`);
          console.log(`  MAP: $${v.idc_product.price}`);
          console.log(`  ${v.competitor_product.competitor}: $${v.competitor_product.price}`);
          console.log(`  Violation: ${v.violation.percentage}% below MAP (${v.violation.severity})`);
          console.log(`  Status: ${v.is_new ? 'NEW' : v.price_changed ? 'PRICE CHANGED' : 'EXISTING'}`);
        });
      } else {
        console.log('\n✅ No violations found - all products are at or above MAP!');
      }
    } else {
      console.error('❌ Scan failed:', await response.text());
    }

  } catch (error) {
    console.error('❌ Error:', error);
  }
}

// Run the scan
scanViolations();