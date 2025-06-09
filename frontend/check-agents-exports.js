// Utility script to check available exports in @openai/agents packages
import * as agents from '@openai/agents';
import * as agentsCore from '@openai/agents-core';
import * as agentsOpenai from '@openai/agents-openai';

console.log('=== @openai/agents exports ===');
console.log(Object.keys(agents));

console.log('\n=== @openai/agents-core exports ===');
console.log(Object.keys(agentsCore));

console.log('\n=== @openai/agents-openai exports ===');
console.log(Object.keys(agentsOpenai));

// Check if there's a capability class in agents-openai
console.log('\nDoes OpenAICapability exist?', 'OpenAICapability' in agentsOpenai);
console.log('Available exports in agents-openai:', Object.keys(agentsOpenai));
