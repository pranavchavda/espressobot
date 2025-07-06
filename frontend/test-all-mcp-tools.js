#!/usr/bin/env node

import { callMCPTool } from './server/tools/mcp-client.js';

async function testAllMCPTools() {
  console.log('Testing all 8 MCP tools...\n');
  
  const tests = [
    {
      name: 'get_product',
      description: 'Get product by SKU',
      args: { identifier: 'TST-001' },
    },
    {
      name: 'search_products',
      description: 'Search products with filters',
      args: { query: 'test', status: 'active', limit: 5 },
    },
    {
      name: 'manage_inventory_policy',
      description: 'Set inventory policy',
      args: { identifier: '12345', policy: 'deny' },
    },
    {
      name: 'update_pricing',
      description: 'Update single product price',
      args: { sku: 'TST-001', price: 99.99, compare_at_price: 129.99 },
    },
    {
      name: 'create_product',
      description: 'Create new product',
      args: {
        title: 'Test Product',
        sku: 'TST-NEW-001',
        price: 49.99,
        vendor: 'Test Vendor',
        product_type: 'Test Type',
        status: 'draft'
      },
    },
    {
      name: 'update_status',
      description: 'Update product status',
      args: { sku: 'TST-001', status: 'active' },
    },
    {
      name: 'manage_tags',
      description: 'Add tags to product',
      args: { sku: 'TST-001', tags: ['test', 'sample'], operation: 'add' },
    },
    {
      name: 'bulk_price_update',
      description: 'Update multiple product prices',
      args: {
        updates: [
          { sku: 'TST-001', price: 89.99 },
          { sku: 'TST-002', price: 79.99, compare_at_price: 99.99 }
        ]
      },
    },
  ];

  let passed = 0;
  let failed = 0;

  for (const test of tests) {
    console.log(`\n${test.name}: ${test.description}`);
    console.log('Args:', JSON.stringify(test.args, null, 2));
    
    try {
      const startTime = Date.now();
      const result = await callMCPTool(test.name, test.args);
      const duration = Date.now() - startTime;
      
      console.log(`✅ Success (${duration}ms)`);
      console.log('Result:', JSON.stringify(result, null, 2).slice(0, 200));
      passed++;
      
    } catch (error) {
      console.log(`❌ Failed: ${error.message}`);
      failed++;
    }
  }

  console.log(`\n\nTest Summary: ${passed} passed, ${failed} failed`);
  
  // Test error handling
  console.log('\n--- Testing Error Handling ---');
  
  try {
    console.log('\nTesting invalid tool name...');
    await callMCPTool('invalid_tool', {});
    console.log('❌ Should have thrown error');
  } catch (error) {
    console.log('✅ Correctly rejected invalid tool');
  }

  try {
    console.log('\nTesting missing required args...');
    await callMCPTool('update_pricing', { price: 100 }); // Missing SKU
    console.log('❌ Should have thrown error');
  } catch (error) {
    console.log('✅ Correctly rejected missing args');
  }

  process.exit(failed > 0 ? 1 : 0);
}

testAllMCPTools().catch(console.error);