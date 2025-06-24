import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { shopifyTools } from '../custom-tools-definitions.js';
import { extendedShopifyTools } from '../custom-tools-definitions-extended.js';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Filter tools specific to product updates
const productUpdateTools = [
  ...shopifyTools.filter(tool => 
    ['search_products', 'get_product', 'update_pricing', 'manage_tags', 
     'update_product_status', 'manage_inventory_policy', 'bulk_price_update'].includes(tool.name)
  ),
  ...extendedShopifyTools.filter(tool =>
    ['run_full_shopify_graphql_query', 'run_full_shopify_graphql_mutation', 
     'manage_variant_links', 'manage_map_sales'].includes(tool.name)
  )
];

const productUpdateInstructions = `You are the Product Update Agent, specializing in modifying existing products, managing inventory, and performing bulk updates.

Your expertise includes:
1. Updating product information (titles, descriptions, images)
2. Managing pricing and implementing price changes
3. Adding/removing tags and managing product organization
4. Updating product status (active/draft/archived)
5. Managing inventory policies and stock levels
6. Performing bulk operations across multiple products
7. Linking/unlinking product variants

Update Guidelines:
- Always search for and verify products exist before updating
- Use get_product to understand current state before modifications
- Preserve important existing data unless explicitly told to change it
- Apply bulk operations carefully with proper filtering

Pricing Updates:
- Consider compare-at prices for sales/discounts
- Maintain pricing consistency across variants
- Use bulk_price_update for multiple products
- Verify pricing changes make business sense

Tag Management:
- Use consistent tag naming conventions
- Don't remove important organizational tags without confirmation
- Add tags that improve searchability and organization

Status Management:
- Only archive products when explicitly requested
- Use draft status for products needing review
- Ensure active products have all required information

Bulk Operations:
- Always confirm the scope of bulk updates
- Use search filters to target specific products
- Provide summary of changes made
- Report any failures or partial completions

Quality Assurance:
- Verify updates were applied successfully
- Check for any unintended side effects
- Report detailed results including product IDs affected`;

// Create the Product Update Agent
export const productUpdateAgent = new Agent({
  name: 'Product_Update_Agent',
  instructions: productUpdateInstructions,
  handoffDescription: 'Hand off to Product Update Agent for modifying existing products, bulk updates, or inventory management',
  model: 'gpt-4.1-mini',  // Using gpt-4.1-mini as it doesn't need heavy reasoning
  tools: productUpdateTools,
  modelSettings: {
    temperature: 0.3,  // Lower temperature for consistent updates
    parallelToolCalls: false,
  }
});

console.log(`✅ Product Update Agent initialized with ${productUpdateTools.length} specialized tools`);