import { Agent, Runner } from '@openai/agents';

// Print out the available methods on the Runner class
console.log('Runner methods:', Object.getOwnPropertyNames(Runner.prototype));
console.log('Runner static methods:', Object.getOwnPropertyNames(Runner));

// Create a simple agent to test
const testAgent = new Agent({
  name: 'TestAgent',
  model: 'gpt-4o-mini',
  instructions: 'You are a test agent. Respond with a simple greeting.'
});

// Try to figure out how to run the agent
async function testRunnerAPI() {
  console.log('Testing Runner API...');
  
  try {
    // Try creating a runner instance
    console.log('Creating runner instance...');
    const runner = new Runner(testAgent);
    console.log('Runner instance methods:', Object.getOwnPropertyNames(Object.getPrototypeOf(runner)));
    
    // Try running the agent
    console.log('Running agent...');
    const result = await runner.run('Hello');
    console.log('Result:', result);
    
    return 'Success!';
  } catch (error) {
    console.error('Error testing Runner API:', error);
    return 'Failed!';
  }
}

// Run the test
testRunnerAPI()
  .then(result => console.log('Test result:', result))
  .catch(error => console.error('Test error:', error));
