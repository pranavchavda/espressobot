/**
 * Test script to verify Google Workspace MCP server availability
 */

import MCPServerManager from './server/tools/mcp-server-manager.js';

async function testGoogleWorkspace() {
  console.log('Testing Google Workspace MCP integration...\n');
  
  try {
    // Initialize server manager
    const serverManager = new MCPServerManager();
    await serverManager.initializeServers();
    
    // Check if Google Workspace server is available
    const googleServer = serverManager.getServer('google-workspace');
    
    if (!googleServer) {
      console.log('❌ Google Workspace MCP server not found');
      console.log('   Make sure workspace-mcp is installed:');
      console.log('   Run: uvx workspace-mcp --help');
      console.log('\n   Or install it globally:');
      console.log('   pip install workspace-mcp');
      return;
    }
    
    console.log('✅ Google Workspace MCP server found');
    
    // List available tools
    try {
      const tools = await googleServer.listTools();
      console.log(`\n📋 Available tools (${tools.length}):`);
      tools.forEach(tool => {
        console.log(`   - ${tool.name}: ${tool.description || 'No description'}`);
      });
    } catch (error) {
      console.log('\n⚠️  Could not list tools:', error.message);
      console.log('   The server may require authentication first');
    }
    
  } catch (error) {
    console.error('❌ Error:', error.message);
  }
  
  process.exit(0);
}

testGoogleWorkspace();