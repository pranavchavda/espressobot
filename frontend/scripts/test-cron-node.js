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

async function testCronEndpoints() {
  console.log('🧪 Testing Price Monitor Cron Endpoints');
  console.log('=======================================\n');

  const tests = [
    {
      name: 'Shopify sync (limited)',
      method: 'POST',
      endpoint: '/shopify-sync-safe/sync-idc-products-safe',
      body: { force: true, brands: ['Eureka'], limit: 5 }
    },
    {
      name: 'Competitor scraping',
      method: 'POST',
      endpoint: '/scraping/scrape-all',
      body: { limit: 5 }
    },
    {
      name: 'Violation scan',
      method: 'POST',
      endpoint: '/violation-history/scan-and-record',
      body: { record_history: true, dry_run: true }
    },
    {
      name: 'Violation statistics',
      method: 'GET',
      endpoint: '/violation-history/statistics?group_by=day'
    },
    {
      name: 'Health check',
      method: 'GET',
      endpoint: '/health'
    }
  ];

  for (const test of tests) {
    process.stdout.write(`Testing ${test.name}... `);
    
    try {
      const options = {
        method: test.method,
        headers: test.method === 'POST' ? { 'Content-Type': 'application/json' } : {}
      };
      
      if (test.body) {
        options.body = JSON.stringify(test.body);
      }
      
      const response = await fetch(`${API_BASE}${test.endpoint}`, options);
      
      if (response.ok) {
        const data = await response.json();
        console.log(`✅ OK (HTTP ${response.status})`);
        
        // Show relevant results
        if (test.name === 'Violation statistics' && data.summary) {
          console.log(`  - Total violations: ${data.summary.total_violations}`);
          console.log(`  - Active violations: ${data.summary.active_violations}`);
          console.log(`  - Avg violation: ${data.summary.average_violation_percent?.toFixed(1)}%`);
        } else if (test.name === 'Violation scan' && data.violations_found !== undefined) {
          console.log(`  - Violations found: ${data.violations_found}`);
          console.log(`  - By severity:`, data.by_severity);
        }
      } else {
        console.log(`❌ Failed (HTTP ${response.status})`);
      }
    } catch (error) {
      console.log(`❌ Error: ${error.message}`);
    }
  }

  console.log('\n=======================================');
  console.log('✅ Test complete!\n');
  console.log('To run the full cron job:');
  console.log('  ./scripts/price-monitor-cron.sh\n');
  console.log('To set up as a cron job, add to crontab:');
  console.log('  # Run every 4 hours');
  console.log('  0 */4 * * * /home/pranav/espressobot/frontend/scripts/price-monitor-cron.sh');
}

// Run the test
testCronEndpoints().catch(console.error);