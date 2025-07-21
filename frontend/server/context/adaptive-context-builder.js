/**
 * Adaptive Context Builder
 * 
 * Builds context dynamically based on task analysis rather than predefined templates.
 * Uses nano/mini agents to intelligently select and fetch only needed context.
 */

import { extractTaskData } from '../agents/task-data-extractor-nano.js';
import { analyzeContextNeeds, fetchSuggestedContext, filterFetchedContext } from '../agents/context-analyzer-mini.js';
import { memoryOperations } from '../memory/memory-operations-local.js';
import { buildCompressedContext } from '../agents/conversation-summarizer-agent.js';

/**
 * Build adaptive context for any e-commerce task
 */
export async function buildAdaptiveContext(options) {
  const {
    task,
    conversationId,
    userId,
    userMessage,
    conversationHistory = [],
    includeExtractedData = true,
    maxTokens = 30000
  } = options;
  
  console.log('[AdaptiveContext] Building context for task:', task.substring(0, 100) + '...');
  
  // Get feedback loop recommendations
  const { feedbackLoop } = await import('./feedback-loop.js');
  const recommendations = await feedbackLoop.getRecommendations(task);
  
  if (recommendations.hasInsights) {
    console.log('[AdaptiveContext] Using feedback insights - avg efficiency:', 
      Math.round(recommendations.efficiency * 100) + '%');
  }
  
  // Start with minimal base context
  const context = {
    task,
    conversationId,
    userId,
    timestamp: new Date().toISOString(),
    tokenCount: 0,
    feedbackInsights: recommendations
  };
  
  try {
    // Step 1: Extract structured data from the task
    let extractedData = null;
    if (includeExtractedData) {
      console.log('[AdaptiveContext] Extracting task data...');
      const extraction = await extractTaskData(task, { includeContext: userMessage });
      
      if (extraction.success) {
        extractedData = extraction.data;
        context.extractedData = extractedData;
        context.tokenCount += JSON.stringify(extractedData).length / 4;
        
        console.log('[AdaptiveContext] Extracted:', {
          entities: extractedData.entities.length,
          action: extractedData.action,
          scope: extractedData.scope
        });
      }
    }
    
    // Step 2: Check for learned patterns
    console.log('[AdaptiveContext] Searching for learned patterns...');
    const learnedPatterns = await memoryOperations.search(
      `Context pattern: ${task}`,
      'system_learning',
      3
    );
    
    if (learnedPatterns.length > 0) {
      context.learnedPatterns = learnedPatterns.map(p => ({
        pattern: p.metadata?.pattern,
        helpful: p.metadata?.helpful || [],
        score: p.score
      }));
      console.log(`[AdaptiveContext] Found ${learnedPatterns.length} learned patterns`);
    }
    
    // Step 3: Analyze what context is needed
    console.log('[AdaptiveContext] Analyzing context needs...');
    const contextAnalysis = await analyzeContextNeeds(task, extractedData, {
      conversationId,
      recentErrors: context.recentErrors || [],
      feedbackInsights: recommendations
    });
    
    if (contextAnalysis.success) {
      context.contextAnalysis = contextAnalysis.analysis;
      
      // Step 4: Fetch suggested context (respecting token limits)
      console.log('[AdaptiveContext] Fetching suggested context...');
      const fetched = await fetchSuggestedContext(
        contextAnalysis.analysis.suggestedContext,
        userId
      );
      
      // Step 4.5: Filter fetched context for relevance
      console.log('[AdaptiveContext] Filtering fetched context for relevance...');
      const filteredContext = await filterFetchedContext(task, fetched.context, {
        maxTokens: maxTokens - context.tokenCount,
        conversationId
      });
      
      // Recalculate total tokens after filtering
      let filteredTokens = 0;
      for (const value of Object.values(filteredContext)) {
        filteredTokens += value.tokenCount || 0;
      }
      
      // Add filtered context
      if (context.tokenCount + filteredTokens < maxTokens) {
        context.fetchedContext = filteredContext;
        context.tokenCount += filteredTokens;
      } else {
        // Only add critical context if over limit
        const criticalContext = {};
        for (const [key, value] of Object.entries(filteredContext)) {
          if (value.priority === 'critical') {
            criticalContext[key] = value;
            context.tokenCount += value.tokenCount;
          }
        }
        context.fetchedContext = criticalContext;
        context.truncated = true;
      }
    }
    
    // Step 5: Add recent conversation context (compressed)
    if (conversationHistory.length > 0) {
      console.log('[AdaptiveContext] Adding conversation history...');
      const compressed = await buildCompressedContext(conversationHistory, {
        maxRecentTurns: extractedData?.scope === 'bulk' ? 2 : 4
      });
      
      context.conversationSummary = compressed.finalSummary;
      context.recentMessages = compressed.recentMessages;
      context.tokenCount += JSON.stringify(compressed).length / 4;
    }
    
    // Step 6: Add any bulk operation data
    if (extractedData?.scope === 'bulk' && extractedData.rawItems) {
      context.bulkItems = extractedData.rawItems;
      context.bulkMetadata = {
        total: extractedData.rawItems.length,
        action: extractedData.action
      };
    }
    
    console.log('[AdaptiveContext] Context built:', {
      totalTokens: Math.round(context.tokenCount),
      hasExtractedData: !!context.extractedData,
      fetchedContextKeys: Object.keys(context.fetchedContext || {}).length,
      hasLearnedPatterns: !!context.learnedPatterns,
      truncated: context.truncated || false
    });
    
    // Extract memories and rules from fetchedContext for compatibility
    const extractedMemories = [];
    const extractedRules = [];
    const extractedPromptFragments = [];
    
    if (context.fetchedContext) {
      for (const [key, value] of Object.entries(context.fetchedContext)) {
        if (value.source === 'memory' && value.results) {
          // Add memories with their original structure
          extractedMemories.push(...value.results.map(result => ({
            content: result.memory || result.content || '',
            score: result.score || 0,
            metadata: result.metadata || {}
          })));
        } else if (value.source === 'rules' && value.results) {
          // Add rules/prompt fragments
          extractedPromptFragments.push(...value.results.map(result => ({
            content: result.memory || result.content || '',
            category: result.metadata?.category || 'general',
            priority: result.metadata?.priority || value.priority,
            score: result.score || 0
          })));
        }
      }
    }
    
    // Ensure compatibility with code expecting traditional context structure
    context.relevantMemories = extractedMemories.length > 0 ? extractedMemories : [];
    context.relevantRules = context.relevantRules || [];
    context.conversationHistory = context.conversationHistory || context.recentMessages || [];
    context.promptFragments = extractedPromptFragments.length > 0 ? extractedPromptFragments : [];
    
    // Log what was extracted
    if (extractedMemories.length > 0) {
      console.log(`[AdaptiveContext] Extracted ${extractedMemories.length} memories from fetchedContext`);
    }
    if (extractedPromptFragments.length > 0) {
      console.log(`[AdaptiveContext] Extracted ${extractedPromptFragments.length} prompt fragments from fetchedContext`);
    }
    
    return context;
    
  } catch (error) {
    console.error('[AdaptiveContext] Error building context:', error);
    // Return minimal context on error
    return {
      ...context,
      error: error.message,
      fallback: true,
      // Ensure compatibility fields
      relevantMemories: [],
      relevantRules: [],
      conversationHistory: [],
      promptFragments: []
    };
  }
}

