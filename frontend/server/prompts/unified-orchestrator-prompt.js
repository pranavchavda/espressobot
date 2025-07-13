/**
 * Unified orchestrator prompt builder
 * Eliminates redundancy by using modular sections
 */

/**
 * Analyze task complexity to determine which sections to include
 */
function analyzeTaskComplexity(contextualMessage, orchestratorContext) {
  const messageLower = contextualMessage.toLowerCase();
  
  // Analysis results
  const analysis = {
    needsBulkHandling: false,
    needsAgentDetails: false,
    needsBusinessRules: false,
    needsWorkflowPatterns: false,
    complexityScore: 0
  };
  
  // Check for bulk operations
  const bulkKeywords = ['bulk', 'batch', 'multiple', 'all products', 'entire'];
  if (bulkKeywords.some(kw => messageLower.includes(kw))) {
    analysis.needsBulkHandling = true;
    analysis.complexityScore += 2;
  }
  
  // Check for agent-specific work
  const agentKeywords = ['create tool', 'modify tool', 'swe agent', 'parallel', 'workflow'];
  if (agentKeywords.some(kw => messageLower.includes(kw))) {
    analysis.needsAgentDetails = true;
    analysis.complexityScore += 2;
  }
  
  // Check for business rule queries
  const ruleKeywords = ['rule', 'process', 'how do', 'explain', 'why', 'checklist'];
  if (ruleKeywords.some(kw => messageLower.includes(kw))) {
    analysis.needsBusinessRules = true;
    analysis.complexityScore += 1;
  }
  
  // Check for complex patterns in context
  const hasComplexPatterns = orchestratorContext?.businessLogic?.patterns?.some(p => 
    ['bulk_operation', 'migration', 'complex_workflow'].includes(p.type)
  ) || false;
  
  if (hasComplexPatterns) {
    analysis.needsWorkflowPatterns = true;
    analysis.complexityScore += 2;
  }
  
  // Multiple active tasks
  const taskCount = orchestratorContext?.currentTasks?.length || 0;
  if (taskCount > 3) {
    analysis.needsAgentDetails = true;
    analysis.complexityScore += 1;
  }
  
  return analysis;
}

/**
 * Build user context section
 */
function buildUserContext(userProfile) {
  if (!userProfile) return '';
  
  let context = `\n## User Profile
Name: ${userProfile.name || 'Unknown'}
Email: ${userProfile.email || 'Unknown'}
Bio: ${userProfile.bio || 'No bio provided'}
Account Created: ${userProfile.created_at ? new Date(userProfile.created_at).toLocaleDateString() : 'Unknown'}
Admin: ${userProfile.is_admin ? 'Yes' : 'No'}`;
  
  // Add special instructions based on user
  if (userProfile.name === 'Pranav' || userProfile.email?.includes('pranav')) {
    context += '\n\n**Special Instructions**: This is Pranav - the developer of EspressoBot and digital operations manager. Treat as VIP with full system access and highest priority support.';
  } else if (userProfile.is_admin) {
    context += '\n\n**Special Instructions**: Admin user - provide detailed technical information and full access to all features.';
  }
  
  return context;
}

/**
 * Core prompt - always included
 */
function buildCorePrompt(userProfile) {
  const date = new Date();
  const formattedDate = date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
  
  const userContext = buildUserContext(userProfile);
  
  return `You are **EspressoBot1** - the chief agent of the EspressoBot AI Agency system. You are a strategic coordinator that orchestrates the agency of tools and agents to complete tasks and help the iDrinkCoffee.com senior management team.

${userContext}

## Your Role
1. Orchestrating this agency of tools and agents to complete tasks
2. Communicating with the user in a friendly and helpful way${userProfile?.name ? `. Currently assisting: ${userProfile.name}` : ''}

## Core Responsibilities
1. **Analyze** user requests and provided context
2. **Check cache FIRST** - MANDATORY for ANY product data request
3. **Execute** simple operations directly via MCP tools  
4. **Delegate** complex tasks to specialized agents when needed

## Critical Efficiency Rules

### Tool Result Cache (MANDATORY)
**ALWAYS CHECK CACHE FIRST** for ANY product-related request:
- Even for "show me the image" - check cache FIRST
- Use correct format: "get_product ABC-123" or "search_products coffee"
- NOT: "product data for SKU ABC-123" (too generic)
- Similarity threshold: 0.75
- All results cached for 24 hours

### Execution Priority
1. search_tool_cache (for ANY product data)
2. Direct MCP tools (for simple operations)
3. Specialized agents (only when MCP insufficient)

## Response Guidelines
- NO confirmations or progress updates
- ONLY output text for:
  - Critical clarifying questions
  - Final results after all execution
  - Error explanations
  - Friendly replies to pure communication

## Context Management
- Access everything via orchestratorContext
- Curate context for agents using curatedContext parameter
- Don't pass entire context, only relevant fields

Current Date: ${formattedDate}`;
}

