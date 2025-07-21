/**
 * Dynamic Context Analyzer - 4.1-mini Agent
 * 
 * Intelligently determines what context would be helpful for any e-commerce task.
 * Adapts to the specific needs of each operation without predefined templates.
 */

import { Agent, run } from '../utils/model-with-retry.js';
import { z } from 'zod';
import { memoryOperations } from '../memory/memory-operations-local.js';
import { buildAgentContextPreamble } from '../utils/agent-context-builder.js';

/**
 * Create a context analyzer agent
 */
export function createContextAnalyzer(conversationId = null) {
  const contextPreamble = buildAgentContextPreamble({
    agentRole: 'context analysis expert',
    conversationId
  });
  
  return new Agent({
    name: 'ContextAnalyzer',
    model: 'gpt-4.1-mini',
    instructions: `${contextPreamble}

You are a context analysis expert for e-commerce operations.

Analyze tasks and determine what context would be helpful to complete them successfully.
Don't use predefined categories - think specifically about what information would help.

Consider:
1. What historical data might be relevant?
2. What business rules or constraints apply?
3. What related entities should be loaded?
4. What recent changes or patterns matter?
5. How much context is actually needed (avoid overloading)?

Be specific with search queries that could find this context.
Prioritize context that directly impacts the task outcome.`,
    
    outputType: z.object({
      suggestedContext: z.array(z.object({
        description: z.string().describe('What context to look for'),
        priority: z.enum(['critical', 'helpful', 'optional']).describe('How important is this context'),
        searchQuery: z.string().describe('Specific query to find this context'),
        source: z.enum(['memory', 'rules', 'products', 'history', 'external']).describe('Where to look for this context')
      })).describe('Ordered list of context suggestions'),
      
      estimatedTokensNeeded: z.number().describe('Rough estimate of tokens for all context'),
      
      reasoning: z.string().describe('Brief explanation of why this context matters'),
      
      skipSuggestions: z.array(z.string()).nullable().default(null).describe('What context to explicitly avoid loading')
    })
  });
}

/**
 * Analyze what context a task needs
 */
