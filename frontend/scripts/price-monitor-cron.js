#!/usr/bin/env node

import fetch from 'node-fetch';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment variables
dotenv.config({ path: path.join(__dirname, '..', '.env') });

// Configuration
const API_BASE = process.env.API_BASE_URL || 'http://localhost:5173/api/price-monitor';
const LOG_DIR = path.join(__dirname, '..', 'logs', 'price-monitor');
const LOG_FILE = path.join(LOG_DIR, `cron-${new Date().toISOString().split('T')[0]}.log`);
const ERROR_LOG = path.join(LOG_DIR, `cron-errors-${new Date().toISOString().split('T')[0]}.log`);

// Optional notifications
const SLACK_WEBHOOK_URL = process.env.SLACK_WEBHOOK_URL;
const EMAIL_RECIPIENT = process.env.PRICE_MONITOR_EMAIL;

// Create log directory
await fs.mkdir(LOG_DIR, { recursive: true });

// Logging functions
async function logMessage(message) {
  const timestamp = new Date().toISOString();
  const logLine = `[${timestamp}] ${message}\n`;
  console.log(logLine.trim());
  await fs.appendFile(LOG_FILE, logLine);
}

async function logError(message) {
  const timestamp = new Date().toISOString();
  const logLine = `[${timestamp}] ERROR: ${message}\n`;
  console.error(logLine.trim());
  await fs.appendFile(ERROR_LOG, logLine);
}

// Notification function
async function sendNotification(message, severity = 'info') {
  // Slack notification
  if (SLACK_WEBHOOK_URL) {
    try {
      await fetch(SLACK_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `Price Monitor Alert (${severity}): ${message}`,
          icon_emoji: severity === 'error' ? ':warning:' : ':information_source:'
        })
      });
    } catch (error) {
      await logError(`Failed to send Slack notification: ${error.message}`);
    }
  }
  
  // Log critical errors
  if (severity === 'error') {
    await logError(message);
  }
}

