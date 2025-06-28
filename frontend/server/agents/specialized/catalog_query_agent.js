
import { Agent } from '@openai/agents';

const catalogQueryAgent = new Agent({
  name: 'Catalog_Query_Agent',
  description: 'Handles product searches and lookups.',
  instructions: 'You are a specialized agent for querying the product catalog. Use the available tools to search for and retrieve product information.',
  tools: [
    'search_products',
    'get_product'
  ],
  model: 'gpt-4.1'
});

export default catalogQueryAgent;
