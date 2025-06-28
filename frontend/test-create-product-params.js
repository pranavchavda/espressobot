#!/usr/bin/env node

console.log('🔍 Testing create_product Parameter Mapping\n');

const fetch = (await import('node-fetch')).default;

// Test specific parameter combinations
async function testParameters() {
  const tests = [
    {
      name: "Basic required fields only",
      message: "Create a product with title 'PARAM TEST 1', vendor 'Test Vendor', and product type 'Test Type'"
    },
    {
      name: "With inventory_quantity",
      message: "Create product 'PARAM TEST 2', vendor 'Test', type 'Equipment', with 100 units in stock"
    },
    {
      name: "With price and SKU",
      message: "Create 'PARAM TEST 3' by 'Test Vendor', type 'Test', price $49.99, SKU PARAM-003"
    },
    {
      name: "Full parameters",
      message: "Create product: title 'PARAM TEST 4', vendor 'Test Co', product_type 'Machines', " +
               "description 'Test description', price $299, sku PARAM-004, barcode 123456, " +
               "weight 5kg, inventory 50 units, track inventory true, status DRAFT"
    },
    {
      name: "Using 'coffee maker' example",
      message: "Create a coffee maker product 'PARAM Coffee Maker' by 'Test Brand' with 100 units inventory"
    }
  ];
  
  for (const test of tests) {
    console.log(`\n📋 ${test.name}`);
    console.log(`Query: "${test.message}"`);
    
    try {
      const response = await fetch('http://localhost:5173/api/agent/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: test.message })
      });
      
      const text = await response.text();
      const lines = text.split('\n');
      
      // Look for tool_call events
      let toolCallFound = false;
      let errorFound = false;
      
      for (let i = 0; i < lines.length; i++) {
        if (lines[i] === 'event: tool_call' && lines[i+1]?.startsWith('data: ')) {
          const data = JSON.parse(lines[i+1].substring(6));
          if (data.tool === 'create_product') {
            toolCallFound = true;
            console.log('✅ Tool called with args:', JSON.stringify(data.args, null, 2));
          }
        }
        
        if (lines[i] === 'event: error' && lines[i+1]?.startsWith('data: ')) {
          const data = JSON.parse(lines[i+1].substring(6));
          errorFound = true;
          console.log('❌ Error:', data.message);
          if (data.details) {
            console.log('   Details:', data.details);
          }
        }
      }
      
      if (!toolCallFound && !errorFound) {
        // Check final response
        for (let i = lines.length - 1; i >= 0; i--) {
          if (lines[i] === 'event: done' && lines[i+1]?.startsWith('data: ')) {
            const data = JSON.parse(lines[i+1].substring(6));
            const response = data.finalResponse || '';
            
            // Check if handoff occurred
            if (response.includes('Product_Creation_Agent')) {
              console.log('🔄 Handoff to Product_Creation_Agent detected');
            }
            
            // Check for success
            if (response.includes('gid://shopify/Product/')) {
              console.log('✅ Product created successfully');
            } else if (response.includes('error') || response.includes('Error')) {
              console.log('❌ Response indicates error:', response.substring(0, 200));
            } else {
              console.log('📝 Response:', response.substring(0, 150) + '...');
            }
            break;
          }
        }
      }
      
    } catch (error) {
      console.log('❌ Request failed:', error.message);
    }
  }
}

// Direct parameter test
async function testDirectParameters() {
  console.log('\n\n=== Direct Parameter Mapping Test ===\n');
  
  // This tests the exact parameter names expected by the Python script
  const directTest = {
    title: "DIRECT PARAM TEST",
    vendor: "Direct Test Vendor", 
    product_type: "Direct Type",
    price: "99.99",
    sku: "DIRECT-001",
    inventory_quantity: 50
  };
  
  console.log('Sending request with explicit parameters:');
  console.log(JSON.stringify(directTest, null, 2));
  
  const message = `Create a product with these exact parameters: ${JSON.stringify(directTest)}`;
  
  const response = await fetch('http://localhost:5173/api/agent/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  const text = await response.text();
  console.log('\nChecking tool execution...');
  
  // Parse and analyze response
  const lines = text.split('\n');
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes('tool_call') || lines[i].includes('error')) {
      console.log(lines[i]);
      if (lines[i+1]?.startsWith('data: ')) {
        console.log(lines[i+1]);
      }
    }
  }
}

// Run tests
console.log('🚀 Testing create_product parameter mapping through API\n');
console.log('Server should be running on http://localhost:5173\n');

await testParameters();
await testDirectParameters();

console.log('\n\n✅ Parameter mapping tests completed!');