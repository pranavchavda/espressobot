#!/usr/bin/env node

import { bashTool } from './server/tools/bash-tool.js';

console.log('🔧 Testing Bash Tool Directly\n');

async function testCommand(command, cwd = '/tmp') {
  console.log(`\nCommand: ${command}`);
  console.log(`CWD: ${cwd}`);
  console.log('─'.repeat(50));
  
  try {
    // The tool object has an invoke method, not execute
    const result = await bashTool.invoke({ command, cwd });
    console.log('Result:', result);
  } catch (error) {
    console.error('Error:', error);
  }
}

// Run tests
console.log('Running direct bash tool tests...\n');

// Test 1: Simple echo
await testCommand('echo "Hello from bash!"');

// Test 2: List tmp directory
await testCommand('ls -la');

// Test 3: Check Python
await testCommand('python3 --version');

// Test 4: List tools directory
await testCommand('ls /home/pranav/idc/tools/ | head -5');

// Test 5: Run a Python tool with help
await testCommand('python3 /home/pranav/idc/tools/search_products.py --help 2>&1 | head -20');

console.log('\n✅ Tests completed!');