/**
 * Context Store Abstraction Layer
 * 
 * This provides a consistent interface for context storage and retrieval,
 * making it easy to swap between pattern matching, semantic search, or hybrid approaches.
 */

export class ContextStore {
  constructor(options = {}) {
    this.type = options.type || 'pattern'; // 'pattern', 'semantic', 'hybrid'
    this.patternMatcher = null;
    this.semanticIndex = null;
    this.metrics = options.enableMetrics || false;
  }

  /**
   * Initialize the store based on type
   */
  async initialize() {
    switch (this.type) {
      case 'pattern':
        // Current implementation - no init needed
        break;
        
      case 'semantic':
        // Future: Initialize vector store
        // this.semanticIndex = await this.initializeVectorStore();
        break;
        
      case 'hybrid':
        // Future: Initialize both
        // this.semanticIndex = await this.initializeVectorStore();
        break;
    }
  }

  /**
   * Get relevant contexts for a message
   */
  async getContexts(message, options = {}) {
    const startTime = Date.now();
    let contexts = [];

    try {
      switch (this.type) {
        case 'pattern':
          contexts = await this.patternBasedSearch(message, options);
          break;
          
        case 'semantic':
          contexts = await this.semanticSearch(message, options);
          break;
          
        case 'hybrid':
          contexts = await this.hybridSearch(message, options);
          break;
      }

      // Track metrics if enabled
      if (this.metrics) {
        await this.trackUsage(message, contexts, Date.now() - startTime);
      }

      return contexts;
    } catch (error) {
      console.error('[ContextStore] Error getting contexts:', error);
      // Fallback to pattern matching
      return this.patternBasedSearch(message, options);
    }
  }

  /**
   * Pattern-based search (current implementation)
   */
  async patternBasedSearch(message, options) {
    const { analyzeContextNeeds } = await import('./context-manager.js');
    return analyzeContextNeeds(message);
  }

  /**
   * Semantic search (future implementation)
   */
  async semanticSearch(message, options) {
    // Placeholder for semantic search
    // Will implement when we move to vector-based approach
    console.log('[ContextStore] Semantic search not yet implemented, falling back to patterns');
    return this.patternBasedSearch(message, options);
  }

  /**
   * Hybrid search combining both approaches
   */
  async hybridSearch(message, options) {
    // Start with pattern matching for speed
    const patternResults = await this.patternBasedSearch(message, options);
    
    // If we get good matches, return them
    if (patternResults.length >= 3) {
      return patternResults;
    }
    
    // Otherwise, enhance with semantic search
    const semanticResults = await this.semanticSearch(message, options);
    
    // Combine and deduplicate
    const combined = new Set([...patternResults, ...semanticResults]);
    return Array.from(combined);
  }

  /**
   * Track usage for learning and optimization
   */
  async trackUsage(message, contexts, responseTime) {
    if (!this.metrics) return;
    
    try {
      const { memoryOperations } = await import('../memory/memory-operations-local.js');
      await memoryOperations.add(
        JSON.stringify({
          type: 'context_usage',
          message: message.substring(0, 100),
          contexts: contexts,
          responseTime: responseTime,
          timestamp: new Date().toISOString()
        }),
        'system_metrics'
      );
    } catch (error) {
      // Silently fail metrics tracking
      console.debug('[ContextStore] Could not track metrics:', error.message);
    }
  }

  /**
   * Add a new context mapping (for learning)
   */
  async addContextMapping(pattern, contexts, confidence = 1.0) {
    // This will be useful for:
    // 1. Learning from successful interactions
    // 2. Building semantic embeddings
    // 3. Improving pattern matching
    
    // For now, just log it
    console.log(`[ContextStore] New mapping: "${pattern}" -> ${contexts.join(', ')} (confidence: ${confidence})`);
  }

  /**
   * Get statistics about context usage
   */
  async getStats() {
    if (!this.metrics) {
      return { message: 'Metrics not enabled' };
    }
    
    // Future: Query metrics from storage
    return {
      totalQueries: 0,
      averageResponseTime: 0,
      mostUsedContexts: [],
      patternHitRate: 0
    };
  }
}

// Singleton instance
let contextStore = null;

/**
 * Get or create the context store instance
 */
export function getContextStore(options = {}) {
  if (!contextStore) {
    contextStore = new ContextStore(options);
  }
  return contextStore;
}

/**
 * Reset the context store (useful for testing)
 */
export function resetContextStore() {
  contextStore = null;
}