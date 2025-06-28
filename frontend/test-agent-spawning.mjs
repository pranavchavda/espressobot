import { createBashAgent } from './server/tools/bash-tool.js';

console.log('Testing agent creation after fix...\n');

try {
  // Test creating a bash agent
  const testAgent = createBashAgent('TestAgent', 'List files in /tmp');
  console.log('✅ Agent created successfully!');
  console.log('Agent name:', testAgent.name);
  console.log('Agent has tools:', testAgent.tools.length);
} catch (error) {
  console.error('❌ Failed to create agent:', error.message);
  console.error('Stack:', error.stack);
}

console.log('\nDone!');