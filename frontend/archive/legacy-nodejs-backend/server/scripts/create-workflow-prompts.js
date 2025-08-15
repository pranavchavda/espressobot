#!/usr/bin/env node
import memoryOps from '../memory/memory-operations-local.js';

const workflowPrompts = [
  {
    name: "Product Creation Workflow",
    fragment: `When creating products in Shopify, follow this exact workflow:

1. VALIDATION PHASE:
   - Verify all required fields: title, vendor, product_type
   - Check metafield requirements for product type
   - Validate image URLs are accessible
   
2. METAFIELD SETUP:
   - ingredient_list (multi_line_text): Full ingredients list
   - is_subscription_only (boolean): Subscription product flag  
   - caffeine_mg_per_serving (number_integer): Caffeine content
   - roast_level (single_line_text): Light/Medium/Dark
   
3. VARIANT CREATION:
   - Standard sizes: 340g, 907g, 2.27kg
   - Set SKU format: {TYPE}-{ORIGIN}-{SIZE}
   - Price scaling: 907g = 2.5x of 340g
   
4. INVENTORY TRACKING:
   - Enable tracking for all variants
   - Set fulfillment service: manual
   - Initial quantity: 0 (update separately)
   
5. PUBLICATION:
   - Publish to Online Store channel
   - Set status: active (unless specified)`,
    category: 'workflows',
    priority: 'high',
    agentType: 'swe',
    tags: ['product-creation', 'shopify', 'workflow']
  },
  {
    name: "Coffee Product Guidelines",
    fragment: `For coffee products specifically:

NAMING CONVENTION:
- Format: "{Origin} {Process} - {Roast}"
- Example: "Colombia Washed - Medium Roast"

REQUIRED METAFIELDS:
- origin_country: Country of origin (e.g., "Colombia")
- tasting_notes: Flavor profile array (e.g., ["chocolate", "caramel", "citrus"])
- brewing_methods: Recommended methods (["espresso", "filter", "french-press"])
- altitude_masl: Growing altitude in meters
- process_method: Processing type (washed/natural/honey)

TAGS STRUCTURE:
- Origin: country-{name} (e.g., country-colombia)
- Roast: roast-{level} (e.g., roast-medium)
- Flavor: flavor-{note} (e.g., flavor-chocolate)
- Certification: cert-{type} (e.g., cert-organic)

DESCRIPTION TEMPLATE:
Include origin story, tasting notes, brewing recommendations, and altitude/process details.`,
    category: 'domain',
    priority: 'high', 
    agentType: 'all',
    tags: ['coffee', 'product-guidelines', 'metafields']
  },
  {
    name: "Bundle Product Creation",
    fragment: `When creating bundle products:

STRUCTURE:
- Parent product = Bundle container
- Components = Referenced via metafields
- Pricing = Sum of components - discount

METAFIELDS:
- bundle_components (list.product_reference): Component products
- bundle_discount_percentage (number_decimal): Bundle discount
- bundle_savings_amount (money): Calculated savings

INVENTORY:
- Track bundle inventory separately
- Monitor component availability
- Set max bundle quantity = MIN(component quantities)

AUTOMATION:
- Use Flow to sync component inventory
- Auto-update bundle availability
- Calculate savings on price changes`,
    category: 'workflows',
    priority: 'medium',
    agentType: 'swe',
    tags: ['bundles', 'complex-products', 'inventory']
  },
  {
    name: "SEO Optimization Checklist",
    fragment: `For SEO optimization on products:

META FIELDS:
- seo.title: 50-60 chars, include key terms
- seo.description: 150-160 chars, compelling CTA
- seo.keywords: Relevant search terms

URL HANDLE:
- Format: {product-type}-{key-attribute}
- Example: coffee-colombia-medium-roast
- Keep under 50 characters
- Use hyphens, no underscores

IMAGE ALT TEXT:
- Descriptive and keyword-rich
- Format: "{Product Name} - {View/Angle}"
- Include key attributes

STRUCTURED DATA:
- Add product schema markup
- Include reviews/ratings
- Set availability status`,
    category: 'patterns',
    priority: 'medium',
    agentType: 'all',
    tags: ['seo', 'optimization', 'checklist']
  }
];

async function createWorkflowPrompts() {
  console.log('📝 Creating workflow-specific prompts...\n');
  
  for (const prompt of workflowPrompts) {
    try {
      await memoryOps.addSystemPromptFragment(prompt);
      console.log(`✅ Added: ${prompt.name}`);
    } catch (error) {
      console.error(`❌ Failed to add "${prompt.name}":`, error.message);
    }
  }
  
  console.log('\n🎉 Workflow prompts created!');
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  createWorkflowPrompts();
}

export default createWorkflowPrompts;