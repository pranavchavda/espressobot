#!/usr/bin/env node

import { callMCPTool } from './server/tools/mcp-client.js';

async function testNativeMCP() {
  console.log('Testing native MCP implementation...\n');
  
  try {
    // First, check if the native tool is loaded
    console.log('Testing native get_product_native tool...');
    const result = await callMCPTool('get_product_native', {
      identifier: 'mexican-altura'
    });
    
    console.log('Result:', JSON.stringify(result, null, 2));
    
  } catch (error) {
    console.error('Error:', error.message);
  }
}

testNativeMCP();