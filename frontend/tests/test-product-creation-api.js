#!/usr/bin/env node

console.log('🧪 Product Creation API Test Suite\n');

const fetch = (await import('node-fetch')).default;

// Helper to make API calls and capture events
async function callAPI(message, verbose = false) {
  console.log(`📝 Testing: "${message}"`);
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    let events = [];
    let finalResponse = null;
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      
      if (line.startsWith('event: ')) {
        const eventType = line.substring(7);
        const dataLine = lines[i + 1];
        
        if (dataLine && dataLine.startsWith('data: ')) {
          try {
            const data = JSON.parse(dataLine.substring(6));
            events.push({ type: eventType, data });
            
            if (eventType === 'done') {
              finalResponse = data.finalResponse;
            }
          } catch (e) {
            // Ignore parse errors
          }
        }
      }
    }
    
    // Extract key information
    const handoffs = events.filter(e => e.type === 'handoff');
    const toolCalls = events.filter(e => e.type === 'tool_call');
    const errors = events.filter(e => e.type === 'error');
    
    if (verbose) {
      console.log('  Handoffs:', handoffs.map(h => `${h.data.from} → ${h.data.to}`).join(', '));
      console.log('  Tools used:', toolCalls.map(t => t.data.tool).join(', '));
    }
    
    if (errors.length > 0) {
      console.log('  ❌ Errors:', errors.map(e => e.data.message).join('; '));
    }
    
    if (finalResponse) {
      // Extract product ID if created
      const idMatch = finalResponse.match(/gid:\/\/shopify\/Product\/(\d+)/);
      if (idMatch) {
        console.log('  ✅ Product created:', idMatch[0]);
      } else {
        console.log('  Response preview:', finalResponse.substring(0, 100) + '...');
      }
    }
    
    return { events, finalResponse, success: errors.length === 0 };
    
  } catch (error) {
    console.log('  ❌ API Error:', error.message);
    return { events: [], finalResponse: null, success: false };
  }
}

// Test suite
async function runTests() {
  console.log('Starting Product Creation Tests...\n');
  
  // Test 1: Simple product creation
  console.log('=== Test 1: Simple Product Creation ===');
  await callAPI(
    "Create a product called 'TEST API Product 001' with vendor 'Test Vendor' and type 'Test Equipment'",
    true
  );
  console.log();
  
  // Test 2: Product with price and SKU
  console.log('=== Test 2: Product with Price and SKU ===');
  await callAPI(
    "Create a product titled 'TEST API Coffee Maker' with vendor 'Test Brand', type 'Coffee Equipment', price $99.99, and SKU TEST-API-001",
    true
  );
  console.log();
  
  // Test 3: Product with inventory
  console.log('=== Test 3: Product with Inventory ===');
  await callAPI(
    "Create a product 'TEST API Grinder' vendor 'Test Co', type 'Grinders', price $199, SKU TEST-GR-001, with 50 units in stock",
    true
  );
  console.log();
  
  // Test 4: Full product with all details
  console.log('=== Test 4: Full Product Creation ===');
  await callAPI(
    "Create a product with title 'TEST API Espresso Machine', vendor 'Test Machines Inc', type 'Espresso Machines', " +
    "description 'A test espresso machine for API testing', price $599.99, compare at price $799.99, " +
    "SKU TEST-ESP-001, barcode 123456789012, weight 15 kg, 25 units in stock, tags: test, api, espresso",
    true
  );
  console.log();
  
  // Test 5: Product with SEO
  console.log('=== Test 5: Product with SEO ===');
  await callAPI(
    "Create 'TEST API SEO Product' by 'Test Vendor', type 'Test Type', with SEO title 'Best Test Product' " +
    "and SEO description 'This is the best test product for API testing'",
    true
  );
  console.log();
  
  // Test 6: Draft vs Active status
  console.log('=== Test 6: Draft Product ===');
  await callAPI(
    "Create a DRAFT product 'TEST API Draft Item' vendor 'Test', type 'Equipment', keep it as draft",
    true
  );
  console.log();
  
  // Test 7: Product with images
  console.log('=== Test 7: Product with Images (URL) ===');
  await callAPI(
    "Create product 'TEST API Image Product' vendor 'Test', type 'Equipment', " +
    "with image https://via.placeholder.com/500x500.png?text=Test+Product",
    true
  );
  console.log();
  
  // Test 8: Edge cases
  console.log('=== Test 8: Edge Cases ===');
  
  // Missing required fields
  await callAPI("Create a product with just a title 'TEST Minimal Product'");
  console.log();
  
  // Special characters
  await callAPI(
    "Create product 'TEST Special Chars & Symbols!' vendor 'Test & Co.' type 'Type/Category'",
    true
  );
  console.log();
  
  // Test 9: Combo product
  console.log('=== Test 9: Combo Product Creation ===');
  await callAPI(
    "Create a combo of products with SKUs TEST-API-001 and TEST-GR-001 with 10% discount",
    true
  );
  console.log();
  
  // Test 10: Open box product
  console.log('=== Test 10: Open Box Creation ===');
  await callAPI(
    "Create an open box version of product with SKU TEST-ESP-001 at 20% discount",
    true
  );
  console.log();
}

// Summary function
async function testSummary() {
  console.log('\n=== Testing Tool Error Patterns ===\n');
  
  // These should trigger specific errors to help identify parameter issues
  const errorTests = [
    {
      name: "Invalid product type format",
      query: "Create product 'ERROR TEST 1' vendor 'Test' with invalid type parameter"
    },
    {
      name: "Missing vendor",
      query: "Create product 'ERROR TEST 2' type 'Test Type' without vendor"
    },
    {
      name: "Invalid price format",
      query: "Create product 'ERROR TEST 3' vendor 'Test' type 'Test' price 'invalid-price'"
    }
  ];
  
  for (const test of errorTests) {
    console.log(`Testing: ${test.name}`);
    const result = await callAPI(test.query);
    console.log();
  }
}

// Run all tests
console.log('🚀 Starting EspressoBot Product Creation API Tests\n');
console.log('Make sure the server is running on http://localhost:5173\n');

await runTests();
await testSummary();

console.log('\n✅ Test suite completed!');