/**
 * Progressive context enhancement - add more context if needed
 */
export async function enhanceContext(existingContext, additionalQueries) {
  console.log('[AdaptiveContext] Enhancing context with additional queries:', additionalQueries);
  
  const enhancements = {};
  let additionalTokens = 0;
  
  for (const query of additionalQueries) {
    try {
      // Search in memories
      const results = await memoryOperations.search(
        query,
        existingContext.userId,
        3
      );
      
      if (results.length > 0) {
        enhancements[query] = results;
        additionalTokens += JSON.stringify(results).length / 4;
      }
    } catch (error) {
      console.error(`[AdaptiveContext] Failed to fetch enhancement: ${query}`, error);
    }
  }
  
  return {
    ...existingContext,
    enhancements,
    tokenCount: existingContext.tokenCount + additionalTokens
  };
}

/**
 * Check if context is sufficient for the task
 */
export async function checkContextSufficiency(task, context) {
  // Use nano agent for quick sufficiency check
  const { Agent, run } = await import('@openai/agents');
  const { z } = await import('zod');
  
  const sufficiencyChecker = new Agent({
    name: 'ContextSufficiency',
    model: 'gpt-4.1-nano',
    instructions: 'Determine if the provided context contains enough information to complete the task.',
    outputType: z.object({
      sufficient: z.boolean(),
      missingInfo: z.array(z.string()).nullable().default(null),
      confidence: z.number().min(0).max(1)
    })
  });
  
  try {
    const result = await run(sufficiencyChecker, {
      task,
      availableContext: Object.keys(context.fetchedContext || {})
    }, { maxTurns: 1 });
    
    return result.finalOutput || { sufficient: true, confidence: 0.5 };
  } catch (error) {
    console.error('[AdaptiveContext] Sufficiency check failed:', error);
    return { sufficient: true, confidence: 0.5 }; // Default to proceeding
  }
}

/**
 * Learn from successful operations and store patterns
 */
export async function learnFromOperation(task, context, outcome) {
  if (!outcome.success) return;
  
  try {
    // Store the successful pattern
    const pattern = {
      task: task.substring(0, 200),
      contextKeys: Object.keys(context.fetchedContext || {}),
      action: context.extractedData?.action,
      scope: context.extractedData?.scope,
      tokenCount: context.tokenCount,
      timestamp: new Date().toISOString()
    };
    
    await memoryOperations.add(
      `Context pattern: ${pattern.task}`,
      'system_learning',
      {
        type: 'context_pattern',
        pattern: pattern,
        helpful: pattern.contextKeys,
        confidence: outcome.confidence || 0.8
      }
    );
    
    console.log('[AdaptiveContext] Stored successful context pattern');
  } catch (error) {
    console.error('[AdaptiveContext] Failed to store learning:', error);
  }
}