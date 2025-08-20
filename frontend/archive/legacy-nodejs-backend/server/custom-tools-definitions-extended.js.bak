import { tool } from '@openai/agents';
import { z } from 'zod';
import { customToolDiscovery } from './custom-tool-discovery.js';

// Initialize custom tool discovery
await customToolDiscovery.discoverTools();

// Additional Shopify management tools

export const manageInventoryPolicyTool = tool({
  name: 'manage_inventory_policy',
  description: 'Update inventory policy for products (DENY when out of stock, CONTINUE to allow overselling)',
  parameters: z.object({
    product_id: z.string().describe('Product ID to update'),
    policy: z.enum(['DENY', 'CONTINUE']).describe('Inventory policy to set'),
    apply_to_all_variants: z.boolean().default(true).describe('Apply to all variants of the product')
  }),
  execute: async (args) => {
    args = args || {};
    if (args.sku && typeof args.sku === "string") { args.sku = args.sku.trim(); }
    if (args.sku && !Array.isArray(args.sku)) { args.sku = [args.sku]; }
    try {
      const result = await customToolDiscovery.executeTool('manage_inventory_policy', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const manageMAPSalesTool = tool({
  name: 'manage_map_sales',
  description: 'Manage MAP (Minimum Advertised Price) sales for products',
  parameters: z.object({
    product_id: z.string().describe('Product ID'),
    enable_map: z.boolean().describe('Enable or disable MAP pricing'),
    map_price: z.string().default('').describe('MAP price in decimal format'),
    sale_price: z.string().default('').describe('Sale price in decimal format')
  }),
  execute: async (args) => {
    args = args || {};
    if (args.sku && typeof args.sku === "string") { args.sku = args.sku.trim(); }
    if (args.sku && !Array.isArray(args.sku)) { args.sku = [args.sku]; }
    try {
      const result = await customToolDiscovery.executeTool('manage_map_sales', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const manageTagsTool = tool({
  name: 'manage_tags',
  description: 'Add or remove multiple tags from a product in one operation',
  parameters: z.object({
    product_id: z.string().describe('Product ID'),
    add_tags: z.array(z.string()).default([]).describe('Tags to add'),
    remove_tags: z.array(z.string()).default([]).describe('Tags to remove')
  }),
  execute: async (args) => {
    args = args || {};
    if (args.sku && typeof args.sku === "string") { args.sku = args.sku.trim(); }
    if (args.sku && !Array.isArray(args.sku)) { args.sku = [args.sku]; }
    try {
      const result = await customToolDiscovery.executeTool('manage_tags', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const manageVariantLinksTool = tool({
  name: 'manage_variant_links',
  description: 'Manage variant links between products (e.g., link color/size variants)',
  parameters: z.object({
    product_id: z.string().describe('Primary product ID'),
    linked_product_ids: z.array(z.string()).default([]).describe('Product IDs to link as variants'),
    link_type: z.string().default('variant').describe('Type of link relationship'),
    unlink: z.boolean().default(false).describe('Unlink instead of link')
  }),
  execute: async (args) => {
    args = args || {};
    if (args.sku && typeof args.sku === "string") { args.sku = args.sku.trim(); }
    if (args.sku && !Array.isArray(args.sku)) { args.sku = [args.sku]; }
    try {
      const result = await customToolDiscovery.executeTool('manage_variant_links', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const perplexityTool = tool({
  name: 'pplx',
  description: 'Query Perplexity AI for research, product information, or general questions',
  parameters: z.object({
    query: z.string().describe('Question or search query for Perplexity'),
    focus: z.enum(['web', 'academic', 'writing', 'wolfram', 'youtube', 'reddit']).default('web').describe('Search focus area'),
    include_sources: z.boolean().default(true).describe('Include source citations')
  }),
  execute: async (args) => {
    args = args || {};
    if (args.sku && typeof args.sku === "string") { args.sku = args.sku.trim(); }
    if (args.sku && !Array.isArray(args.sku)) { args.sku = [args.sku]; }
    try {
      const result = await customToolDiscovery.executeTool('pplx', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const uploadToSkuVaultTool = tool({
  name: 'upload_to_skuvault',
  description: 'Upload product data to SkuVault inventory management system',
  parameters: z.object({
    product_id: z.string().default('').describe('Specific product ID to upload'),
    sku: z.string().default('').describe('Specific SKU to upload'),
    all_products: z.boolean().default(false).describe('Upload all products'),
    sync_inventory: z.boolean().default(true).describe('Sync inventory quantities')
  }),
  execute: async (args) => {
    args = args || {};
    if (args.sku && typeof args.sku === "string") { args.sku = args.sku.trim(); }
    if (args.sku && !Array.isArray(args.sku)) { args.sku = [args.sku]; }
    try {
      const result = await customToolDiscovery.executeTool('upload_to_skuvault', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const bulkPriceUpdateTool = tool({
  name: 'bulk_price_update',
  description: 'Update prices for multiple products or variants in bulk',
  parameters: z.object({
    updates: z.array(z.object({
      product_id: z.string().default('').describe('Product ID'),
      variant_id: z.string().default('').describe('Variant ID'),
      sku: z.string().default('').describe('SKU'),
      price: z.string().describe('New price'),
      compare_at_price: z.string().default('').describe('Compare at price')
    })).describe('Array of price updates'),
    price_list_id: z.string().default('').describe('Price list ID for specific markets (e.g., USD pricing)')
  }),
  execute: async (args) => {
    args = args || {};
    if (args.sku && typeof args.sku === "string") { args.sku = args.sku.trim(); }
    if (args.sku && !Array.isArray(args.sku)) { args.sku = [args.sku]; }
    try {
      const result = await customToolDiscovery.executeTool('bulk_price_update', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const createComboTool = tool({
  name: 'create_combo',
  description: 'Create a combo/bundle product from multiple existing products',
  parameters: z.object({
    title: z.string().describe('Combo product title'),
    product_ids: z.array(z.string()).describe('Product IDs to include in combo'),
    combo_price: z.string().describe('Total combo price'),
    description: z.string().default('').describe('Combo description'),
    create_as_draft: z.boolean().default(true).describe('Create in draft status')
  }),
  execute: async (args) => {
    args = args || {};
    if (args.sku && typeof args.sku === "string") { args.sku = args.sku.trim(); }
    if (args.sku && !Array.isArray(args.sku)) { args.sku = [args.sku]; }
    try {
      const result = await customToolDiscovery.executeTool('create_combo', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

export const createOpenBoxTool = tool({
  name: 'create_open_box',
  description: 'Create an open box variant of an existing product',
  parameters: z.object({
    product_id: z.string().describe('Original product ID'),
    discount_percentage: z.number().default(15).describe('Discount percentage for open box'),
    condition_notes: z.string().default('Open box - inspected and certified').describe('Condition description'),
    inventory_quantity: z.number().default(1).describe('Available quantity')
  }),
  execute: async (args) => {
    args = args || {};
    if (args.sku && typeof args.sku === "string") { args.sku = args.sku.trim(); }
    if (args.sku && !Array.isArray(args.sku)) { args.sku = [args.sku]; }
    try {
      const result = await customToolDiscovery.executeTool('create_open_box', args);
      return JSON.stringify(result);
    } catch (error) {
      return JSON.stringify({ error: error.message });
    }
  }
});

// Export all extended tools
export const extendedShopifyTools = [
  manageInventoryPolicyTool,
  manageMAPSalesTool,
  manageTagsTool,
  manageVariantLinksTool,
  perplexityTool,
  uploadToSkuVaultTool,
  bulkPriceUpdateTool,
  createComboTool,
  createOpenBoxTool
];