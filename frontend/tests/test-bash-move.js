import { executeBashCommand } from '../server/tools/bash-tool.js';

async function testBashMove() {
  console.log('Testing bash move command...\n');
  
  // First, create a test file
  console.log('1. Creating test file...');
  const createResult = await executeBashCommand({
    command: 'echo "test content" > /tmp/test-move-file.txt',
    cwd: '/tmp'
  });
  console.log('Create result:', createResult);
  
  // Try to move the file
  console.log('\n2. Testing move command...');
  try {
    const moveResult = await executeBashCommand({
      command: 'mv /tmp/test-move-file.txt /tmp/test-moved-file.txt',
      cwd: '/tmp'
    });
    console.log('Move result:', moveResult);
  } catch (error) {
    console.error('Move error:', error);
    console.error('Error stack:', error.stack);
  }
  
  // Check if file was moved
  console.log('\n3. Checking if file was moved...');
  const checkResult = await executeBashCommand({
    command: 'ls -la /tmp/test-moved-file.txt',
    cwd: '/tmp'
  });
  console.log('Check result:', checkResult);
}

testBashMove().catch(console.error);