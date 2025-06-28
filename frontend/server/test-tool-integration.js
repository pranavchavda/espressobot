import { customToolDiscovery } from './custom-tool-discovery.js';
import { spawn } from 'child_process';
import { promisify } from 'util';
import fs from 'fs/promises';
import path from 'path';

console.log('🧪 Tool Integration Testing Framework\n');
console.log('=====================================\n');

// Initialize tools
await customToolDiscovery.discoverTools();
const allTools = customToolDiscovery.allTools;

console.log(`📦 Found ${allTools.length} tools in registry\n`);

// List all available tools
console.log('📋 Available Tools:');
allTools.forEach(tool => {
  console.log(`   - ${tool.name}`);
});

// Tools expected by agents (from the specialized agent files)
const expectedTools = {
  'Catalog_Query_Agent': ['search_products.py', 'get_product.py'],
  'Channel_Specials_Agent': ['manage_map_sales.py', 'manage_miele_sales.py'],
  'Inventory_Agent': [
    'manage_inventory_policy.py', 'manage_skuvault_kits.py',
    'upload_to_skuvault.py', 'update_skuvault.py',
    'update_skuvault_prices.py', 'update_skuvault_prices_v2.py'
  ],
  'Product_Creation_Agent': [
    'create_product.py', 'create_full_product.py', 'create_combo.py',
    'create_open_box.py', 'add_product_images.py'
  ],
  'Product_Update_Agent': [
    'update_pricing.py', 'bulk_price_update.py', 'manage_features_json.py',
    'manage_features_metaobjects.py', 'manage_tags.py', 'manage_variant_links.py',
    'update_status.py', 'manage_redirects.py', 'search_products.py'
  ],
  'Secure_Data_Agent': ['graphql_query.py', 'graphql_mutation.py'],
  'System_Health_Agent': ['test_connection.py']
};

// Check tool availability
console.log('\n🔍 Checking Tool Availability:\n');

const missingTools = [];
const availableToolNames = allTools.map(t => t.name);

Object.entries(expectedTools).forEach(([agent, tools]) => {
  console.log(`\n${agent}:`);
  tools.forEach(toolName => {
    // Try different variations of the tool name
    const baseName = toolName.replace('.py', '');
    const underscoreName = baseName;
    const noUnderscoreName = baseName.replace(/_/g, '');
    
    const found = availableToolNames.includes(baseName) || 
                  availableToolNames.includes(noUnderscoreName) ||
                  availableToolNames.includes(underscoreName);
    
    if (found) {
      const actualName = availableToolNames.find(n => 
        n === baseName || n === noUnderscoreName || n === underscoreName
      );
      console.log(`   ✅ ${toolName} -> ${actualName}`);
    } else {
      console.log(`   ❌ ${toolName} - NOT FOUND`);
      missingTools.push({ agent, tool: toolName });
    }
  });
});

// Check Python tool files
console.log('\n\n📁 Checking Python Tool Files:\n');

const pythonToolsDir = '/home/pranav/idc/tools';
try {
  const files = await fs.readdir(pythonToolsDir);
  const pythonFiles = files.filter(f => f.endsWith('.py'));
  
  console.log(`Found ${pythonFiles.length} Python files in ${pythonToolsDir}:`);
  pythonFiles.forEach(file => {
    const toolName = file.replace('.py', '');
    const inRegistry = availableToolNames.includes(toolName) || 
                       availableToolNames.includes(toolName.replace(/_/g, ''));
    console.log(`   ${inRegistry ? '✅' : '❌'} ${file}`);
  });
} catch (error) {
  console.error(`Error reading Python tools directory: ${error.message}`);
}

// Test a sample tool execution
console.log('\n\n🧪 Testing Tool Execution:\n');

// Test search_products tool
const testTool = allTools.find(t => t.name === 'search_products');
if (testTool) {
  console.log('Testing search_products tool...');
  try {
    const result = await customToolDiscovery.executeTool('search_products', {
      query: 'status:active',
      first: 5
    });
    
    if (result.error) {
      console.log(`   ❌ Error: ${result.error}`);
    } else if (result.products && Array.isArray(result.products)) {
      console.log(`   ✅ Success! Found ${result.products.length} products`);
      if (result.products.length > 0) {
        console.log(`   Sample: ${result.products[0].title} (${result.products[0].sku})`);
      }
    } else {
      console.log(`   ⚠️  Unexpected result format:`, JSON.stringify(result).substring(0, 100));
    }
  } catch (error) {
    console.log(`   ❌ Execution error: ${error.message}`);
  }
} else {
  console.log('   ❌ search_products tool not found in registry');
}

// Summary
console.log('\n\n📊 Summary:\n');
console.log(`Total tools in registry: ${allTools.length}`);
console.log(`Missing tools: ${missingTools.length}`);
if (missingTools.length > 0) {
  console.log('\nMissing tools by agent:');
  const byAgent = {};
  missingTools.forEach(({ agent, tool }) => {
    if (!byAgent[agent]) byAgent[agent] = [];
    byAgent[agent].push(tool);
  });
  Object.entries(byAgent).forEach(([agent, tools]) => {
    console.log(`   ${agent}: ${tools.length} missing`);
    tools.forEach(tool => console.log(`      - ${tool}`));
  });
}

// Recommendations
console.log('\n\n💡 Recommendations:\n');
console.log('1. Add missing tools to the registry in tool-registry-extended.js');
console.log('2. Update agent definitions to use correct tool names (without .py extension)');
console.log('3. Ensure Python scripts exist in /home/pranav/idc/tools/');
console.log('4. Test each tool individually before agent integration');

process.exit(0);