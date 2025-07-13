#!/usr/bin/env node

import { runDynamicOrchestrator } from './server/espressobot1.js';

async function testOrchestratorMCPDirect() {
  console.log('🔍 Testing Orchestrator MCP Tool Access\n');
  
  // Test a simple get_product request
  const testMessage = "Get product details for mexican-altura";
  const conversationId = `test-mcp-${Date.now()}`;
  
  console.log(`Testing: "${testMessage}"`);
  console.log(`Conversation ID: ${conversationId}\n`);
  
  let toolCalls = [];
  let messages = [];
  let errors = [];
  
  try {
    await runDynamicOrchestrator(
      testMessage,
      conversationId,
      "test-user",
      (event, data) => {
        switch (event) {
          case 'tool_call':
            toolCalls.push({
              tool: data.tool || data.name,
              args: data.args || data.arguments,
              timestamp: Date.now()
            });
            console.log(`🔧 Tool Call: ${data.tool || data.name}`);
            if (data.args || data.arguments) {
              console.log(`   Args:`, data.args || data.arguments);
            }
            break;
            
          case 'agent_message':
          case 'message':
            messages.push(data);
            console.log(`💬 Message: ${typeof data === 'string' ? data : data.content || JSON.stringify(data)}`);
            break;
            
          case 'error':
            errors.push(data);
            console.log(`❌ Error: ${data}`);
            break;
            
          case 'agent_processing':
            console.log(`⚡ Processing: ${data.message || data}`);
            break;
            
          default:
            console.log(`📋 ${event}:`, data);
            break;
        }
      }
    );
    
  } catch (error) {
    console.error('❌ Orchestrator failed:', error.message);
    errors.push(error.message);
  }
  
  console.log('\n📊 === Test Results ===');
  console.log(`Tool calls made: ${toolCalls.length}`);
  console.log(`Messages sent: ${messages.length}`);
  console.log(`Errors encountered: ${errors.length}`);
  
  if (toolCalls.length > 0) {
    console.log('\n🔧 Tool Calls Made:');
    toolCalls.forEach((call, i) => {
      console.log(`  ${i + 1}. ${call.tool}`);
      if (call.args) {
        console.log(`     Args: ${JSON.stringify(call.args)}`);
      }
    });
    
    // Check if it used MCP tools directly
    const mcpCalls = toolCalls.filter(call => 
      call.tool === 'get_product' ||
      call.tool === 'search_products' ||
      call.tool === 'manage_inventory_policy' ||
      call.tool.includes('mcp')
    );
    
    const bashCalls = toolCalls.filter(call => 
      call.tool === 'spawn_bash_agent' ||
      call.tool.includes('bash')
    );
    
    console.log(`\n✅ MCP tool calls: ${mcpCalls.length}`);
    console.log(`⚠️  Bash agent calls: ${bashCalls.length}`);
    
    if (mcpCalls.length > 0) {
      console.log('🎉 SUCCESS: Orchestrator used MCP tools directly!');
    } else if (bashCalls.length > 0) {
      console.log('❌ ISSUE: Orchestrator used bash agents instead of MCP tools');
    }
  } else {
    console.log('❌ No tool calls made - orchestrator may be stuck');
  }
  
  if (errors.length > 0) {
    console.log('\n❌ Errors:');
    errors.forEach(error => console.log(`  - ${error}`));
  }
}

testOrchestratorMCPDirect().catch(console.error);