// API call wrapper
async function apiCall(method, endpoint, data = null, description) {
  await logMessage(`Calling ${description}: ${method} ${endpoint}`);
  
  try {
    const options = {
      method,
      headers: { 'Content-Type': 'application/json' }
    };
    
    if (data && method === 'POST') {
      options.body = JSON.stringify(data);
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    const result = await response.json();
    
    if (response.ok) {
      await logMessage(`✅ ${description} completed successfully`);
      return { success: true, data: result };
    } else {
      await logError(`${description} failed with HTTP ${response.status}: ${JSON.stringify(result)}`);
      await sendNotification(`${description} failed with HTTP ${response.status}`, 'error');
      return { success: false, error: result };
    }
  } catch (error) {
    await logError(`${description} failed: ${error.message}`);
    await sendNotification(`${description} failed: ${error.message}`, 'error');
    return { success: false, error: error.message };
  }
}

// Main execution
async function runPriceMonitorCron() {
  await logMessage('=========================================');
  await logMessage('Starting Price Monitor Cron Job');
  await logMessage('=========================================');
  
  const results = {
    overall_success: true,
    steps: []
  };
  
  // 1. Safe Sync Shopify Products
  await logMessage('📦 Step 1: Syncing Shopify products (SAFE mode - preserves manual matches)');
  const syncResult = await apiCall('POST', '/shopify-sync-safe/sync-idc-products-safe', 
    { force: true }, 'Shopify product sync');
  
  if (syncResult.success) {
    const { total_products_created, total_products_updated, manual_matches_preserved } = syncResult.data;
    await logMessage(`Sync results: ${total_products_created} created, ${total_products_updated} updated, ${manual_matches_preserved} manual matches preserved`);
    results.steps.push({ step: 'shopify_sync', ...syncResult.data });
  } else {
    results.overall_success = false;
  }
  
  // 2. Scrape Competitor Prices
  await logMessage('🔍 Step 2: Scraping competitor prices');
  const scrapeResult = await apiCall('POST', '/scraping/scrape-all', {}, 'Competitor price scraping');
  
  if (scrapeResult.success) {
    const { total_products_scraped } = scrapeResult.data;
    await logMessage(`Scraped ${total_products_scraped || 0} products from competitors`);
    results.steps.push({ step: 'competitor_scraping', ...scrapeResult.data });
  } else {
    results.overall_success = false;
  }
  
  // 3. Generate Product Matches
  await logMessage('🔗 Step 3: Generating product matches for new products');
  const matchResult = await apiCall('POST', '/product-matching/generate-matches', 
    { only_unmatched: true }, 'Product matching');
  
  if (matchResult.success) {
    const { matches_created } = matchResult.data;
    await logMessage(`Created ${matches_created || 0} new product matches`);
    results.steps.push({ step: 'product_matching', ...matchResult.data });
  } else {
    results.overall_success = false;
  }
  
  // 4. Scan for MAP Violations
  await logMessage('⚠️  Step 4: Scanning for MAP violations');
  const violationResult = await apiCall('POST', '/violation-history/scan-and-record', 
    { record_history: true, dry_run: false }, 'MAP violation scan');
  
  if (violationResult.success) {
    const { violations_found, history_recorded } = violationResult.data;
    await logMessage(`Found ${violations_found} violations, recorded ${history_recorded} in history`);
    results.steps.push({ step: 'violation_scan', ...violationResult.data });
    
    // Send notification if violations found
    if (violations_found > 0) {
      await sendNotification(`Found ${violations_found} MAP violations`, 'warning');
    }
  } else {
    results.overall_success = false;
  }
  
  // 5. Generate Statistics
  await logMessage('📊 Step 5: Generating violation statistics');
  const statsResult = await apiCall('GET', '/violation-history/statistics?group_by=day', 
    null, 'Violation statistics');
  
  if (statsResult.success) {
    const { summary } = statsResult.data;
    await logMessage(`Currently ${summary.active_violations} active violations`);
    results.steps.push({ step: 'statistics', ...summary });
  }
  
  // 6. System Health Check
  await logMessage('🏥 Step 6: Checking system health');
  const healthResult = await apiCall('GET', '/health', null, 'System health check');
  
  if (!healthResult.success) {
    results.overall_success = false;
    await sendNotification('Price monitor health check failed!', 'error');
  }
  
  // 7. Clean up old logs
  await logMessage('🧹 Step 7: Cleaning up old logs');
  const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
  
  try {
    const files = await fs.readdir(LOG_DIR);
    let cleaned = 0;
    
    for (const file of files) {
      if (file.startsWith('cron-') && file.endsWith('.log')) {
        const filePath = path.join(LOG_DIR, file);
        const stats = await fs.stat(filePath);
        
        if (stats.mtimeMs < thirtyDaysAgo) {
          await fs.unlink(filePath);
          cleaned++;
        }
      }
    }
    
    await logMessage(`Cleaned up ${cleaned} old log files`);
  } catch (error) {
    await logError(`Failed to clean up logs: ${error.message}`);
  }
  
  // Summary
  await logMessage('=========================================');
  if (results.overall_success) {
    await logMessage('✅ Price Monitor Cron Job completed successfully');
    
    // Save summary report
    const summaryPath = path.join(LOG_DIR, 'last-run-summary.json');
    await fs.writeFile(summaryPath, JSON.stringify({
      timestamp: new Date().toISOString(),
      success: true,
      results: results.steps
    }, null, 2));
  } else {
    await logMessage('⚠️  Price Monitor Cron Job completed with errors');
    await sendNotification('Price monitor cron job completed with errors - check logs', 'error');
  }
  
  process.exit(results.overall_success ? 0 : 1);
}

// Run the cron job
runPriceMonitorCron().catch(async (error) => {
  await logError(`Cron job failed: ${error.message}`);
  await sendNotification(`Price monitor cron job crashed: ${error.message}`, 'error');
  process.exit(1);
});