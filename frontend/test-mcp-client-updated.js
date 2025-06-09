import { createParser } from 'eventsource-parser';
import fetch from 'node-fetch';

// MCP server URL without the /sse suffix
const MCP_SERVER_URL = 'https://webhook-listener-pranavchavda.replit.app/mcp';

// List of allowed Shopify tools
const ALLOWED_TOOLS = [
  'search_products',
  'get_collections',
  'get_single_product',
  'add_tags_to_product',
  'remove_tags_from_product'
];

async function testListTools() {
  console.log('Testing tools/list endpoint...');
  const id = Date.now();
  const req = { 
    jsonrpc: '2.0', 
    id, 
    method: 'tools/list', 
    params: { 
      allowed_tools: ALLOWED_TOOLS 
    } 
  };
  
  try {
    console.log(`Sending request to ${MCP_SERVER_URL}`);
    const res = await fetch(MCP_SERVER_URL, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'Accept': 'text/event-stream' 
      },
      body: JSON.stringify(req)
    });
    
    console.log(`Response status: ${res.status}`);
    
    if (!res.ok) {
      console.error(`HTTP error: ${res.status}`);
      const text = await res.text();
      console.log('Response body:', text);
      return;
    }
    
    // Check content type to see if we're getting SSE
    const contentType = res.headers.get('content-type');
    console.log(`Content-Type: ${contentType}`);
    
    if (contentType && contentType.includes('text/event-stream')) {
      console.log('Received SSE stream, parsing events...');
      
      let toolsReceived = false;
      
      const parser = createParser({
        onEvent: (event) => {
          try {
            console.log('Received SSE event:', event.data);
            const msg = JSON.parse(event.data);
            if (msg.id === id && msg.result?.content) {
              console.log('Tools received:', JSON.stringify(msg.result.content, null, 2));
              toolsReceived = true;
            }
          } catch (err) {
            console.error('Error parsing SSE event:', err);
          }
        }
      });
      
      // Process the response as a stream
      for await (const chunk of res.body) {
        const text = chunk.toString('utf8');
        console.log('Chunk received:', text);
        parser.feed(text);
        if (toolsReceived) break;
      }
      
      if (!toolsReceived) {
        console.warn('No tools received from SSE stream');
      }
    } else {
      // Not SSE, try to parse as JSON
      console.log('Not an SSE stream, trying to parse as JSON...');
      const text = await res.text();
      console.log('Response body:', text);
      
      try {
        const json = JSON.parse(text);
        console.log('Parsed JSON response:', JSON.stringify(json, null, 2));
      } catch (err) {
        console.error('Failed to parse response as JSON:', err);
      }
    }
  } catch (error) {
    console.error('Error testing tools/list:', error);
  }
}

async function testToolCall() {
  console.log('\nTesting tools/call endpoint...');
  const id = Date.now();
  const req = { 
    jsonrpc: '2.0', 
    id, 
    method: 'tools/call', 
    params: { 
      name: 'search_products', 
      arguments: { 
        query: 'coffee', 
        first: 3 
      } 
    } 
  };
  
  try {
    console.log(`Sending request to ${MCP_SERVER_URL}`);
    const res = await fetch(MCP_SERVER_URL, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json', 
        'Accept': 'text/event-stream' 
      },
      body: JSON.stringify(req)
    });
    
    console.log(`Response status: ${res.status}`);
    
    if (!res.ok) {
      console.error(`HTTP error: ${res.status}`);
      const text = await res.text();
      console.log('Response body:', text);
      return;
    }
    
    // Check content type to see if we're getting SSE
    const contentType = res.headers.get('content-type');
    console.log(`Content-Type: ${contentType}`);
    
    if (contentType && contentType.includes('text/event-stream')) {
      console.log('Received SSE stream, parsing events...');
      
      let resultReceived = false;
      
      const parser = createParser({
        onEvent: (event) => {
          try {
            console.log('Received SSE event:', event.data);
            const msg = JSON.parse(event.data);
            if (msg.id === id && msg.result) {
              console.log('Tool result received:', JSON.stringify(msg.result, null, 2));
              resultReceived = true;
            }
          } catch (err) {
            console.error('Error parsing SSE event:', err);
          }
        }
      });
      
      // Process the response as a stream
      for await (const chunk of res.body) {
        const text = chunk.toString('utf8');
        console.log('Chunk received:', text);
        parser.feed(text);
        if (resultReceived) break;
      }
      
      if (!resultReceived) {
        console.warn('No result received from SSE stream');
      }
    } else {
      // Not SSE, try to parse as JSON
      console.log('Not an SSE stream, trying to parse as JSON...');
      const text = await res.text();
      console.log('Response body:', text);
      
      try {
        const json = JSON.parse(text);
        console.log('Parsed JSON response:', JSON.stringify(json, null, 2));
      } catch (err) {
        console.error('Failed to parse response as JSON:', err);
      }
    }
  } catch (error) {
    console.error('Error testing tools/call:', error);
  }
}

// Run the tests
async function runTests() {
  await testListTools();
  await testToolCall();
}

runTests().catch(console.error);
