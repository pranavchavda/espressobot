/**
 * Static list of available operations for task planning
 * This replaces the need to discover and test MCP tools at startup
 */

export const availableOperations = {
  // Products Agent operations
  productsOperations: [
    'get_product',
    'search_products',
    'create_product',
    'update_status',
    'graphql_query',
    'graphql_mutation'
  ],
  
  // Pricing Agent operations
  pricingOperations: [
    'update_pricing',
    'bulk_price_update',
    'update_costs'
  ],
  
  // Inventory Agent operations
  inventoryOperations: [
    'manage_inventory_policy',
    'manage_tags',
    'manage_redirects'
  ],
  
  // Sales Agent operations
  salesOperations: [
    'manage_miele_sales',
    'manage_map_sales'
  ],
  
  // Features Agent operations
  featuresOperations: [
    'manage_features_metaobjects',
    'update_metafields',
    'manage_variant_links'
  ],
  
  // Media Agent operations
  mediaOperations: [
    'add_product_images'
  ],
  
  // Integrations Agent operations
  integrationsOperations: [
    'upload_to_skuvault',
    'manage_skuvault_kits',
    'send_review_request',
    'perplexity_research'
  ],
  
  // Product Management Agent operations
  productManagementOperations: [
    'add_variants_to_product',
    'create_full_product',
    'update_full_product',
    'create_combo',
    'create_open_box'
  ],
  
  // Utility Agent operations
  utilityOperations: [
    'memory_operations'
  ],
  
  // Documentation Agent operations
  documentationOperations: [
    'introspect_admin_schema',
    'search_dev_docs',
    'fetch_docs_by_path',
    'get_started'
  ],
  
  // External MCP Agent operations
  externalOperations: [
    'fetch' // Web content fetching
  ],
  
  // Google Workspace Agent operations (direct API tools)
  googleWorkspaceOperations: [
    'gmail_search',
    'gmail_send',
    'calendar_list_events',
    'calendar_create_event',
    'drive_search',
    'tasks_list_tasklists',
    'tasks_list',
    'tasks_create',
    'tasks_update',
    'tasks_delete',
    'tasks_complete',
    'tasks_list_all'
  ],
  
  // GA4 Analytics Agent operations
  ga4AnalyticsOperations: [
    'analytics_run_report',
    'analytics_get_realtime',
    'analytics_get_ecommerce',
    'analytics_get_traffic_sources',
    'analytics_get_product_performance',
    'analytics_get_ads_performance',
    'analytics_get_campaign_performance',
    'analytics_get_ads_keywords',
    'analytics_compare_channels'
  ],
  
  // Native orchestrator tools
  orchestratorTools: [
    'search_tool_cache',
    'spawn_bash_agent',
    'spawn_swe_agent',
    'spawn_parallel_executors',
    'task_planner',
    'view_image',
    'parse_file',
    'save_file',
    'file_operations',
    // Direct agent access tools
    'products_agent',
    'pricing_agent',
    'inventory_agent',
    'sales_agent',
    'features_agent',
    'media_agent',
    'integrations_agent',
    'product_management_agent',
    'utility_agent',
    'documentation_agent',
    'external_mcp_agent',
    'google_workspace_agent',
    'ga4_analytics_agent',
    'smart_mcp_execute'
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
    ...availableOperations.productsOperations,
    ...availableOperations.pricingOperations,
    ...availableOperations.inventoryOperations,
    ...availableOperations.salesOperations,
    ...availableOperations.featuresOperations,
    ...availableOperations.mediaOperations,
    ...availableOperations.integrationsOperations,
    ...availableOperations.productManagementOperations,
    ...availableOperations.utilityOperations,
    ...availableOperations.documentationOperations,
    ...availableOperations.externalOperations,
    ...availableOperations.googleWorkspaceOperations,
    ...availableOperations.ga4AnalyticsOperations,
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
 * Get the appropriate agent for an operation
 */
export function getAgentForOperation(operationName) {
  const agentMap = {
    productsOperations: 'products_agent',
    pricingOperations: 'pricing_agent',
    inventoryOperations: 'inventory_agent',
    salesOperations: 'sales_agent',
    featuresOperations: 'features_agent',
    mediaOperations: 'media_agent',
    integrationsOperations: 'integrations_agent',
    productManagementOperations: 'product_management_agent',
    utilityOperations: 'utility_agent',
    documentationOperations: 'documentation_agent',
    externalOperations: 'external_mcp_agent',
    googleWorkspaceOperations: 'google_workspace_agent',
    ga4AnalyticsOperations: 'ga4_analytics_agent',
    fileOperations: 'spawn_bash_agent'
  };
  
  const category = getOperationCategory(operationName);
  return agentMap[category] || null;
}