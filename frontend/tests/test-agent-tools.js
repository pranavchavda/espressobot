#!/usr/bin/env node

console.log('🔍 Testing Agent Tool Configuration\n');

import { Agent } from '@openai/agents';
import enhancedOrchestrator from './server/enhanced-multi-agent-orchestrator-v2.js';
import productCreationAgent from './server/agents/specialized/product_creation_agent.js';
import { openAITools } from './server/tools/openai-tool-converter.js';

// Check what tools are available
console.log('=== Available OpenAI Tools ===');
console.log('Total tools converted:', Object.keys(openAITools).length);
console.log('Tool names:', Object.keys(openAITools).join(', '));

// Check orchestrator configuration
console.log('\n=== Orchestrator Configuration ===');
console.log('Name:', enhancedOrchestrator.name);
console.log('Model:', enhancedOrchestrator.model);
console.log('Handoffs:', enhancedOrchestrator.handoffs?.map(h => h.name || 'Unknown').join(', '));
console.log('Tools:', enhancedOrchestrator.tools?.length || 0);

// Check Product Creation Agent
console.log('\n=== Product Creation Agent ===');
console.log('Name:', productCreationAgent.name);
console.log('Model:', productCreationAgent.model);
console.log('Number of tools:', productCreationAgent.tools?.length || 0);

// List each tool
if (productCreationAgent.tools && productCreationAgent.tools.length > 0) {
  console.log('\nTools assigned:');
  productCreationAgent.tools.forEach((tool, index) => {
    if (typeof tool === 'function') {
      console.log(`  ${index + 1}. [Function Tool]`);
    } else if (tool && tool.name) {
      console.log(`  ${index + 1}. ${tool.name} - ${tool.description?.substring(0, 50)}...`);
    } else if (typeof tool === 'string') {
      console.log(`  ${index + 1}. [String] ${tool} (NOT CONVERTED!)`);
    } else {
      console.log(`  ${index + 1}. [Unknown type]`, tool);
    }
  });
}

// Test if create_product tool exists
console.log('\n=== Testing create_product Tool ===');
const createProductTool = openAITools['create_product'];
if (createProductTool) {
  console.log('✅ create_product tool found');
  console.log('Description:', createProductTool.description);
  
  // Test execution with minimal params
  try {
    const result = await createProductTool.execute({
      title: 'Tool Test Product',
      vendor: 'Test Vendor',
      product_type: 'Test Type'
    });
    console.log('Execution result:', result);
  } catch (error) {
    console.log('Execution error:', error.message);
  }
} else {
  console.log('❌ create_product tool NOT found');
}

console.log('\n✅ Configuration test completed!');