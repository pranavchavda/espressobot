import { buildTieredContext, buildCoreContext, buildFullContext, requiresFullContext } from '../context/tiered-context-builder.js';
import { stripProductKeys, estimateSizeReduction } from '../context/product-key-stripper.js';

console.log('=== Testing Tiered Context System ===\n');

// Test 1: Heuristic detection
console.log('1. Testing heuristic detection:');
const testCases = [
  { task: 'Update price for SKU ESP-1001 to $49.99', expectFull: false },
  { task: 'Process bulk update for 150 products', expectFull: true },
  { task: 'Export complete catalog as JSON', expectFull: true },
  { task: 'Get product details for mexican-altura', expectFull: false },
  { task: 'Update all products in coffee category', expectFull: true },
  { task: 'Simple price check', expectFull: false },
  { task: 'Create new product', userMessage: '{"products": [' + 'x'.repeat(6000) + ']}', expectFull: true }
];

for (const { task, userMessage = '', expectFull } of testCases) {
  const needsFull = requiresFullContext(task, userMessage);
  const status = needsFull === expectFull ? '✓' : '✗';
  console.log(`  ${status} "${task.substring(0, 50)}..." → ${needsFull ? 'FULL' : 'CORE'} (expected: ${expectFull ? 'FULL' : 'CORE'})`);
}

// Test 2: Context size comparison
console.log('\n2. Testing context size reduction:');
async function testContextSizes() {
  const testTask = 'Update prices for products ESP-1001, BRE-2002, MIE-3003';
  
  try {
    // Build core context
    console.log('  Building CORE context...');
    const coreContext = await buildCoreContext({
      task: testTask,
      conversationId: 'test-123',
      userId: '2',
      userMessage: testTask,
      autonomyLevel: 'high',
      conversationHistory: ['User: previous message', 'Assistant: response']
    });
    
    const coreSize = JSON.stringify(coreContext).length;
    console.log(`  Core context size: ${Math.round(coreSize / 1024)}KB`);
    
    // Build full context
    console.log('  Building FULL context...');
    const fullContext = await buildFullContext({
      task: testTask,
      conversationId: 'test-123',
      userId: '2',
      userMessage: testTask,
      autonomyLevel: 'high',
      conversationHistory: ['User: previous message', 'Assistant: response']
    });
    
    const fullSize = JSON.stringify(fullContext).length;
    console.log(`  Full context size: ${Math.round(fullSize / 1024)}KB`);
    
    const reduction = Math.round(((fullSize - coreSize) / fullSize) * 100);
    console.log(`  Size reduction: ${reduction}% smaller with core context`);
    
  } catch (error) {
    console.log(`  Error: ${error.message}`);
  }
}

// Test 3: Product key stripping
console.log('\n3. Testing product key stripping:');
const sampleProduct = {
  id: 'gid://shopify/Product/123',
  title: 'Test Coffee',
  handle: 'test-coffee',
  sku: 'ESP-1001',
  vendor: 'Test Brand',
  productType: 'Coffee',
  status: 'active',
  price: '19.99',
  compareAtPrice: '24.99',
  tags: ['coffee', 'espresso'],
  descriptionHtml: '<p>Great coffee</p>',
  inventoryQuantity: 100,
  inventoryPolicy: 'DENY',
  
  // Unused fields that will be stripped
  admin_graphql_api_id: 'gid://shopify/Product/123',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
  published_at: '2024-01-01T00:00:00Z',
  templateSuffix: '',
  publishedScope: 'web',
  legacyResourceId: 123456,
  onlineStoreUrl: 'https://store.com/products/test',
  availableForSale: true,
  sellingPlanGroups: [],
  tracksInventory: true,
  harmonizedSystemCode: '0901210000',
  originCountry: 'CO',
  
  variants: [{
    id: 'gid://shopify/ProductVariant/456',
    title: 'Default',
    sku: 'ESP-1001',
    price: '19.99',
    inventoryQuantity: 100,
    // Unused variant fields
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    taxable: true,
    taxCode: '',
    fulfillmentService: 'manual'
  }]
};

const strippedProduct = stripProductKeys(sampleProduct);
const reduction = estimateSizeReduction(sampleProduct);

console.log(`  Original product keys: ${Object.keys(sampleProduct).length}`);
console.log(`  Stripped product keys: ${Object.keys(strippedProduct).length}`);
console.log(`  Size reduction: ${reduction.percentage}% (${reduction.original} → ${reduction.stripped} bytes)`);
console.log(`  Removed keys: ${Object.keys(sampleProduct).filter(k => !(k in strippedProduct)).join(', ')}`);

// Test 4: Auto tier selection
console.log('\n4. Testing automatic tier selection:');
async function testAutoTierSelection() {
  const scenarios = [
    { task: 'Get price for ESP-1001', forceFullContext: false },
    { task: 'Update 200 products with new prices', forceFullContext: false },
    { task: 'Simple query', forceFullContext: true } // Force full to test override
  ];
  
  for (const { task, forceFullContext } of scenarios) {
    try {
      const context = await buildTieredContext({
        task,
        conversationId: 'test-456',
        userId: '2',
        forceFullContext
      });
      
      console.log(`  "${task}" → ${context.fullSlice ? 'FULL' : 'CORE'} slice${forceFullContext ? ' (forced)' : ''}`);
    } catch (error) {
      console.log(`  Error with "${task}": ${error.message}`);
    }
  }
}

// Run async tests
(async () => {
  await testContextSizes();
  await testAutoTierSelection();
  console.log('\n=== All tests completed ===');
})();