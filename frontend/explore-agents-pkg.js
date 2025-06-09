// Explore the structure of @openai/agents packages
import * as agents from '@openai/agents';
import * as agentsCore from '@openai/agents-core';

console.log('Available exports from @openai/agents:');
console.log(Object.keys(agents));

console.log('\nAvailable exports from @openai/agents-core:');
console.log(Object.keys(agentsCore));

// Try to find MCP-related functionality
if (agentsCore.mcp) {
  console.log('\nFound agentsCore.mcp:');
  console.log(Object.keys(agentsCore.mcp));
}

// Look for anything related to MCP in any nested object
function findMCP(obj, path = '') {
  for (const [key, value] of Object.entries(obj)) {
    if (typeof value === 'object' && value !== null) {
      if (key.toLowerCase().includes('mcp')) {
        console.log(`Found MCP at ${path}.${key}`);
      }
      findMCP(value, `${path}.${key}`);
    }
  }
}

console.log('\nSearching for MCP-related objects in agents:');
findMCP(agents, 'agents');

console.log('\nSearching for MCP-related objects in agentsCore:');
findMCP(agentsCore, 'agentsCore');
