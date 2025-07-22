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

// REMOVED: filterFetchedContext function - replaced by context synthesis approach
// The ContextRelevanceFilter agent and filtering logic have been superseded by 
// the synthesizeContextFragment function which creates cohesive context instead of filtering

/**
 * Synthesize fetched context into a cohesive, task-specific context fragment
 */
export async function synthesizeContextFragment(task, fetchedContext, options = {}) {
  const { maxTokens = 8000, conversationId = null } = options;
  
  console.log('[ContextAnalyzer] Synthesizing context into task-specific fragment...');
  
  // Create a context synthesis agent
  const contextPreamble = buildAgentContextPreamble({
    agentRole: 'context synthesis expert',
    conversationId
  });
  
  const synthesisAgent = new Agent({
    name: 'ContextSynthesizer',
    model: 'gpt-4.1-mini',
    instructions: `${contextPreamble}

You are a context synthesis expert. Your job is to take multiple context sources and synthesize them into a single, cohesive context fragment that contains ONLY the information needed to complete the specific task.

Your synthesized context should:
1. Combine relevant information from all sources
2. Remove duplicates and redundancies  
3. Be concise but complete
4. Focus specifically on the task at hand
5. Organize information logically
6. Use clear, actionable language

Write the synthesized context as if you're briefing someone on exactly what they need to know to complete this task. Include:
- Key facts and background
- Relevant procedures or workflows
- Important constraints or requirements
- User preferences that affect execution

Exclude:
- Irrelevant background information
- Overly detailed explanations
- Information not directly related to the task`,
    
    outputType: z.object({
      synthesizedContext: z.string().describe('The synthesized context fragment containing only task-relevant information'),
      includedSources: z.array(z.string()).describe('Which context sources were included in the synthesis'),
      excludedSources: z.array(z.string()).describe('Which context sources were excluded and why'),
      keyInsights: z.array(z.string()).describe('Key insights or requirements extracted from the context')
    })
  });
  
  try {
    // Prepare all context content for synthesis
    let allContextContent = '';
    const sourcesList = [];
    
    for (const [key, value] of Object.entries(fetchedContext)) {
      if (value.results && value.results.length > 0) {
        sourcesList.push(key);
        allContextContent += `\n\n=== ${key.toUpperCase()} ===\n`;
        
        // Include all relevant content from this source
        for (const result of value.results) {
          const content = result.memory || result.content || '';
          if (content.trim()) {
            allContextContent += content.substring(0, 1000) + '\n';
          }
        }
      }
    }
    
    if (!allContextContent.trim()) {
      console.log('[ContextAnalyzer] No context content to synthesize');
      return {
        success: false,
        synthesizedFragment: null,
        includedSources: [],
        excludedSources: sourcesList
      };
    }
    
    const prompt = `Task to complete: ${task}

Available context from multiple sources:
${allContextContent}

Synthesize this context into a single, focused fragment that contains exactly what's needed to complete the task. Be concise but comprehensive.`;
    
    const result = await run(synthesisAgent, prompt, { maxTurns: 1 });
    
    if (result.finalOutput) {
      const synthesis = result.finalOutput;
      console.log(`[ContextAnalyzer] Context synthesized - included ${synthesis.includedSources.length} sources, excluded ${synthesis.excludedSources.length}`);
      console.log(`[ContextAnalyzer] Key insights: ${synthesis.keyInsights.join(', ')}`);
      
      return {
        success: true,
        synthesizedFragment: synthesis.synthesizedContext,
        includedSources: synthesis.includedSources,
        excludedSources: synthesis.excludedSources,
        keyInsights: synthesis.keyInsights,
        tokenCount: synthesis.synthesizedContext.length / 4 // Rough token estimate
      };
    }
    
    // Fallback
    console.log('[ContextAnalyzer] Synthesis failed, no output generated');
    return {
      success: false,
      synthesizedFragment: null,
      includedSources: [],
      excludedSources: sourcesList
    };
    
  } catch (error) {
    console.error('[ContextAnalyzer] Error synthesizing context:', error.message);
    return {
      success: false,
      synthesizedFragment: null,
      error: error.message
    };
  }
}

/**
 * Full context analysis pipeline - run early filtering and rewriting
 */
export async function runContextAnalyzer(message, options = {}) {
  const { userId, conversationId, rawContext, tieredPromptSections } = options;
  
  try {
    console.log('[ContextAnalyzer] Running full context analysis pipeline...');
    
    // Step 1: Analyze what context we need for this task
    const analysis = await analyzeContextNeeds(message, null, {
      conversationId,
      maxTokens: 12000
    });
    
    if (!analysis.success) {
      return { success: false, error: 'Context analysis failed' };
    }
    
    // Step 2: Fetch suggested context
    const fetchResult = await fetchSuggestedContext(analysis.analysis.suggestedContext, userId);
    const fetchedContext = fetchResult.context; // Extract the actual context data
    
    // Step 3: Add tiered prompt sections to the context for synthesis
    if (tieredPromptSections && typeof tieredPromptSections === 'object') {
      for (const [sectionName, sectionContent] of Object.entries(tieredPromptSections)) {
        if (sectionContent && sectionContent.trim()) {
          fetchedContext[`Tiered Prompt - ${sectionName}`] = {
            priority: 'helpful',
            source: 'rules',
            results: [{ content: sectionContent }],
            tokenCount: sectionContent.length / 4
          };
        }
      }
    }
    
    // Step 4: Synthesize the fetched context into a cohesive fragment
    const synthesisResult = await synthesizeContextFragment(message, fetchedContext, {
      maxTokens: 8000,
      conversationId
    });
    
    if (!synthesisResult.success) {
      return { success: false, error: 'Context synthesis failed' };
    }
    
    console.log(`[ContextAnalyzer] Pipeline complete - synthesized context from ${synthesisResult.includedSources.length} sources`);
    
    return {
      success: true,
      context: {
        synthesizedFragment: synthesisResult.synthesizedFragment,
        includedSources: synthesisResult.includedSources,
        keyInsights: synthesisResult.keyInsights,
        // Legacy format for compatibility
        memories: [],
        promptFragments: [{
          category: 'synthesized',
          content: synthesisResult.synthesizedFragment,
          priority: 'high',
          score: 1.0
        }]
      }
    };
    
  } catch (error) {
    console.error('[ContextAnalyzer] Pipeline failed:', error.message);
    return { success: false, error: error.message };
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