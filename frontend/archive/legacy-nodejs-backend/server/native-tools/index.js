/**
 * Native JavaScript tools for Shopify operations
 * These tools provide direct implementation without Python subprocess overhead
 */

// Import individual tools
import { searchProductsTool } from './search-products.js';
import { getProductTool } from './get-product.js';
import { updatePricingTool } from './update-pricing.js';
import { manageTagsTool, addTagsTool, removeTagsTool } from './manage-tags.js';
import { updateStatusTool, publishProductTool, unpublishProductTool, archiveProductTool } from './update-status.js';

// Export all tools
export const nativeTools = {
  // Core tools
  search_products: searchProductsTool,
  get_product: getProductTool,
  update_pricing: updatePricingTool,
  manage_tags: manageTagsTool,
  add_tags_to_product: addTagsTool,
  remove_tags_from_product: removeTagsTool,
  update_product_status: updateStatusTool,
  
  // Convenience tools
  publish_product: publishProductTool,
  unpublish_product: unpublishProductTool,
  archive_product: archiveProductTool,
};

/**
 * Register all native tools with the tool registry
 * @param {CustomToolRegistry} toolRegistry - The tool registry instance
 */
export function registerNativeTools(toolRegistry) {
  // Get feature flag for native tools
  const useNativeTools = process.env.USE_NATIVE_TOOLS === 'true';
  
  if (!useNativeTools) {
    console.log('Native tools disabled. Set USE_NATIVE_TOOLS=true to enable.');
    return;
  }
  
  console.log('Registering native JavaScript tools...');
  
  // Register each tool
  for (const [name, tool] of Object.entries(nativeTools)) {
    try {
      toolRegistry.registerNativeTool(tool);
      console.log(`✅ Registered native tool: ${name}`);
    } catch (error) {
      console.error(`❌ Failed to register native tool ${name}:`, error.message);
    }
  }
  
  console.log(`Registered ${Object.keys(nativeTools).length} native tools`);
}

// Export individual tools for direct import
export { 
  searchProductsTool,
  getProductTool,
  updatePricingTool,
  manageTagsTool,
  addTagsTool,
  removeTagsTool,
  updateStatusTool,
  publishProductTool,
  unpublishProductTool,
  archiveProductTool
};