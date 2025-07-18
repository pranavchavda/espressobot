/**
 * Direct MCP Agent Tools for EspressoBot1
 * Provides direct access to specialized MCP agents without routing overhead
 */

import { z } from 'zod';
import { tool } from '@openai/agents';

// Import all specialized agents
import { executeProductsTask } from '../agents/products-agent.js';
import { executePricingTask } from '../agents/pricing-agent.js';
import { executeInventoryTask } from '../agents/inventory-agent.js';
import { executeSalesTask } from '../agents/sales-agent.js';
import { executeFeaturesTask } from '../agents/features-agent.js';
import { executeMediaTask } from '../agents/media-agent.js';
import { executeIntegrationsTask } from '../agents/integrations-agent.js';
import { executeProductManagementTask } from '../agents/product-management-agent.js';
import { executeUtilityTask } from '../agents/utility-agent.js';
import { executeDocumentationQuery } from '../agents/documentation-mcp-agent.js';
import { executeExternalMCPTask } from '../agents/external-mcp-agent.js';

/**
 * Products Agent - Basic product operations and GraphQL
 */
export function createProductsAgentTool() {
  return tool({
    name: 'products_agent',
    description: 'Product operations: get_product, search_products, create_product, update_status, graphql_query, graphql_mutation',
    parameters: z.object({
      task: z.string().describe('The product operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Products Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeProductsTask(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Products Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Pricing Agent - Price management and cost tracking
 */
export function createPricingAgentTool() {
  return tool({
    name: 'pricing_agent',
    description: 'Pricing operations: update_pricing, bulk_price_update, update_costs',
    parameters: z.object({
      task: z.string().describe('The pricing operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Pricing Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executePricingTask(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Pricing Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Inventory Agent - Stock management and tagging
 */
export function createInventoryAgentTool() {
  return tool({
    name: 'inventory_agent',
    description: 'Inventory operations: manage_inventory_policy, manage_tags, manage_redirects',
    parameters: z.object({
      task: z.string().describe('The inventory operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Inventory Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeInventoryTask(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Inventory Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Sales Agent - MAP sales management
 */
export function createSalesAgentTool() {
  return tool({
    name: 'sales_agent',
    description: 'Sales operations: manage_miele_sales, manage_map_sales',
    parameters: z.object({
      task: z.string().describe('The sales operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Sales Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeSalesTask(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Sales Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Features Agent - Content and metafields
 */
export function createFeaturesAgentTool() {
  return tool({
    name: 'features_agent',
    description: 'Content operations: manage_features_metaobjects, update_metafields, manage_variant_links',
    parameters: z.object({
      task: z.string().describe('The features operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Features Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeFeaturesTask(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Features Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Media Agent - Image management
 */
export function createMediaAgentTool() {
  return tool({
    name: 'media_agent',
    description: 'Image operations: add_product_images (add, list, delete, reorder, clear)',
    parameters: z.object({
      task: z.string().describe('The media operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Media Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeMediaTask(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Media Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Integrations Agent - External systems
 */
export function createIntegrationsAgentTool() {
  return tool({
    name: 'integrations_agent',
    description: 'Integration operations: upload_to_skuvault, manage_skuvault_kits, send_review_request, perplexity_research',
    parameters: z.object({
      task: z.string().describe('The integration operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Integrations Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeIntegrationsTask(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Integrations Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Product Management Agent - Complex product operations
 */
export function createProductManagementAgentTool() {
  return tool({
    name: 'product_management_agent',
    description: 'Complex operations: add_variants_to_product, create_full_product, update_full_product, create_combo, create_open_box',
    parameters: z.object({
      task: z.string().describe('The product management operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Product Management Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeProductManagementTask(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Product Management Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Utility Agent - Memory operations
 */
export function createUtilityAgentTool() {
  return tool({
    name: 'utility_agent',
    description: 'Utility operations: memory_operations (search, add, list, delete)',
    parameters: z.object({
      task: z.string().describe('The utility operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[Utility Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeUtilityTask(
          task, 
          global.currentConversationId,
          {}
        );
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[Utility Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Documentation Agent - API documentation and schema
 */
export function createDocumentationAgentTool() {
  return tool({
    name: 'documentation_agent',
    description: 'Query Shopify API documentation and schema',
    parameters: z.object({
      query: z.string().describe('The documentation query or schema search')
    }),
    execute: async ({ query }) => {
      console.log(`[Documentation Agent] Querying: ${query.substring(0, 100)}...`);
      
      try {
        const result = await executeDocumentationQuery(query, {});
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Query failed'}`;
        }
        
        return result.result || result || 'Query completed successfully';
        
      } catch (error) {
        console.error(`[Documentation Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * External MCP Agent - External server operations
 */
export function createExternalMCPAgentTool() {
  return tool({
    name: 'external_mcp_agent',
    description: 'Execute external MCP server operations',
    parameters: z.object({
      task: z.string().describe('The external operation to perform')
    }),
    execute: async ({ task }) => {
      console.log(`[External MCP Agent] Executing: ${task.substring(0, 100)}...`);
      
      try {
        const result = await executeExternalMCPTask(task, {});
        
        if (result && result.success === false) {
          return `Error: ${result.error || 'Operation failed'}`;
        }
        
        return result.result || result || 'Task completed successfully';
        
      } catch (error) {
        console.error(`[External MCP Agent] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

/**
 * Smart routing based on task analysis
 */
export function createSmartMCPExecuteTool() {
  return tool({
    name: 'smart_mcp_execute',
    description: 'Intelligently route to the best specialized agent based on task content',
    parameters: z.object({
      task: z.string().describe('The task to execute')
    }),
    execute: async ({ task }) => {
      console.log(`[Smart MCP Execute] Analyzing task: ${task.substring(0, 100)}...`);
      
      const taskLower = task.toLowerCase();
      
      try {
        // Route based on keywords - same logic as Python Tools Agent V2
        if (taskLower.includes('memory') || taskLower.includes('remember')) {
          console.log('[Smart MCP Execute] Routing to Utility Agent');
          return await executeUtilityTask(task, global.currentConversationId, {});
        }
        
        if (taskLower.includes('image') || taskLower.includes('photo') || taskLower.includes('media')) {
          console.log('[Smart MCP Execute] Routing to Media Agent');
          return await executeMediaTask(task, global.currentConversationId, {});
        }
        
        if (taskLower.includes('price') || taskLower.includes('cost') || taskLower.includes('discount')) {
          console.log('[Smart MCP Execute] Routing to Pricing Agent');
          return await executePricingTask(task, global.currentConversationId, {});
        }
        
        if (taskLower.includes('inventory') || taskLower.includes('stock') || taskLower.includes('tag') || taskLower.includes('redirect')) {
          console.log('[Smart MCP Execute] Routing to Inventory Agent');
          return await executeInventoryTask(task, global.currentConversationId, {});
        }
        
        if (taskLower.includes('miele') || taskLower.includes('breville') || taskLower.includes('map sale')) {
          console.log('[Smart MCP Execute] Routing to Sales Agent');
          return await executeSalesTask(task, global.currentConversationId, {});
        }
        
        if (taskLower.includes('feature') || taskLower.includes('metafield') || taskLower.includes('content')) {
          console.log('[Smart MCP Execute] Routing to Features Agent');
          return await executeFeaturesTask(task, global.currentConversationId, {});
        }
        
        if (taskLower.includes('skuvault') || taskLower.includes('review') || taskLower.includes('research')) {
          console.log('[Smart MCP Execute] Routing to Integrations Agent');
          return await executeIntegrationsTask(task, global.currentConversationId, {});
        }
        
        if (taskLower.includes('variant') || taskLower.includes('combo') || taskLower.includes('open box') || taskLower.includes('create full')) {
          console.log('[Smart MCP Execute] Routing to Product Management Agent');
          return await executeProductManagementTask(task, global.currentConversationId, {});
        }
        
        if (taskLower.includes('documentation') || taskLower.includes('schema') || taskLower.includes('api')) {
          console.log('[Smart MCP Execute] Routing to Documentation Agent');
          return await executeDocumentationQuery(task, {});
        }
        
        // Default to Products Agent for general product operations
        console.log('[Smart MCP Execute] Defaulting to Products Agent');
        return await executeProductsTask(task, global.currentConversationId, {});
        
      } catch (error) {
        console.error(`[Smart MCP Execute] Failed:`, error);
        return `Error: ${error.message}`;
      }
    }
  });
}

