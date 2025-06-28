#!/usr/bin/env node

console.log('🧪 Quick Orchestrator Test\n');

async function test() {
  const fetch = (await import('node-fetch')).default;
  
  try {
    // Check health endpoint
    console.log('Checking /api/agent/health...');
    const healthRes = await fetch('http://localhost:5173/api/agent/health');
    
    if (!healthRes.ok) {
      console.log('❌ Server not running or not accessible');
      console.log('Please start the server with: npm run dev');
      return;
    }
    
    const health = await healthRes.json();
    console.log('✅ Server is running');
    console.log(`\nConfigured agents (${health.agents.length}):`);
    health.agents.forEach(agent => console.log(`  - ${agent}`));
    
    // Quick test
    console.log('\n\nSending test request...');
    const response = await fetch('http://localhost:5173/api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: 'Hello, which agents are available?' })
    });
    
    const text = await response.text();
    const lines = text.split('\n');
    
    let orchestrator = 'Unknown';
    for (const line of lines) {
      if (line.includes('Enhanced_EspressoBot_Orchestrator')) {
        orchestrator = 'Enhanced Multi-Agent Orchestrator ✅';
        break;
      } else if (line.includes('EspressoBot_Orchestrator')) {
        orchestrator = 'Old EspressoBot Orchestrator ❌';
        break;
      }
    }
    
    console.log(`\nOrchestrator in use: ${orchestrator}`);
    
    if (orchestrator.includes('Enhanced')) {
      console.log('\n✅ The enhanced multi-agent system is active!');
      console.log('You can now run: node test-tools-via-api.js');
    } else {
      console.log('\n⚠️  The old orchestrator is still being used.');
      console.log('Make sure USE_MULTI_AGENT=true is in your .env file');
      console.log('and restart the server.');
    }
    
  } catch (error) {
    console.error('Error:', error.message);
    console.log('\n❌ Could not connect to server');
    console.log('Please start the server with: npm run dev');
  }
}

test();