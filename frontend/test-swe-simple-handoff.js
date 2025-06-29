import { runDynamicOrchestrator } from './server/dynamic-bash-orchestrator.js';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

async function testSWESimple() {
  console.log('Testing SWE Agent via orchestrator handoff (simple task)...\n');
  
  try {
    // Test: Ask orchestrator to use SWE Agent for a simple tool creation
    const prompt = `Please use the SWE Agent to create a simple ad-hoc tool called 'count_files' that counts the number of files in a directory passed as an argument. Save it in the tmp/ directory.`;
    
    console.log('Prompt:', prompt);
    console.log('\n--- Running Orchestrator ---\n');
    
    const result = await runDynamicOrchestrator(prompt);
    
    console.log('\n--- Result ---');
    console.log('Final output:', result.finalOutput || result);
    
    // Check if the tool was created
    console.log('\n--- Checking if tool exists ---');
    const { exec } = await import('child_process');
    const { promisify } = await import('util');
    const execAsync = promisify(exec);
    
    try {
      const { stdout } = await execAsync('ls -la tmp/count_files.py');
      console.log('Tool created:', stdout);
    } catch (e) {
      console.log('Tool not found in tmp/');
    }
    
  } catch (error) {
    console.error('Error:', error);
    console.error('Stack:', error.stack);
  }
}

// Run the test
testSWESimple();