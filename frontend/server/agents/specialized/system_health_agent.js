
import { Agent } from '@openai/agents';

const systemHealthAgent = new Agent({
  name: 'System_Health_Agent',
  description: 'Handles connection checks, test runs, and diagnostics.',
  instructions: 'You are a specialized agent for checking the health and connectivity of the system. Use the available tools to run diagnostic tests.',
  tools: [
    'test_connection'
  ],
  model: 'gpt-4.1-nano'
});

export default systemHealthAgent;
