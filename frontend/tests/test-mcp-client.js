import { createParser } from 'eventsource-parser';
import fetch from 'node-fetch';

// SSE-based MCP server client implementation
class SseMCPServer {
  constructor(serverUrl, allowedTools) {
    this.name = 'shopify-mcp';
    this.url = serverUrl;
    this.allowedTools = allowedTools;
    this.cacheToolsList = false;
  }
  
  async connect() {
    console.log('Connecting to MCP server:', this.url);
  }
  
  async close() {
    console.log('Closing MCP server connection');
  }
  
  async listTools() {
    console.log('Listing tools from MCP server...');
    const id = Date.now();
    const req = { 
      jsonrpc: '2.0', 
      id, 
      method: 'tools/list', 
      params: { allowed_tools: this.allowedTools } 
    };
    
    console.log('Request:', JSON.stringify(req, null, 2));
    
    try {
      const res = await fetch(this.url, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'Accept': 'text/event-stream' 
        },
        body: JSON.stringify(req)
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! Status: ${res.status}`);
      }
      
      const parser = createParser({
        onEvent: (ev) => {
          try {
            console.log('Received event data:', ev.data);
            const msg = JSON.parse(ev.data);
            if (msg.id === id && msg.result?.content) {
              this._tools = msg.result.content.map(t => ({
                name: t.name,
                inputSchema: t.inputSchema
              }));
              console.log('Parsed tools:', this._tools);
            }
          } catch (err) {
            console.error('Error parsing event data:', err);
          }
        }
      });
      
      // Handle streaming response for node-fetch in ESM mode
      this._tools = [];
      
      // Process the response as a stream of text
      for await (const chunk of res.body) {
        const text = chunk.toString('utf8');
        console.log('Received chunk:', text);
        parser.feed(text);
        if (this._tools.length) break;
      }
      
      return this._tools;
    } catch (error) {
      console.error('Error listing tools:', error);
      return [];
    }
  }
  
  async callTool(toolName, args) {
    console.log(`Calling tool ${toolName} with args:`, args);
    const id = Date.now();
    const req = { 
      jsonrpc: '2.0', 
      id, 
      method: 'tools/call', 
      params: { 
        name: toolName, 
        arguments: args 
      } 
    };
    
    console.log('Request:', JSON.stringify(req, null, 2));
    
    try {
      const res = await fetch(this.url, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json', 
          'Accept': 'text/event-stream' 
        },
        body: JSON.stringify(req)
      });
      
      if (!res.ok) {
        throw new Error(`HTTP error! Status: ${res.status}`);
      }
      
      let result = null;
      const parser = createParser({
        onEvent: (ev) => {
          try {
            console.log('Received event data:', ev.data);
            const msg = JSON.parse(ev.data);
            if (msg.id === id && msg.result) {
              result = msg.result;
              console.log('Tool result:', result);
            }
          } catch (err) {
            console.error('Error parsing event data:', err);
          }
        }
      });
      
      // Process the response as a stream of text
      for await (const chunk of res.body) {
        const text = chunk.toString('utf8');
        console.log('Received chunk:', text);
        parser.feed(text);
        if (result) break;
      }
      
      return result;
    } catch (error) {
      console.error('Error calling tool:', error);
      return null;
    }
  }
}

// Test the SSE MCP client
async function testMcpClient() {
  // Get MCP server URL from environment or use default
  const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 'https://webhook-listener-pranavchavda.replit.app/mcp/sse';
  
  // Try a direct fetch to the MCP server to check if it's working
  console.log('Testing direct fetch to MCP server...');
  try {
    const directRes = await fetch(MCP_SERVER_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'tools/list',
        params: {}
      })
    });
    
    const contentType = directRes.headers.get('content-type');
    console.log('Direct fetch response content type:', contentType);
    
    if (contentType && contentType.includes('text/event-stream')) {
      console.log('Server supports SSE, processing events...');
      let data = '';
      for await (const chunk of directRes.body) {
        data += chunk.toString();
        console.log('Received data chunk:', chunk.toString());
      }
      console.log('Complete response:', data);
    } else {
      const text = await directRes.text();
      console.log('Direct fetch response (not SSE):', text.substring(0, 500) + '...');
    }
  } catch (err) {
    console.error('Direct fetch error:', err);
  }
  
  // Define allowed tools
  const ALLOWED_TOOLS = [
    'mcp6_search_products',
    'mcp6_get_single_product',
    'mcp6_get_collections',
    'mcp6_add_product_to_collection',
    'mcp6_set_metafield',
    'mcp6_add_tags_to_product',
    'mcp6_remove_tags_from_product',
    'mcp6_update_pricing'
  ];
  
  console.log('Creating MCP client with URL:', MCP_SERVER_URL);
  const mcpClient = new SseMCPServer(MCP_SERVER_URL, ALLOWED_TOOLS);
  
  try {
    // Connect to the MCP server
    await mcpClient.connect();
    
    // List available tools
    console.log('Listing available tools...');
    const tools = await mcpClient.listTools();
    console.log('Available tools:', tools);
    
    // Call a tool if tools were successfully listed
    if (tools && tools.length > 0) {
      console.log('Testing tool call with search_products...');
      const result = await mcpClient.callTool('mcp6_search_products', { query: 'coffee' });
      console.log('Tool call result:', result);
    }
    
    // Close the connection
    await mcpClient.close();
  } catch (error) {
    console.error('Test failed:', error);
  }
}

// Run the test
testMcpClient().catch(console.error);
