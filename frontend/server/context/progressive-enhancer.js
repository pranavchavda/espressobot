/**
 * Progressive Context Enhancer
 * 
 * Monitors agent execution and progressively adds context when agents struggle
 * or encounter errors, learning from these patterns for future operations.
 */

import { enhanceContext, checkContextSufficiency } from './adaptive-context-builder.js';
import { memoryOperations } from '../memory/memory-operations-local.js';
import { Agent, run } from '@openai/agents';
import { z } from 'zod';

/**
 * Monitor agent execution and detect when context enhancement is needed
 */
export class ProgressiveEnhancer {
  constructor() {
    this.attemptHistory = new Map(); // Track attempts per conversation
    this.errorPatterns = new Map();  // Learn from error patterns
  }

  /**
   * Analyze agent output for signs of struggle
   */
  async analyzeAgentOutput(output, task, conversationId) {
    const analyzer = new Agent({
      name: 'OutputAnalyzer',
      model: 'gpt-4.1-nano',
      instructions: `Analyze agent output for signs of missing context or confusion.
      
Look for:
- Uncertainty phrases ("I'm not sure", "I can't find", "unclear")
- Missing information ("need more details", "not enough context")
- Tool failures or errors
- Requests for clarification
- Circular reasoning or repetition`,
      
      outputType: z.object({
        needsEnhancement: z.boolean(),
        missingContext: z.array(z.string()).nullable().default(null),
        confidence: z.number().min(0).max(1),
        errorType: z.enum(['missing_info', 'tool_error', 'confusion', 'none']).nullable().default('none')
      })
    });

    try {
      const prompt = `Analyze this agent output for signs of missing context or confusion:

Task: ${task}
Agent Output: ${typeof output === 'string' ? output : JSON.stringify(output)}

Look for uncertainty, missing information, tool failures, or requests for clarification.`;

      const result = await run(analyzer, prompt, { maxTurns: 1 });

      return result.finalOutput || { needsEnhancement: false, confidence: 0.5 };
    } catch (error) {
      console.error('[ProgressiveEnhancer] Analysis failed:', error);
      return { needsEnhancement: false, confidence: 0.5 };
    }
  }

  /**
   * Suggest context enhancements based on analysis
   */
  async suggestEnhancements(analysis, task, currentContext) {
    if (!analysis.needsEnhancement || !analysis.missingContext) {
      return [];
    }

    const suggester = new Agent({
      name: 'EnhancementSuggester',
      model: 'gpt-4.1-mini',
      instructions: `Based on what context is missing, suggest specific queries to find that information.
      
Be specific and actionable with search queries.
Focus on the most critical missing pieces.
Consider business rules, historical patterns, and related entities.`,
      
      outputType: z.object({
        queries: z.array(z.object({
          query: z.string(),
          reason: z.string(),
          priority: z.enum(['critical', 'helpful', 'optional'])
        })),
        rationale: z.string()
      })
    });

    try {
      const prompt = `Missing context: ${JSON.stringify(analysis.missingContext)}
Task: ${task}
Current context keys: ${Object.keys(currentContext.fetchedContext || {}).join(', ')}

Generate specific queries to find the missing information.`;
      
      const result = await run(suggester, prompt, { maxTurns: 1 });

      if (result.finalOutput) {
        return result.finalOutput.queries.map(q => q.query);
      }
      return [];
    } catch (error) {
      console.error('[ProgressiveEnhancer] Suggestion failed:', error);
      return [];
    }
  }

