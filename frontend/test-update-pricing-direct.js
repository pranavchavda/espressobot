#!/usr/bin/env node

console.log('🔧 Testing Update Pricing Directly\n');

import PythonToolWrapper from './server/custom-tools/python-tool-wrapper.js';

const wrapper = new PythonToolWrapper();

// First, let's get a product to find its variant ID
console.log('1. Getting product info for UPDATE-TEST-001...');
try {
  const productInfo = await wrapper.executeTool('get_product', {}, ['UPDATE-TEST-001']);
  console.log('Product found:', typeof productInfo === 'string' ? productInfo.substring(0, 200) : productInfo);
  
  // Parse to get IDs if it's JSON
  if (typeof productInfo === 'object' && productInfo.data) {
    const product = productInfo.data.product;
    if (product && product.variants && product.variants.edges.length > 0) {
      const productId = product.id.split('/').pop();
      const variantId = product.variants.edges[0].node.id.split('/').pop();
      
      console.log('\n2. Found IDs:');
      console.log('   Product ID:', productId);
      console.log('   Variant ID:', variantId);
      
      console.log('\n3. Updating price...');
      const updateResult = await wrapper.executeTool('update_pricing', {
        'product-id': productId,
        'variant-id': variantId,
        'price': '75.00'
      });
      
      console.log('Update result:', updateResult);
    }
  }
} catch (error) {
  console.error('Error:', error.message);
}

// Try the bulk price update instead
console.log('\n4. Testing bulk_price_update as alternative...');
try {
  // Create a simple CSV data
  const updates = [
    { identifier: 'UPDATE-TEST-001', price: '65.00' }
  ];
  
  // Note: bulk_price_update expects a CSV file, not inline data
  console.log('Note: bulk_price_update requires a CSV file, cannot test inline');
} catch (error) {
  console.error('Error:', error.message);
}

console.log('\n✅ Direct test completed!');