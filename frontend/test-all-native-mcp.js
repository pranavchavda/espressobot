#!/usr/bin/env node

import { callMCPTool } from './server/tools/mcp-client.js';

async function testAllNativeMCP() {
  console.log('🚀 Testing All Native MCP Tools\n');
  
  const nativeTools = [
    'get_product',
    'search_products',
    'create_product', 
    'manage_tags',
    'add_product_images',
    'add_variants_to_product',
    'create_full_product',
    'update_full_product'
  ];
  
  console.log(`Found ${nativeTools.length} native tools to test\n`);
  
  let passed = 0;
  let failed = 0;
  const results = [];
  
  for (const toolName of nativeTools) {
    console.log(`\n=== Testing ${toolName} ===`);
    
    try {
      const startTime = Date.now();
      
      // Test with minimal safe parameters
      let testArgs = {};
      switch (toolName) {
        case 'get_product':
          testArgs = { identifier: 'nonexistent-test' };
          break;
        case 'search_products':
          testArgs = { query: 'test', limit: 1 };
          break;
        case 'create_product':
          testArgs = { 
            title: 'Test Product', 
            vendor: 'Test Vendor',
            product_type: 'Test Type'
          };
          break;
        case 'manage_tags':
          testArgs = {
            product: 'test-product',
            tags: 'test,native',
            action: 'add'
          };
          break;
        case 'add_product_images':
          testArgs = {
            product_identifier: 'test-product',
            image_urls: ['https://example.com/test.jpg']
          };
          break;
        case 'add_variants_to_product':
          testArgs = {
            product_identifier: 'test-product',
            variants: [{ price: 99.99, sku: 'TEST-001' }]
          };
          break;
        case 'create_full_product':
          testArgs = {
            title: 'Test Full Product',
            vendor: 'Test Vendor',
            product_type: 'Test Type',
            handle: 'test-full-product'
          };
          break;
        case 'update_full_product':
          testArgs = {
            identifier: 'test-product',
            updates: { title: 'Updated Test Product' }
          };
          break;
      }
      
      const result = await callMCPTool(toolName, testArgs);
      const duration = Date.now() - startTime;
      
      console.log(`✅ Completed in ${duration}ms`);
      
      // Check for expected vs unexpected errors
      const isExpectedError = result.success === false && (
        result.error?.includes('not found') ||
        result.error?.includes('Invalid vendor') ||
        result.error?.includes('Could not find')
      );
      
      if (result.success || isExpectedError) {
        console.log('   Status: Native implementation working correctly');
        passed++;
        results.push({ tool: toolName, status: 'passed', duration, result: isExpectedError ? 'expected_error' : 'success' });
      } else {
        console.log('   Status: Unexpected error');
        console.log('   Error:', result.error);
        failed++;
        results.push({ tool: toolName, status: 'failed', duration, error: result.error });
      }
      
    } catch (error) {
      const duration = Date.now() - Date.now();
      console.log(`❌ Exception: ${error.message}`);
      failed++;
      results.push({ tool: toolName, status: 'exception', duration, error: error.message });
    }
  }
  
  console.log('\n\n📊 === TEST SUMMARY ===');
  console.log(`Total tools tested: ${nativeTools.length}`);
  console.log(`Native implementations working: ${passed}`);
  console.log(`Failed: ${failed}`);
  console.log(`Success rate: ${Math.round((passed / nativeTools.length) * 100)}%\n`);
  
  // Performance summary
  const durations = results.filter(r => r.duration).map(r => r.duration);
  if (durations.length > 0) {
    const avgDuration = Math.round(durations.reduce((a, b) => a + b, 0) / durations.length);
    const maxDuration = Math.max(...durations);
    const minDuration = Math.min(...durations);
    
    console.log('⚡ Performance Summary:');
    console.log(`   Average execution time: ${avgDuration}ms`);
    console.log(`   Fastest: ${minDuration}ms`);
    console.log(`   Slowest: ${maxDuration}ms`);
    console.log('   (Note: Includes expected errors from test data)\n');
  }
  
  // Detailed results
  console.log('📋 Detailed Results:');
  results.forEach(result => {
    const icon = result.status === 'passed' ? '✅' : result.status === 'failed' ? '❌' : '⚠️';
    console.log(`   ${icon} ${result.tool}: ${result.status} (${result.duration}ms)`);
  });
  
  process.exit(failed > 0 ? 1 : 0);
}

testAllNativeMCP().catch(console.error);