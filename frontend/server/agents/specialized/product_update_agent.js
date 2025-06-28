
import { Agent } from '@openai/agents';

const productUpdateAgent = new Agent({
  name: 'Product_Update_Agent',
  description: 'Handles changes to existing products, including pricing, features, tags, variants, and status.',
  instructions: 'You are a specialized agent for updating existing product information. Use the available tools to manage pricing, features, tags, and other product attributes.',
  tools: [
    'update_pricing',
    'bulk_price_update',
    'manage_features_json',
    'manage_features_metaobjects',
    'manage_tags',
    'manage_variant_links',
    'update_status',
    'manage_redirects',
    'search_products' // For lookups before update
  ],
  model: 'gpt-4.1'
});

export default productUpdateAgent;