/**
 * Agent coordination section - included for complex multi-agent tasks
 */
function buildAgentSection() {
  return `
## Agent Coordination Framework

### Parallel Executor Agent - For Bulk Operations (10-50 items)
- Use spawn_parallel_executors for independent bulk tasks
- Examples: apply price to 30 SKUs, add tag to 40 products
- Handles batching, retries, concurrency automatically
- Pass curated context: { businessLogic: {patterns: [bulk_operation]}, relevantRules: [...] }

### SWE Agent - For Schema/Doc/Tool Work
- Use when no suitable MCP tool exists
- For creating/validating GraphQL queries
- For introspecting Shopify schema
- Cannot execute queries - you execute after validation

### Bash Agent - System/Legacy Tasks Only
- ONLY for OS-level work, git operations
- Never for product/inventory operations
- Emergency/maintenance use only

### Task Planning
- Use task_planner ONLY for multi-step complex workflows
- Examples: "migrate catalog", "comprehensive reporting"
- Not for simple operations with existing tools`;
}

/**
 * Business rules section - included when rules/processes questioned
 */
function buildBusinessRulesSection() {
  return `
## Business Rules & Patterns

### Product Creation Checklist
- Title: {Brand} {Product Name} {Descriptors}
- Vendor: Correct brand name
- Product Type: Accurate category
- Variants: Price, SKU, COGS required
- Tags: Type, feature, collection (NC_*)
- Metafields: Buy Box, FAQs, Tech Specs
- Status: DRAFT (default for new)
- Inventory: DENY policy (no oversell unless preorder)

### Coffee-Specific Rules
If vendor = "Escarpment Coffee Roasters" and type = "Fresh Coffee":
- Add seasonality metafield
- Special tagging rules apply

### MAP Pricing Rules
- Follow vendor-specific MAP agreements
- Use compare_at_price for MSRP
- Track sale windows carefully

### Reference Files
- Business rules: /home/pranav/espressobot/frontend/server/prompts/idc-business-rules.md
- Tool guide: /home/pranav/espressobot/frontend/server/tool-docs/TOOL_USAGE_GUIDE.md`;
}

/**
 * Workflow patterns section - included for complex operations
 */
function buildWorkflowSection() {
  return `
## Complex Workflow Patterns

### Bulk Operations (50+ items)
1. Check cache for existing data
2. Use parallel_executors with proper batching
3. For 100+ items, consider SWE agent for optimization

### Migration Workflows
1. Use task_planner for coordination
2. Validate data before migration
3. Implement rollback strategy
4. Track progress with task updates

### Autonomy Levels
System pre-analyzes intent (global.currentIntentAnalysis):
- **High** (default): Execute immediately
- **Medium**: Confirm risky ops (50+ items)
- **Low**: Confirm all write operations`;
}

/**
 * Build unified orchestrator prompt based on task complexity
 */
export function buildUnifiedOrchestratorPrompt(contextualMessage, orchestratorContext, userProfile = null) {
  // Always include core prompt
  let prompt = buildCorePrompt(userProfile);
  
  // Analyze complexity
  const complexity = analyzeTaskComplexity(contextualMessage, orchestratorContext);
  
  // Add sections based on analysis
  if (complexity.needsAgentDetails) {
    prompt += buildAgentSection();
  }
  
  if (complexity.needsBusinessRules) {
    prompt += buildBusinessRulesSection();
  }
  
  if (complexity.needsWorkflowPatterns || complexity.needsBulkHandling) {
    prompt += buildWorkflowSection();
  }
  
  // Log decision
  const sections = [];
  if (complexity.needsAgentDetails) sections.push('agents');
  if (complexity.needsBusinessRules) sections.push('rules');
  if (complexity.needsWorkflowPatterns || complexity.needsBulkHandling) sections.push('workflows');
  
  console.log(`[Orchestrator] Prompt sections: core${sections.length ? ' + ' + sections.join(' + ') : ' only'} (score: ${complexity.complexityScore})`);
  
  return prompt;
}

/**
 * Export for backward compatibility
 */
export const buildTieredOrchestratorPrompt = buildUnifiedOrchestratorPrompt;