
import { Agent } from '@openai/agents';

const secureDataAgent = new Agent({
  name: 'Secure_Data_Agent',
  description: 'Handles secure order and customer information access (when approved). Highly restricted.',
  instructions: 'You are a specialized agent for accessing sensitive order and customer data. All your actions are audited. Use the GraphQL tools to perform queries and mutations.',
  tools: [
    'graphql_query',
    'graphql_mutation'
  ],
  model: 'o4-mini'
});

export default secureDataAgent;
