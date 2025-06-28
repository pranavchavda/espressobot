import { customToolDiscovery } from './custom-tool-discovery.js';
import fs from 'fs/promises';
import path from 'path';

console.log('🧪 Testing Updated Agent Definitions\n');
console.log('====================================\n');

// Initialize tools
await customToolDiscovery.discoverTools();
const allTools = customToolDiscovery.allTools;
const availableToolNames = allTools.map(t => t.name);

console.log(`📦 Found ${allTools.length} tools in registry\n`);

// Read agent files directly
const agentsDir = './server/agents/specialized';
const agentFiles = await fs.readdir(agentsDir);

console.log('🔍 Checking Agent Tool Definitions:\n');

let allToolsValid = true;
const agentToolMapping = {};

for (const file of agentFiles) {
  if (file.endsWith('.js')) {
    const content = await fs.readFile(path.join(agentsDir, file), 'utf-8');
    
    // Extract tools array
    const toolsMatch = content.match(/tools:\s*\[([\s\S]*?)\]/);
    if (toolsMatch) {
      const toolsString = toolsMatch[1];
      const tools = toolsString
        .split(',')
        .map(t => {
          // Remove comments
          const commentIndex = t.indexOf('//');
          if (commentIndex > -1) {
            t = t.substring(0, commentIndex);
          }
          return t.trim().replace(/['"]/g, '');
        })
        .filter(t => t.length > 0);
      
      const agentName = file.replace('.js', '');
      agentToolMapping[agentName] = tools;
      
      console.log(`\n${agentName}:`);
      tools.forEach(tool => {
        const found = availableToolNames.includes(tool);
        if (found) {
          console.log(`   ✅ ${tool}`);
        } else {
          console.log(`   ❌ ${tool} - NOT FOUND`);
          allToolsValid = false;
        }
      });
      
      if (tools.length === 0) {
        console.log('   (no tools)');
      }
    }
  }
}

// Summary
console.log('\n\n📊 Summary:\n');
console.log(`Total agents checked: ${Object.keys(agentToolMapping).length}`);
console.log(`All tools valid: ${allToolsValid ? '✅ YES' : '❌ NO'}`);

if (allToolsValid) {
  console.log('\n✅ All agent tool definitions are correctly mapped to the registry!');
} else {
  console.log('\n❌ Some tools are still missing from the registry.');
}

// Show tool counts per agent
console.log('\n📈 Tool count per agent:');
Object.entries(agentToolMapping).forEach(([agent, tools]) => {
  console.log(`   ${agent}: ${tools.length} tools`);
});

process.exit(allToolsValid ? 0 : 1);