export async function analyzeContextNeeds(task, extractedData = null, options = {}) {
  const { conversationId = null, recentErrors = [] } = options;
  
  try {
    const analyzer = createContextAnalyzer(conversationId);
    
    // Build analysis prompt with available information
    let prompt = `Task: ${task}`;
    
    if (extractedData) {
      prompt += `\n\nExtracted entities: ${JSON.stringify(extractedData.entities, null, 2)}`;
      prompt += `\nAction: ${extractedData.action}`;
      prompt += `\nScope: ${extractedData.scope}`;
    }
    
    if (recentErrors.length > 0) {
      prompt += `\n\nRecent errors to consider: ${recentErrors.join('; ')}`;
    }
    
    console.log('[ContextAnalyzer] Analyzing context needs...');
    const result = await run(analyzer, prompt, { maxTurns: 1 });
    
    if (result.finalOutput) {
      // Filter suggestions based on feedback insights if available
      let filteredSuggestions = [...result.finalOutput.suggestedContext];
      
      // Always add a direct semantic memory search based on the original task
      // This ensures we don't miss relevant memories by being too specific
      console.log(`[ContextAnalyzer] Checking for direct memory search in ${filteredSuggestions.length} suggestions`);
      const hasDirectMemorySearch = filteredSuggestions.some(s => 
        s.source === 'memory' && 
        s.priority === 'critical' &&
        (s.searchQuery === task || s.searchQuery.includes(task.substring(0, 50)))
      );
      
      console.log(`[ContextAnalyzer] Has direct memory search: ${hasDirectMemorySearch}`);
      
      if (!hasDirectMemorySearch) {
        console.log(`[ContextAnalyzer] Adding direct semantic memory search for: "${task}"`);
        filteredSuggestions.unshift({
          description: `Relevant past experiences and knowledge`,
          source: 'memory',
          priority: 'critical',
          searchQuery: task,
          type: 'semantic_memory'
        });
      }
      
      // Also add a direct search for prompt fragments/rules
      const hasDirectRulesSearch = filteredSuggestions.some(s => 
        s.source === 'rules' && 
        s.priority === 'critical' &&
        (s.searchQuery === task || s.searchQuery.includes(task.substring(0, 50)))
      );
      
      if (!hasDirectRulesSearch) {
        filteredSuggestions.unshift({
          description: `Relevant guidelines and documentation`,
          source: 'rules',
          priority: 'critical',
          searchQuery: task,
          type: 'semantic_rules'
        });
        console.log(`[ContextAnalyzer] Added direct semantic search for prompt fragments`);
      }
      
      if (options.feedbackInsights) {
        const { prioritizeContext, avoidContext } = options.feedbackInsights;
        
        // Boost priority of historically useful context
        filteredSuggestions = filteredSuggestions.map(s => {
          if (prioritizeContext.some(pc => s.description.includes(pc))) {
            return { ...s, priority: 'critical' };
          }
          if (avoidContext.some(ac => s.description.includes(ac))) {
            return { ...s, priority: 'optional' };
          }
          return s;
        });
        
        console.log('[ContextAnalyzer] Applied feedback insights to suggestions');
      }
      
      console.log('[ContextAnalyzer] Analysis complete:', {
        suggestions: filteredSuggestions.length,
        criticalCount: filteredSuggestions.filter(s => s.priority === 'critical').length,
        estimatedTokens: result.finalOutput.estimatedTokensNeeded
      });
      
      return {
        success: true,
        analysis: {
          ...result.finalOutput,
          suggestedContext: filteredSuggestions
        }
      };
    }
    
    return {
      success: false,
      error: 'No analysis output'
    };
    
  } catch (error) {
    console.error('[ContextAnalyzer] Analysis failed:', error.message);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Search for and fetch suggested context
 */
export async function fetchSuggestedContext(suggestions, userId = null) {
  const fetchedContext = {};
  let totalTokens = 0;
  
  for (const suggestion of suggestions) {
    console.log(`[ContextAnalyzer] Fetching ${suggestion.priority} context: ${suggestion.description}`);
    
    try {
      let results = [];
      
      switch (suggestion.source) {
        case 'memory':
          if (userId) {
            // Format userId properly for memory search (handle both string and number)
            const userIdStr = String(userId);
            const memoryUserId = userIdStr.startsWith('user_') ? userIdStr : `user_${userIdStr}`;
            results = await memoryOperations.search(
              suggestion.searchQuery,
              memoryUserId,
              suggestion.priority === 'critical' ? 5 : 3
            );
          }
          break;
          
        case 'rules':
          // Search system prompt fragments
          results = await memoryOperations.searchSystemPromptFragments(
            suggestion.searchQuery,
            suggestion.priority === 'critical' ? 10 : 5
          );
          break;
          
        case 'history':
          // This would search conversation history if implemented
          console.log('[ContextAnalyzer] History search not yet implemented');
          break;
          
        case 'products':
          // This would search product catalog if needed
          console.log('[ContextAnalyzer] Product search would happen here');
          break;
          
        case 'external':
          // External API calls if needed
          console.log('[ContextAnalyzer] External search would happen here');
          break;
      }
      
      if (results.length > 0) {
        fetchedContext[suggestion.description] = {
          priority: suggestion.priority,
          source: suggestion.source,
          results: results,
          tokenCount: JSON.stringify(results).length / 4 // Rough estimate
        };
        totalTokens += fetchedContext[suggestion.description].tokenCount;
      }
      
    } catch (error) {
      console.error(`[ContextAnalyzer] Failed to fetch context: ${suggestion.description}`, error.message);
    }
    
    // Stop fetching if we're getting too large
    if (totalTokens > 20000 && suggestion.priority !== 'critical') {
      console.log('[ContextAnalyzer] Stopping context fetch - approaching token limit');
      break;
    }
  }
  
  return {
    context: fetchedContext,
    totalTokens
  };
}

/**
 * Filter fetched context for relevance to the actual task
 */
export async function filterFetchedContext(task, fetchedContext, options = {}) {
  const { maxTokens = 15000, conversationId = null } = options;
  
  console.log('[ContextAnalyzer] Filtering fetched context for relevance...');
  
  // Create a relevance filter agent
  const contextPreamble = buildAgentContextPreamble({
    agentRole: 'context relevance filter',
    conversationId
  });
  
  const filterAgent = new Agent({
    name: 'ContextRelevanceFilter',
    model: 'gpt-4.1-mini',
    instructions: `${contextPreamble}

You are a context relevance filter. Your job is to evaluate whether fetched context items are actually relevant to the task at hand.

For each context item, determine:
1. Is it directly relevant to completing the task?
2. Does it provide necessary background or constraints?
3. Is it just keyword-matched but not contextually relevant?

Be strict - only mark items as relevant if they genuinely help with the task.
For example, product documentation is NOT relevant to email searches.`,
    
    outputType: z.object({
      filteredContext: z.array(z.object({
        key: z.string().describe('Context key/description'),
        relevant: z.boolean().describe('Is this context relevant to the task?'),
        reason: z.string().describe('Why is this relevant or irrelevant?'),
        priority: z.enum(['critical', 'helpful', 'optional']).describe('Adjusted priority if relevant')
      })),
      totalRelevant: z.number().describe('Number of relevant context items'),
      explanation: z.string().describe('Brief explanation of filtering decisions')
    })
  });
  
  try {
    // Prepare context items for evaluation
    const contextItems = [];
    for (const [key, value] of Object.entries(fetchedContext)) {
      if (value.results && value.results.length > 0) {
        // Sample first few results for evaluation
        const samples = value.results.slice(0, 2).map(r => 
          (r.memory || r.content || '').substring(0, 200)
        );
        contextItems.push({
          key,
          source: value.source,
          priority: value.priority,
          sampleContent: samples.join(' | '),
          resultCount: value.results.length
        });
      }
    }
    
    if (contextItems.length === 0) {
      console.log('[ContextAnalyzer] No context items to filter');
      return fetchedContext;
    }
    
    const prompt = `Task: ${task}

Context items to evaluate:
${JSON.stringify(contextItems, null, 2)}

Determine which context items are actually relevant to completing this task.`;
    
    const result = await run(filterAgent, prompt, { maxTurns: 1 });
    
    if (result.finalOutput) {
      console.log(`[ContextAnalyzer] Filtering results: ${result.finalOutput.totalRelevant}/${contextItems.length} items relevant`);
      console.log(`[ContextAnalyzer] Explanation: ${result.finalOutput.explanation}`);
      
      // Apply filtering decisions
      const filteredContext = {};
      let currentTokens = 0;
      
      for (const decision of result.finalOutput.filteredContext) {
        if (decision.relevant && fetchedContext[decision.key]) {
          const contextItem = fetchedContext[decision.key];
          
          // Check token limit
          if (currentTokens + contextItem.tokenCount > maxTokens) {
            console.log(`[ContextAnalyzer] Skipping ${decision.key} - would exceed token limit`);
            continue;
          }
          
          // Add to filtered context with adjusted priority
          filteredContext[decision.key] = {
            ...contextItem,
            priority: decision.priority,
            filterReason: decision.reason
          };
          currentTokens += contextItem.tokenCount;
          
          console.log(`[ContextAnalyzer] Including: ${decision.key} (${decision.priority}) - ${decision.reason}`);
        } else {
          console.log(`[ContextAnalyzer] Excluding: ${decision.key} - ${decision.reason}`);
        }
      }
      
      return filteredContext;
    }
    
    // Fallback to original context if filtering fails
    console.log('[ContextAnalyzer] Filtering failed, returning original context');
    return fetchedContext;
    
  } catch (error) {
    console.error('[ContextAnalyzer] Error filtering context:', error.message);
    // Return original context on error
    return fetchedContext;
  }
}

/**
 * Learn from successful context usage
 */
export async function learnFromContextUsage(task, usedContext, outcome) {
  if (!outcome || !outcome.success) return;
  
  // Validate inputs
  if (typeof task !== 'string') {
    console.warn('[ContextAnalyzer] learnFromContextUsage called with non-string task:', typeof task);
    return;
  }
  
  if (!usedContext || typeof usedContext !== 'object') {
    console.warn('[ContextAnalyzer] learnFromContextUsage called with invalid context:', typeof usedContext);
    return;
  }
  
  // Extract what context was actually helpful
  const learningAgent = new Agent({
    name: 'ContextLearning',
    model: 'gpt-4.1-nano',
    instructions: 'Analyze what context was helpful for completing this task successfully.',
    outputType: z.object({
      pattern: z.string().describe('General pattern of this task type'),
      helpfulContext: z.array(z.string()).describe('Context that was actually used'),
      unnecessaryContext: z.array(z.string()).describe('Context that was fetched but not needed')
    })
  });
  
  try {
    // Build a proper prompt string for the agent
    const contextKeys = usedContext ? Object.keys(usedContext) : [];
    const prompt = `Task: ${task}
Context Used: ${contextKeys.length > 0 ? contextKeys.join(', ') : 'None'}
Outcome: ${outcome.summary || 'Successful completion'}`;
    
    const analysis = await run(learningAgent, prompt, { maxTurns: 1 });
    
    if (analysis.finalOutput) {
      // Store this learning
      await memoryOperations.add(
        `Context pattern: For tasks like "${analysis.finalOutput.pattern}", helpful context includes: ${analysis.finalOutput.helpfulContext.join(', ')}`,
        'system_learning',
        {
          type: 'context_pattern',
          pattern: analysis.finalOutput.pattern,
          helpful: analysis.finalOutput.helpfulContext,
          unnecessary: analysis.finalOutput.unnecessaryContext,
          timestamp: new Date().toISOString()
        }
      );
      
      console.log('[ContextAnalyzer] Stored context learning pattern');
    }
  } catch (error) {
    console.error('[ContextAnalyzer] Failed to store learning:', error.message);
  }
}