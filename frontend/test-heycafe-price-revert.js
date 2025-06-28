#!/usr/bin/env node

console.log('🔍 Testing HeyCafe Jack price revert\n');

const fetch = (await import('node-fetch')).default;

async function testPriceRevert() {
  const message = "please revert the sale on both heycafe jack variants";
  
  console.log(`Query: "${message}"\n`);
  
  try {
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    // Track the flow
    let agent = null;
    let toolsCalled = [];
    let finalResponse = null;
    
    for (let i = 0; i < lines.length; i++) {
      if (lines[i] === 'event: agent_message' && lines[i+1]?.startsWith('data: ')) {
        const data = JSON.parse(lines[i+1].substring(6));
        agent = data.agent;
      }
      
      if (lines[i] === 'event: tool_call' && lines[i+1]?.startsWith('data: ')) {
        const data = JSON.parse(lines[i+1].substring(6));
        toolsCalled.push({ tool: data.tool, args: data.args });
      }
      
      if (lines[i] === 'event: error' && lines[i+1]?.startsWith('data: ')) {
        const data = JSON.parse(lines[i+1].substring(6));
        console.log('❌ Error:', data.message);
      }
      
      if (lines[i] === 'event: done' && lines[i+1]?.startsWith('data: ')) {
        const data = JSON.parse(lines[i+1].substring(6));
        finalResponse = data.finalResponse;
      }
    }
    
    // Display results
    if (agent) {
      console.log('Agent:', agent);
    }
    
    if (toolsCalled.length > 0) {
      console.log('\nTools called:');
      toolsCalled.forEach(t => {
        console.log(`- ${t.tool}`);
        if (t.args) {
          console.log('  Args:', JSON.stringify(t.args, null, 2));
        }
      });
    }
    
    if (finalResponse) {
      console.log('\nResponse:', finalResponse);
    }
    
  } catch (error) {
    console.error('Request failed:', error.message);
  }
}

await testPriceRevert();
console.log('\n✅ Test completed!');