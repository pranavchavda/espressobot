import { getSmartContext } from '../context-loader/context-manager.js';
import { memoryOperations } from '../memory/memory-operations-local.js';
import { stripProductKeys, stripProductArray } from './product-key-stripper.js';

/**
 * Build a core context slice with essential information only
 * This is the minimal context needed for most operations
 */
export async function buildCoreContext(options) {
  const { 
    task, 
    conversationId, 
    userId, 
    userMessage, 
    autonomyLevel,
    conversationHistory = [],
    userProfile = null
  } = options;
  
  console.log(`[CONTEXT] Building core context slice`);
  
  const coreContext = {
    task,
    conversationId,
    userId,
    userProfile,
    autonomyLevel,
    // Only most recent memories (top-5)
    relevantMemories: [],
    // Core business rules only
    relevantRules: [],
    // Last 3 conversation turns
    conversationHistory: conversationHistory.slice(-3),
    // Current task status only
    currentTasks: [],
    // Essential state only
    stateTracking: {
      hasProducts: false,
      hasPricing: false,
      isBulkOperation: false
    }
  };
  
  // Get top-5 memories only for core context
  if (userId) {
    try {
      const memories = await memoryOperations.search(task, `user_${userId}`, 5);
      coreContext.relevantMemories = memories.map(m => ({
        content: m.memory,
        score: m.score
      }));
    } catch (error) {
      console.log(`[CONTEXT] Error searching memories:`, error.message);
    }
  }
  
  // Get relevant prompt fragments from library (top-3 for core context)
  try {
    const promptFragments = await memoryOperations.searchSystemPromptFragments(task, 5);
    console.log(`[CONTEXT] Raw prompt fragments found: ${promptFragments?.length || 0}`);
    
    if (promptFragments && promptFragments.length > 0) {
      // Take top 3 fragments, preferring high/critical priority
      const sortedFragments = promptFragments.sort((a, b) => {
        // Priority order: critical > high > medium
        const priorityScore = {critical: 3, high: 2, medium: 1};
        const aScore = priorityScore[a.metadata?.priority] || 0;
        const bScore = priorityScore[b.metadata?.priority] || 0;
        return bScore - aScore;
      });
      
      coreContext.promptFragments = sortedFragments.slice(0, 3).map(f => ({
        content: f.memory,
        category: f.metadata?.category,
        priority: f.metadata?.priority,
        score: f.score
      }));
      
      console.log(`[CONTEXT] Added ${coreContext.promptFragments.length} prompt fragments to core context`);
      coreContext.promptFragments.forEach((f, i) => {
        console.log(`  ${i+1}. [${f.priority}] ${f.category}: ${f.content.substring(0, 60)}...`);
      });
    }
  } catch (error) {
    console.log(`[CONTEXT] Error searching prompt fragments:`, error.message);
    coreContext.promptFragments = [];
  }
  
  // Extract only core business rules
  try {
    const smartContext = await getSmartContext(task, {
      includeMemory: false,
      userId: userId ? `user_${userId}` : null,
      conversationId,
      minimal: true // Request minimal context
    });
    
    // Parse only essential rules
    const sections = smartContext.split(/\n## /);
    for (const section of sections) {
      if (section.includes('Business Rules')) {
        // Filter to only critical rules
        const rules = section.split('\n').filter(line => {
          const trimmed = line.trim();
          return trimmed && (
            trimmed.includes('CRITICAL') ||
            trimmed.includes('ALWAYS') ||
            trimmed.includes('NEVER') ||
            trimmed.includes('MAP')
          );
        });
        coreContext.relevantRules = rules.slice(0, 10); // Max 10 core rules
      }
    }
  } catch (error) {
    console.log(`[CONTEXT] Error loading core rules:`, error.message);
  }
  
  // Basic state tracking
  coreContext.stateTracking.hasProducts = /product|sku|item/i.test(task);
  coreContext.stateTracking.hasPricing = /price|\$|cost|discount/i.test(task);
  coreContext.stateTracking.isBulkOperation = /bulk|all|multiple|batch|\d{2,}/i.test(task);
  
  // Add minimal business logic for core context
  coreContext.businessLogic = {
    patterns: [],
    warnings: [],
    requirements: []
  };
  
  // Detect critical patterns even in core context
  if (/remove.*discount|set.*base.*price.*compare/i.test(task)) {
    coreContext.businessLogic.patterns.push({
      type: 'discount_removal',
      critical: true
    });
  }
  if (/MAP|minimum.*advertised|miele.*sale|breville.*sale/i.test(task)) {
    coreContext.businessLogic.patterns.push({
      type: 'map_pricing',
      critical: true
    });
  }
  
  return coreContext;
}

/**
 * Build a full context slice with comprehensive information
 * This includes all data for complex operations
 */
export async function buildFullContext(options, coreContext = null) {
  const { 
    task, 
    conversationId, 
    userId, 
    userMessage, 
    autonomyLevel,
    additionalContext,
    includeProductBlobs = true,
    includeExtendedHistory = true,
    includeAllMemories = true,
    userProfile = null
  } = options;
  
  console.log(`[CONTEXT] Building full context slice`);
  
  // Start with core context if provided, otherwise build it
  const fullContext = coreContext || await buildCoreContext(options);
  
  // Extend with full data
  fullContext.fullSlice = true;
  
  // Get extended memories (up to 15)
  if (includeAllMemories && userId) {
    try {
      const memories = await memoryOperations.search(task, `user_${userId}`, 15);
      fullContext.relevantMemories = memories.map(m => ({
        content: m.memory,
        score: m.score,
        metadata: m.metadata
      }));
    } catch (error) {
      console.log(`[CONTEXT] Error loading extended memories:`, error.message);
    }
  }
  
  // Get ALL relevant prompt fragments for full context (up to 10)
  try {
    const promptFragments = await memoryOperations.searchSystemPromptFragments(task, 10);
    if (promptFragments && promptFragments.length > 0) {
      fullContext.promptFragments = promptFragments.map(f => ({
        content: f.memory,
        category: f.metadata?.category,
        priority: f.metadata?.priority,
        tags: f.metadata?.tags,
        agentType: f.metadata?.agent_type,
        score: f.score
      }));
      console.log(`[CONTEXT] Found ${fullContext.promptFragments.length} prompt fragments for full context`);
      
      // Group by category for better organization
      fullContext.promptFragmentsByCategory = {};
      fullContext.promptFragments.forEach(f => {
        const cat = f.category || 'general';
        if (!fullContext.promptFragmentsByCategory[cat]) {
          fullContext.promptFragmentsByCategory[cat] = [];
        }
        fullContext.promptFragmentsByCategory[cat].push(f);
      });
    }
  } catch (error) {
    console.log(`[CONTEXT] Error loading prompt fragments:`, error.message);
    fullContext.promptFragments = [];
  }
  
  // Get full conversation history (up to 10 turns)
  if (includeExtendedHistory && conversationId) {
    // For now, use the provided conversation history or empty array
    // In production, this would fetch from database
    fullContext.conversationHistory = options.conversationHistory || [];
  }
  
  // Get all business rules and tools
  try {
    const smartContext = await getSmartContext(task, {
      includeMemory: false,
      userId: userId ? `user_${userId}` : null,
      conversationId,
      minimal: false // Request full context
    });
    
    // Parse all sections
    const sections = smartContext.split(/\n## /);
    for (const section of sections) {
      if (section.includes('Business Rules')) {
        fullContext.relevantRules = section.split('\n').filter(line => line.trim());
      } else if (section.includes('Tools')) {
        fullContext.relevantTools = section.split('\n').filter(line => line.trim());
      } else if (section.includes('Workflow')) {
        fullContext.relevantWorkflows = section.split('\n').filter(line => line.trim());
      }
    }
  } catch (error) {
    console.log(`[CONTEXT] Error loading full smart context:`, error.message);
  }
  
  // Add product blobs if needed (this is the largest contributor)
  if (includeProductBlobs) {
    fullContext.productBlobs = await extractProductBlobs(fullContext.specificEntities);
  }
  
  // Add full business logic analysis
  fullContext.businessLogic = analyzeBusinessLogic(task, userMessage);
  
  // Add any additional context
  if (additionalContext) {
    fullContext.additionalContext = additionalContext;
  }
  
  return fullContext;
}


/**
 * Extract product blobs for referenced products (expensive operation)
 */
async function extractProductBlobs(entities) {
  const productBlobs = [];
  const skuEntities = entities.find(e => e.type === 'skus');
  
  if (!skuEntities || skuEntities.values.length === 0) {
    return productBlobs;
  }
  
  // Limit to first 10 SKUs to prevent context explosion
  const skusToFetch = skuEntities.values.slice(0, 10);
  
  console.log(`[CONTEXT] Fetching product blobs for ${skusToFetch.length} SKUs`);
  
  // Import the MCP tool for getting products
  try {
    const { getProductTool } = await import('../native-tools/get-product.js');
    
    // Fetch products in parallel
    const fetchPromises = skusToFetch.map(async (sku) => {
      try {
        const product = await getProductTool.execute({ sku });
        // Strip unnecessary keys to reduce size
        return stripProductKeys(product);
      } catch (error) {
        console.log(`[CONTEXT] Failed to fetch product ${sku}:`, error.message);
        return null;
      }
    });
    
    const results = await Promise.all(fetchPromises);
    return results.filter(p => p !== null);
  } catch (error) {
    console.log(`[CONTEXT] Error loading product tool:`, error.message);
    // Fallback to empty array if tool not available
    return [];
  }
}

/**
 * Analyze task for business logic patterns
 */
function analyzeBusinessLogic(task, fullMessage) {
  const logic = {
    patterns: [],
    warnings: [],
    requirements: []
  };
  
  // Discount patterns
  if (/remove.*discount|set.*base.*price.*compare/i.test(task)) {
    logic.patterns.push({
      type: 'discount_removal',
      action: 'Set base price to compare_at_price value',
      warning: 'Preserve original compare_at_price before updating'
    });
  }
  
  // Bulk operations
  const bulkMatch = task.match(/(\d+)\+?\s*(?:products?|items?)/i);
  if (bulkMatch && parseInt(bulkMatch[1]) > 10) {
    logic.patterns.push({
      type: 'bulk_operation',
      itemCount: parseInt(bulkMatch[1]),
      warning: 'High-impact operation affecting many items',
      requirement: 'Use batch processing for efficiency'
    });
    logic.warnings.push(`This operation affects ${bulkMatch[1]} items`);
  }
  
  // Price updates
  if (/update.*price|change.*price|set.*price/i.test(task)) {
    logic.patterns.push({
      type: 'price_update',
      action: 'Update product pricing',
      reminder: 'Check for compare_at_price to maintain discount structure'
    });
  }
  
  // Inventory policy
  if (/inventory.*policy|oversell|backorder/i.test(task)) {
    logic.patterns.push({
      type: 'inventory_policy',
      action: 'Manage inventory selling policy',
      options: ['DENY (no overselling)', 'CONTINUE (allow overselling)']
    });
  }
  
  // MAP pricing
  if (/MAP|minimum.*advertised|miele.*sale|breville.*sale/i.test(task)) {
    logic.patterns.push({
      type: 'map_pricing',
      action: 'Apply MAP-compliant pricing',
      warning: 'Must follow manufacturer pricing agreements',
      requirement: 'Check MAP calendar for approved prices'
    });
    logic.warnings.push('MAP pricing rules apply - verify compliance');
  }
  
  return logic;
}

/**
 * Determine if full context is needed based on task analysis
 */
export function requiresFullContext(task, userMessage = '') {
  const fullMessage = `${task} ${userMessage}`.toLowerCase();
  
  // Patterns that require full context
  const fullContextPatterns = [
    /bulk|batch|multiple|all\s+products/i,
    /catalog|entire|complete\s+list/i,
    /\d{3,}\s*(?:products?|items?|skus?)/i, // 100+ items
    /json.*array|array.*json|csv|export/i,
    /complex|detailed|comprehensive/i,
    /migrate|transform|convert\s+all/i
  ];
  
  // Check for patterns
  for (const pattern of fullContextPatterns) {
    if (pattern.test(fullMessage)) {
      console.log(`[CONTEXT] Full context required - matched pattern: ${pattern}`);
      return true;
    }
  }
  
  // Check for large input data
  if (userMessage.length > 5000 || (userMessage.includes('{') && userMessage.includes('}'))) {
    console.log(`[CONTEXT] Full context required - large input data`);
    return true;
  }
  
  // Check entity count
  const skuMatches = fullMessage.match(/\b[A-Z]{2,}-?\d{3,}[A-Z]?\b/g) || [];
  if (skuMatches.length > 5) {
    console.log(`[CONTEXT] Full context required - ${skuMatches.length} SKUs referenced`);
    return true;
  }
  
  return false;
}

/**
 * Build context with automatic tier selection
 */
export async function buildTieredContext(options) {
  const { task, userMessage = '', forceFullContext = false } = options;
  
  // Check if full context is needed
  const needsFullContext = forceFullContext || requiresFullContext(task, userMessage);
  
  if (needsFullContext) {
    console.log(`[CONTEXT] Using FULL context slice`);
    return await buildFullContext(options);
  } else {
    console.log(`[CONTEXT] Using CORE context slice`);
    return await buildCoreContext(options);
  }
}