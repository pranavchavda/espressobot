import fetch from 'node-fetch';

const OPENAI_API_KEY = process.env.OPENAI_API_KEY || '[REMOVED]';
const TRACE_ID = 'trace_c52d07d853814e20bcf34d64b7838f14';

async function fetchTrace() {
  try {
    // Try the traces endpoint
    const response = await fetch(`https://api.openai.com/v1/traces/${TRACE_ID}`, {
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      console.log('Status:', response.status);
      console.log('Status Text:', response.statusText);
      const text = await response.text();
      console.log('Response:', text);
      
      // Try alternative endpoints
      console.log('\n--- Trying alternative endpoint ---');
      const altResponse = await fetch(`https://api.openai.com/v1/agents/traces/${TRACE_ID}`, {
        headers: {
          'Authorization': `Bearer ${OPENAI_API_KEY}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (altResponse.ok) {
        const data = await altResponse.json();
        console.log('Trace data:', JSON.stringify(data, null, 2));
      } else {
        console.log('Alt Status:', altResponse.status);
        console.log('Alt Response:', await altResponse.text());
      }
    } else {
      const data = await response.json();
      console.log('Trace data:', JSON.stringify(data, null, 2));
    }
  } catch (error) {
    console.error('Error fetching trace:', error);
  }
}

// Also try to list recent traces
async function listTraces() {
  try {
    const response = await fetch('https://api.openai.com/v1/traces', {
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      const data = await response.json();
      console.log('\n--- Recent traces ---');
      console.log(JSON.stringify(data, null, 2));
    }
  } catch (error) {
    console.error('Error listing traces:', error);
  }
}

console.log(`Fetching trace: ${TRACE_ID}`);
fetchTrace();
listTraces();