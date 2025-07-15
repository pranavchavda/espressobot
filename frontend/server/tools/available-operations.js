/**
 * Static list of available operations for task planning
 * This replaces the need to discover and test MCP tools at startup
 */

export const availableOperations = {
  // Python MCP Tools (via spawn_mcp_agent)
  shopifyOperations: [
    'search_products',
    'get_product',
    'create_product',
    'update_status',
    'update_pricing',
    'bulk_price_update',
    'manage_tags',
    'manage_inventory_policy',
    'add_product_images',
    'create_open_box',
    'create_full_product',
    'add_variants_to_product',
    'create_combo',
    'manage_variant_links',
    'update_full_product',
    'manage_features_metaobjects',
    'manage_redirects',
    'manage_miele_sales',
    'manage_map_sales',
    'upload_to_skuvault',
    'manage_skuvault_kits',
    'send_review_request',
    'graphql_query',
    'graphql_mutation'
  ],
  
  // Memory operations (via spawn_mcp_agent)
  memoryOperations: [
    'memory_search',
    'memory_add',
    'memory_list',
    'memory_delete'
  ],
  
  // Research operations (via spawn_mcp_agent)
  researchOperations: [
    'perplexity_research'
  ],
  
  // Documentation operations (via spawn_mcp_agent)
  documentationOperations: [
    'introspect_admin_schema',
    'search_dev_docs',
    'fetch_docs_by_path',
    'get_started'
  ],
  
  // External operations (via spawn_mcp_agent)
  externalOperations: [
    'fetch' // Web content fetching
  ],
  
  // Native orchestrator tools
  orchestratorTools: [
    'search_tool_cache',
    'spawn_mcp_agent',
    'spawn_bash_agent',
    'spawn_swe_agent',
    'spawn_parallel_bash_agents',
    'spawn_parallel_executors',
    'task_planner',
    'view_image',
    'parse_file',
    'save_file',
    'file_operations'
  ],
  
  // File system operations (via spawn_bash_agent)
  fileOperations: [
    'read_file',
    'write_file',
    'list_directory',
    'create_directory',
    'delete_file',
    'move_file',
    'copy_file'
  ]
};

/**
 * Get all available operation names for task planning
 */
export function getAllOperationNames() {
  return [
    ...availableOperations.orchestratorTools,
    ...availableOperations.shopifyOperations,
    ...availableOperations.memoryOperations,
    ...availableOperations.researchOperations,
    ...availableOperations.documentationOperations,
    ...availableOperations.externalOperations,
    ...availableOperations.fileOperations
  ];
}

/**
 * Get operation category
 */
export function getOperationCategory(operationName) {
  for (const [category, operations] of Object.entries(availableOperations)) {
    if (operations.includes(operationName)) {
      return category;
    }
  }
  return 'unknown';
}

/**
 * Check if an operation requires MCP agent
 */
export function requiresMCPAgent(operationName) {
  return availableOperations.shopifyOperations.includes(operationName) ||
         availableOperations.memoryOperations.includes(operationName) ||
         availableOperations.researchOperations.includes(operationName) ||
         availableOperations.documentationOperations.includes(operationName) ||
         availableOperations.externalOperations.includes(operationName);
}