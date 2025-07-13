/**
 * Configuration for prompt fragment retrieval
 * Controls what appears in the "Relevant Documentation" section
 */

export const promptFragmentConfig = {
  // Similarity threshold for semantic search (0-1)
  // Higher = more strict matching, lower = more lenient
  similarityThreshold: 0.5, // Increased for more relevant matches now that agent filtering is fixed
  
  // Maximum number of fragments to retrieve
  limits: {
    core: 5,    // For core context (simple tasks)
    full: 10    // For full context (complex tasks)
  },
  
  // Categories to prioritize (in order)
  priorityCategories: [
    'critical',      // Always include critical rules
    'workflow',      // Workflow patterns
    'business_rule', // Business rules
    'tool_usage',    // Tool documentation
    'general'        // General guidance
  ],
  
  // Tags to boost relevance
  boostTags: [
    'frequently_used',
    'best_practice',
    'important'
  ],
  
  // Tags to filter out
  excludeTags: [
    'deprecated',
    'draft',
    'internal_only'
  ],
  
  // Agent-specific filtering
  agentTypeFilter: {
    orchestrator: ['orchestrator', 'all', 'general'],
    bash: ['bash', 'all', 'general'],
    swe: ['swe', 'all', 'development', 'general']
  }
};

/**
 * Filter and score prompt fragments based on configuration
 */
export function filterPromptFragments(fragments, options = {}) {
  const {
    agentType = 'orchestrator',
    taskKeywords = [],
    maxResults = promptFragmentConfig.limits.full
  } = options;
  
  console.log(`[FILTER] Starting with ${fragments.length} fragments`);
  console.log(`[FILTER] Task keywords: ${taskKeywords.join(', ')}`);
  
  // Filter by similarity threshold
  let filtered = fragments.filter(f => 
    f.score >= promptFragmentConfig.similarityThreshold
  );
  console.log(`[FILTER] After similarity threshold (${promptFragmentConfig.similarityThreshold}): ${filtered.length} fragments`);
  
  // Log scores for debugging
  if (fragments.length > 0) {
    const scores = fragments.map(f => f.score).sort((a, b) => b - a);
    console.log(`[FILTER] Score range: ${scores[0]?.toFixed(3)} to ${scores[scores.length-1]?.toFixed(3)}`);
  }
  
  // Filter by agent type
  const allowedTypes = promptFragmentConfig.agentTypeFilter[agentType] || ['general'];
  const beforeAgentFilter = filtered.length;
  filtered = filtered.filter(f => {
    const fragmentAgentType = f.agentType || 'general';
    return allowedTypes.includes(fragmentAgentType);
  });
  console.log(`[FILTER] After agent type filter (${agentType}): ${filtered.length} fragments (removed ${beforeAgentFilter - filtered.length})`);
  
  // Filter out excluded tags
  const beforeTagFilter = filtered.length;
  filtered = filtered.filter(f => {
    const tags = f.tags || [];
    return !tags.some(tag => promptFragmentConfig.excludeTags.includes(tag));
  });
  console.log(`[FILTER] After tag exclusion: ${filtered.length} fragments (removed ${beforeTagFilter - filtered.length})`);
  
  // Score and sort by relevance
  const scored = filtered.map(f => {
    let score = f.score;
    const boosts = [];
    
    // Boost by priority category
    const categoryIndex = promptFragmentConfig.priorityCategories.indexOf(f.category || 'general');
    if (categoryIndex !== -1) {
      const categoryBoost = (promptFragmentConfig.priorityCategories.length - categoryIndex) * 0.1;
      score += categoryBoost;
      boosts.push(`category:+${categoryBoost.toFixed(2)}`);
    }
    
    // Boost by tags
    const tags = f.tags || [];
    const boostCount = tags.filter(tag => promptFragmentConfig.boostTags.includes(tag)).length;
    if (boostCount > 0) {
      const tagBoost = boostCount * 0.05;
      score += tagBoost;
      boosts.push(`tags:+${tagBoost.toFixed(2)}`);
    }
    
    // Boost by task keyword matches
    const content = f.content.toLowerCase();
    const keywordMatches = taskKeywords.filter(kw => content.includes(kw.toLowerCase())).length;
    if (keywordMatches > 0) {
      const keywordBoost = keywordMatches * 0.1;
      score += keywordBoost;
      boosts.push(`keywords:+${keywordBoost.toFixed(2)}`);
    }
    
    return { ...f, adjustedScore: score, boosts: boosts.join(', ') };
  });
  
  // Sort by adjusted score and limit
  const result = scored
    .sort((a, b) => b.adjustedScore - a.adjustedScore)
    .slice(0, maxResults);
    
  console.log(`[FILTER] Final result: ${result.length} fragments`);
  
  return result;
}