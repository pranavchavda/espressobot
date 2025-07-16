/**
 * Context Feedback Loop
 * 
 * Monitors successful operations and continuously improves context selection
 * by tracking what context was actually useful vs what was fetched.
 */

import { memoryOperations } from '../memory/memory-operations-local.js';
import { learnFromOperation } from './adaptive-context-builder.js';
import { learnFromContextUsage } from '../agents/context-analyzer-mini.js';
import { Agent, run } from '@openai/agents';
import { z } from 'zod';

class ContextFeedbackLoop {
  constructor() {
    this.operationTracker = new Map();
    this.contextUsageStats = new Map();
    this.improvementThreshold = 0.7; // 70% confidence threshold
  }

  /**
   * Start tracking an operation
   */
  startOperation(operationId, task, context) {
    this.operationTracker.set(operationId, {
      task,
      startTime: Date.now(),
      initialContext: this.extractContextSummary(context),
      contextKeys: Object.keys(context.fetchedContext || {}),
      tokenCount: context.tokenCount || 0,
      toolUsage: [],
      errors: [],
      status: 'in_progress'
    });
    
    console.log(`[FeedbackLoop] Started tracking operation ${operationId}`);
  }

  /**
   * Track tool usage during operation
   */
  trackToolUsage(operationId, toolName, success, context = null) {
    const operation = this.operationTracker.get(operationId);
    if (!operation) return;

    operation.toolUsage.push({
      tool: toolName,
      success,
      timestamp: Date.now(),
      contextUsed: context ? Object.keys(context) : []
    });
  }

  /**
   * Track errors during operation
   */
  trackError(operationId, error, context = null) {
    const operation = this.operationTracker.get(operationId);
    if (!operation) return;

    operation.errors.push({
      error: error.message || error,
      timestamp: Date.now(),
      contextMissing: context?.missingInfo || []
    });
  }

  /**
   * Complete operation tracking and analyze results
   */
  async completeOperation(operationId, success, result = null) {
    const operation = this.operationTracker.get(operationId);
    if (!operation) return;

    operation.endTime = Date.now();
    operation.duration = operation.endTime - operation.startTime;
    operation.status = success ? 'completed' : 'failed';
    operation.result = result;

    console.log(`[FeedbackLoop] Operation ${operationId} completed in ${operation.duration}ms`);

    // Analyze the operation
    const analysis = await this.analyzeOperation(operation);
    
    // Store insights
    await this.storeOperationInsights(operation, analysis);
    
    // Update context usage statistics
    this.updateUsageStats(operation, analysis);
    
    // Clean up tracker
    this.operationTracker.delete(operationId);
    
    return analysis;
  }

  /**
   * Analyze what context was actually useful
   */
  async analyzeOperation(operation) {
    const analyzer = new Agent({
      name: 'OperationAnalyzer',
      model: 'gpt-4.1-mini',
      instructions: `Analyze this completed operation to determine which context was actually useful.
      
Consider:
- Which context keys were referenced in tool calls
- What errors occurred due to missing context
- Which context was fetched but never used
- Overall efficiency of the operation`,
      
      outputType: z.object({
        usefulContext: z.array(z.string()).describe('Context keys that were actually used'),
        unusedContext: z.array(z.string()).describe('Context keys that were fetched but not used'),
        missingContext: z.array(z.string()).describe('Context that would have helped but was missing'),
        efficiency: z.number().min(0).max(1).describe('Overall context efficiency score'),
        recommendations: z.array(z.string()).describe('Recommendations for future operations')
      })
    });

    try {
      const prompt = `Analyze this completed operation:
      
Task: ${operation.task}
Context Keys Used: ${operation.contextKeys.join(', ')}
Tool Calls Made: ${operation.toolUsage.length}
Errors: ${operation.errors.length}
Duration: ${operation.duration}ms
Success: ${operation.status === 'completed'}

Tool Usage Details:
${operation.toolUsage.map(t => `- ${t.tool}: ${t.params}`).join('\n')}

${operation.errors.length > 0 ? `Errors:\n${operation.errors.join('\n')}` : ''}

Determine which context was useful, what was unused, and what was missing.`;

      const result = await run(analyzer, prompt, { maxTurns: 1 });

      return result.finalOutput || {
        usefulContext: [],
        unusedContext: operation.contextKeys,
        missingContext: [],
        efficiency: 0.5,
        recommendations: []
      };
    } catch (error) {
      console.error('[FeedbackLoop] Analysis failed:', error);
      return null;
    }
  }

  /**
   * Store insights from the operation
   */
  async storeOperationInsights(operation, analysis) {
    if (!analysis) return;

    try {
      // Store efficiency pattern
      await memoryOperations.add(
        `Context efficiency: ${operation.task.substring(0, 50)} - ${Math.round(analysis.efficiency * 100)}%`,
        'system_feedback',
        {
          type: 'context_efficiency',
          task: operation.task,
          usefulContext: analysis.usefulContext,
          unusedContext: analysis.unusedContext,
          missingContext: analysis.missingContext,
          efficiency: analysis.efficiency,
          duration: operation.duration,
          timestamp: new Date().toISOString()
        }
      );

      // Store recommendations
      if (analysis.recommendations.length > 0) {
        await memoryOperations.add(
          `Context recommendations for: ${operation.task.substring(0, 50)}`,
          'system_feedback',
          {
            type: 'context_recommendations',
            task: operation.task,
            recommendations: analysis.recommendations,
            basedOn: {
              toolUsage: operation.toolUsage.length,
              errors: operation.errors.length,
              efficiency: analysis.efficiency
            }
          }
        );
      }

      console.log('[FeedbackLoop] Stored operation insights');
    } catch (error) {
      console.error('[FeedbackLoop] Failed to store insights:', error);
    }
  }

