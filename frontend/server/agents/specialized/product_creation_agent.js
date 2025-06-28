
import { Agent } from '@openai/agents';

const productCreationAgent = new Agent({
  name: 'Product_Creation_Agent',
  description: 'Handles new product listings, including standard products, combos, and open box units. Also manages product images.',
  instructions: 'You are a specialized agent for creating new products in the e-commerce system. Use the available tools to create products, combos, open box units, and add images.',
  tools: [
    'create_product',
    'product_create_full',
    'create_combo',
    'create_open_box',
    'add_product_images'
  ],
  model: 'gpt-4.1-mini'
});

export default productCreationAgent;
