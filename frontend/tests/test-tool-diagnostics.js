#!/usr/bin/env node

console.log('🔧 Tool Execution Diagnostics\n');

const fetch = (await import('node-fetch')).default;

// Simple API call that captures all events
async function diagnoseToolCall(message) {
  console.log(`Query: "${message}"\n`);
  
  const response = await fetch('http://localhost:5173/api/agent/run', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });
  
  const text = await response.text();
  const lines = text.split('\n');
  
  // Track the flow
  const events = {
    handoffs: [],
    toolCalls: [],
    errors: [],
    agentMessages: []
  };
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    if (line.startsWith('event: ')) {
      const eventType = line.substring(7);
      const dataLine = lines[i + 1];
      
      if (dataLine && dataLine.startsWith('data: ')) {
        try {
          const data = JSON.parse(dataLine.substring(6));
          
          switch(eventType) {
            case 'handoff':
              events.handoffs.push(`${data.from} → ${data.to}`);
              break;
            case 'tool_call':
              events.toolCalls.push({
                agent: data.agent,
                tool: data.tool,
                args: data.args
              });
              break;
            case 'error':
              events.errors.push({
                message: data.message,
                details: data.details
              });
              break;
            case 'agent_message':
              events.agentMessages.push(data.agent || 'Unknown');
              break;
          }
        } catch (e) {
          // Ignore parse errors
        }
      }
    }
  }
  
  // Display results
  console.log('📊 Event Flow:');
  
  if (events.handoffs.length > 0) {
    console.log('\n🔄 Handoffs:');
    events.handoffs.forEach(h => console.log(`  - ${h}`));
  }
  
  if (events.toolCalls.length > 0) {
    console.log('\n🔧 Tool Calls:');
    events.toolCalls.forEach(t => {
      console.log(`  - Agent: ${t.agent}`);
      console.log(`    Tool: ${t.tool}`);
      console.log(`    Args: ${JSON.stringify(t.args, null, 4)}`);
    });
  }
  
  if (events.errors.length > 0) {
    console.log('\n❌ Errors:');
    events.errors.forEach(e => {
      console.log(`  - ${e.message}`);
      if (e.details) {
        console.log(`    Details: ${e.details}`);
      }
    });
  }
  
  if (events.agentMessages.length > 0) {
    console.log('\n💬 Agents Involved:');
    console.log(`  - ${[...new Set(events.agentMessages)].join(', ')}`);
  }
  
  return events;
}

// Run diagnostics
async function runDiagnostics() {
  console.log('=== Test 1: Simple Product Creation ===\n');
  await diagnoseToolCall("Create a product named 'Diagnostic Test Product' by vendor 'Test Co' of type 'Test Equipment'");
  
  console.log('\n\n=== Test 2: Product with Inventory ===\n');
  await diagnoseToolCall("Create product 'Inventory Test' vendor 'Test' type 'Equipment' with 50 units in stock");
  
  console.log('\n\n=== Test 3: Search Products ===\n');
  await diagnoseToolCall("Search for products with status:active");
  
  console.log('\n\n=== Test 4: Direct Tool Request ===\n');
  await diagnoseToolCall("Use the create_product tool to create a product with title 'Direct Tool Test', vendor 'Test', and product_type 'Test Type'");
}

console.log('🚀 Starting Tool Diagnostics\n');
console.log('Server should be running on http://localhost:5173\n');

await runDiagnostics();

console.log('\n✅ Diagnostics completed!');