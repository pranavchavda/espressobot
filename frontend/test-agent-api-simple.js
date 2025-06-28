import EventSource from 'eventsource';

console.log('🧪 Simple EspressoBot API Test\n');

const API_BASE = 'http://localhost:5173';
const AGENT_ENDPOINT = `${API_BASE}/api/agent/run`;

// Test function
async function testAgent(message) {
  return new Promise((resolve, reject) => {
    console.log(`📨 Sending: "${message}"\n`);
    
    const results = {
      agents: new Set(),
      tools: new Set(),
      response: '',
      errors: []
    };

    // Create EventSource with POST
    const es = new EventSource(AGENT_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message })
    });

    es.addEventListener('conversation_id', (event) => {
      const data = JSON.parse(event.data);
      console.log(`📝 Conversation ID: ${data.conv_id}`);
    });

    es.addEventListener('agent_processing', (event) => {
      const data = JSON.parse(event.data);
      if (data.agent) {
        results.agents.add(data.agent);
        console.log(`🤖 Agent: ${data.agent} - ${data.message}`);
      }
    });

    es.addEventListener('handoff', (event) => {
      const data = JSON.parse(event.data);
      console.log(`➡️  Handoff: ${data.from} → ${data.to}`);
      if (data.to) results.agents.add(data.to);
    });

    es.addEventListener('tool_call', (event) => {
      const data = JSON.parse(event.data);
      if (data.tool) {
        results.tools.add(data.tool);
        console.log(`🔧 Tool: ${data.agent} uses ${data.tool}`);
      }
    });

    es.addEventListener('done', (event) => {
      const data = JSON.parse(event.data);
      results.response = data.finalResponse || 'No response';
      es.close();
      resolve(results);
    });

    es.addEventListener('error', (event) => {
      if (event.data) {
        const data = JSON.parse(event.data);
        console.error(`❌ Error: ${data.message}`);
        results.errors.push(data.message);
      }
    });

    es.onerror = (error) => {
      console.error('EventSource error:', error);
      es.close();
      reject(error);
    };

    // Timeout after 30 seconds
    setTimeout(() => {
      es.close();
      resolve(results);
    }, 30000);
  });
}

// Run test
async function runTest() {
  try {
    const result = await testAgent("Search for coffee products under $300");
    
    console.log('\n📊 Results:');
    console.log(`   Agents used: ${Array.from(result.agents).join(', ')}`);
    console.log(`   Tools used: ${Array.from(result.tools).join(', ')}`);
    console.log(`   Errors: ${result.errors.length}`);
    console.log(`\n📝 Response: ${result.response.substring(0, 300)}...`);
    
  } catch (error) {
    console.error('Test failed:', error);
  }
}

runTest();