  /**
   * Track attempt and decide if enhancement is needed
   */
  async trackAttempt(conversationId, task, output, error = null) {
    const key = `${conversationId}-${task.substring(0, 50)}`;
    
    if (!this.attemptHistory.has(key)) {
      this.attemptHistory.set(key, {
        attempts: 0,
        errors: [],
        enhancements: []
      });
    }

    const history = this.attemptHistory.get(key);
    history.attempts++;

    if (error) {
      history.errors.push({
        error: error.message || error,
        timestamp: new Date().toISOString()
      });
    }

    // Analyze if we need enhancement after 2 attempts or on specific errors
    if (history.attempts >= 2 || (error && error.includes('context'))) {
      const analysis = await this.analyzeAgentOutput(output || error, task, conversationId);
      
      if (analysis.needsEnhancement) {
        console.log('[ProgressiveEnhancer] Enhancement needed after', history.attempts, 'attempts');
        return {
          needsEnhancement: true,
          analysis,
          attemptCount: history.attempts
        };
      }
    }

    return {
      needsEnhancement: false,
      attemptCount: history.attempts
    };
  }

  /**
   * Apply progressive enhancement to context
   */
  async enhance(task, currentContext, analysis) {
    console.log('[ProgressiveEnhancer] Applying progressive enhancement');
    
    // Get enhancement suggestions
    const queries = await this.suggestEnhancements(analysis, task, currentContext);
    
    if (queries.length === 0) {
      console.log('[ProgressiveEnhancer] No enhancement queries suggested');
      return currentContext;
    }

    // Apply enhancements
    const enhanced = await enhanceContext(currentContext, queries);
    
    // Store this enhancement pattern for learning
    await this.storeEnhancementPattern(task, analysis, queries, enhanced);
    
    return enhanced;
  }

  /**
   * Store enhancement patterns for future learning
   */
  async storeEnhancementPattern(task, analysis, queries, enhancedContext) {
    try {
      const pattern = {
        taskPattern: task.substring(0, 100),
        errorType: analysis.errorType,
        missingContext: analysis.missingContext,
        enhancementQueries: queries,
        tokenIncrease: enhancedContext.tokenCount - (enhancedContext.tokenCount - queries.length * 500), // Rough estimate
        timestamp: new Date().toISOString()
      };

      await memoryOperations.add(
        `Enhancement pattern: ${analysis.errorType} - ${task.substring(0, 50)}`,
        'system_learning',
        {
          type: 'enhancement_pattern',
          pattern,
          effectiveness: 0.7 // Will be updated based on outcome
        }
      );

      console.log('[ProgressiveEnhancer] Stored enhancement pattern');
    } catch (error) {
      console.error('[ProgressiveEnhancer] Failed to store pattern:', error);
    }
  }

  /**
   * Check if we have learned patterns for this type of task
   */
  async checkLearnedPatterns(task, errorType) {
    try {
      const patterns = await memoryOperations.search(
        `Enhancement pattern: ${errorType}`,
        'system_learning',
        5
      );

      if (patterns.length > 0) {
        console.log('[ProgressiveEnhancer] Found', patterns.length, 'learned enhancement patterns');
        
        // Extract the most relevant queries from patterns
        const relevantQueries = new Set();
        patterns.forEach(p => {
          if (p.metadata?.pattern?.enhancementQueries) {
            p.metadata.pattern.enhancementQueries.forEach(q => relevantQueries.add(q));
          }
        });

        return Array.from(relevantQueries).slice(0, 3); // Top 3 queries
      }
    } catch (error) {
      console.error('[ProgressiveEnhancer] Pattern check failed:', error);
    }

    return [];
  }

  /**
   * Update pattern effectiveness based on outcome
   */
  async updatePatternEffectiveness(task, outcome) {
    // This would update the stored patterns based on whether the enhancement helped
    // Implementation depends on tracking mechanism
    console.log('[ProgressiveEnhancer] Pattern effectiveness update:', outcome.success ? 'helpful' : 'not helpful');
  }

  /**
   * Clear old attempt history to prevent memory bloat
   */
  clearOldHistory(maxAge = 3600000) { // 1 hour default
    const now = Date.now();
    for (const [key, history] of this.attemptHistory.entries()) {
      const lastAttempt = history.errors[history.errors.length - 1]?.timestamp;
      if (lastAttempt && now - new Date(lastAttempt).getTime() > maxAge) {
        this.attemptHistory.delete(key);
      }
    }
  }
}

// Singleton instance
export const progressiveEnhancer = new ProgressiveEnhancer();