console.log('Testing imports...\n');

try {
  console.log('1. Importing SWE agent...');
  const { sweAgent } = await import('./server/agents/swe-agent.js');
  console.log('   ✓ SWE agent imported successfully');
  console.log('   Type:', typeof sweAgent);
  console.log('   Is Agent instance?', sweAgent?.constructor?.name);
  console.log('   Has asTool method?', typeof sweAgent?.asTool);
  
} catch (error) {
  console.error('   ✗ Error importing SWE agent:', error.message);
  console.error('   Stack:', error.stack);
}

try {
  console.log('\n2. Importing dynamic orchestrator...');
  const { dynamicOrchestrator } = await import('./server/dynamic-bash-orchestrator.js');
  console.log('   ✓ Dynamic orchestrator imported successfully');
  console.log('   Type:', typeof dynamicOrchestrator);
  
} catch (error) {
  console.error('   ✗ Error importing dynamic orchestrator:', error.message);
}