  /**
   * Update usage statistics for context keys
   */
  updateUsageStats(operation, analysis) {
    if (!analysis) return;

    // Update useful context stats
    analysis.usefulContext.forEach(key => {
      const stats = this.contextUsageStats.get(key) || { useful: 0, unused: 0 };
      stats.useful++;
      this.contextUsageStats.set(key, stats);
    });

    // Update unused context stats
    analysis.unusedContext.forEach(key => {
      const stats = this.contextUsageStats.get(key) || { useful: 0, unused: 0 };
      stats.unused++;
      this.contextUsageStats.set(key, stats);
    });

    // Periodically prune low-value context
    if (Math.random() < 0.1) { // 10% chance
      this.pruneIneffectiveContext();
    }
  }

  /**
   * Prune context keys that are frequently unused
   */
  async pruneIneffectiveContext() {
    console.log('[FeedbackLoop] Evaluating context effectiveness...');
    
    const recommendations = [];
    
    for (const [key, stats] of this.contextUsageStats.entries()) {
      const total = stats.useful + stats.unused;
      if (total < 10) continue; // Need enough data
      
      const usefulness = stats.useful / total;
      
      if (usefulness < 0.2) { // Less than 20% useful
        recommendations.push({
          key,
          usefulness,
          recommendation: 'Consider removing this context key'
        });
      } else if (usefulness > 0.8) { // More than 80% useful
        recommendations.push({
          key,
          usefulness,
          recommendation: 'High-value context - prioritize in core context'
        });
      }
    }

    if (recommendations.length > 0) {
      await memoryOperations.add(
        'Context effectiveness evaluation',
        'system_feedback',
        {
          type: 'context_evaluation',
          recommendations,
          timestamp: new Date().toISOString()
        }
      );
      
      console.log(`[FeedbackLoop] Generated ${recommendations.length} context recommendations`);
    }

    // Clear old stats to prevent memory bloat
    if (this.contextUsageStats.size > 1000) {
      this.contextUsageStats.clear();
    }
  }

  /**
   * Get recommendations for a new task based on past feedback
   */
  async getRecommendations(task) {
    try {
      // Search for similar task feedback
      const feedback = await memoryOperations.search(
        `Context efficiency: ${task}`,
        'system_feedback',
        5
      );

      const recommendations = await memoryOperations.search(
        `Context recommendations for: ${task}`,
        'system_feedback',
        3
      );

      const insights = {
        averageEfficiency: 0,
        commonUsefulContext: new Set(),
        commonUnusedContext: new Set(),
        allRecommendations: []
      };

      // Aggregate feedback
      if (feedback.length > 0) {
        let totalEfficiency = 0;
        feedback.forEach(f => {
          if (f.metadata?.efficiency) {
            totalEfficiency += f.metadata.efficiency;
          }
          if (f.metadata?.usefulContext) {
            f.metadata.usefulContext.forEach(c => insights.commonUsefulContext.add(c));
          }
          if (f.metadata?.unusedContext) {
            f.metadata.unusedContext.forEach(c => insights.commonUnusedContext.add(c));
          }
        });
        insights.averageEfficiency = totalEfficiency / feedback.length;
      }

      // Collect recommendations
      recommendations.forEach(r => {
        if (r.metadata?.recommendations) {
          insights.allRecommendations.push(...r.metadata.recommendations);
        }
      });

      console.log('[FeedbackLoop] Found insights from', feedback.length, 'similar operations');
      
      return {
        hasInsights: feedback.length > 0,
        efficiency: insights.averageEfficiency,
        prioritizeContext: Array.from(insights.commonUsefulContext),
        avoidContext: Array.from(insights.commonUnusedContext),
        recommendations: insights.allRecommendations
      };
    } catch (error) {
      console.error('[FeedbackLoop] Failed to get recommendations:', error);
      return {
        hasInsights: false,
        efficiency: 0.5,
        prioritizeContext: [],
        avoidContext: [],
        recommendations: []
      };
    }
  }

  /**
   * Extract summary of context for tracking
   */
  extractContextSummary(context) {
    return {
      tokenCount: context.tokenCount || 0,
      hasExtractedData: !!context.extractedData,
      fetchedContextKeys: Object.keys(context.fetchedContext || {}),
      hasLearnedPatterns: !!context.learnedPatterns,
      adaptiveFeatures: {
        truncated: context.truncated || false,
        enhanced: !!context.enhancements
      }
    };
  }

  /**
   * Generate periodic improvement report
   */
  async generateImprovementReport() {
    const report = {
      timestamp: new Date().toISOString(),
      activeOperations: this.operationTracker.size,
      contextStats: {},
      topRecommendations: []
    };

    // Analyze context usage stats
    let totalUseful = 0;
    let totalUnused = 0;
    
    for (const [key, stats] of this.contextUsageStats.entries()) {
      totalUseful += stats.useful;
      totalUnused += stats.unused;
      
      const usefulness = stats.useful / (stats.useful + stats.unused);
      report.contextStats[key] = {
        usefulness: Math.round(usefulness * 100),
        totalUses: stats.useful + stats.unused
      };
    }

    report.overallEfficiency = totalUseful / (totalUseful + totalUnused);

    // Get recent recommendations
    try {
      const recentRecs = await memoryOperations.search(
        'Context recommendations',
        'system_feedback',
        10
      );
      
      report.topRecommendations = recentRecs
        .flatMap(r => r.metadata?.recommendations || [])
        .slice(0, 5);
    } catch (error) {
      console.error('[FeedbackLoop] Failed to get recommendations for report:', error);
    }

    return report;
  }
}

// Export singleton instance
export const feedbackLoop = new ContextFeedbackLoop();