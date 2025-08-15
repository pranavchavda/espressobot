import { tool } from '@openai/agents';
import { z } from 'zod';

/**
 * Analyze user intent to determine appropriate autonomy level
 */
export const analyzeIntent = (message) => {
  const lowerMessage = message.toLowerCase();
  
  // Check for specific values/parameters - expanded to catch more patterns
  const specificValuePatterns = [
    /\b(sku[:\s]*\w+|id[:\s]*\d+)\b/i,
    /\$[\d.,]+/,
    /\bprice[:\s]*[\d.,]+/i,
    /\b\d+\.?\d*\s*%/,  // Percentages
    /"[^"]+"|'[^']+'/,  // Quoted strings
    /\bto\s+\$?[\d.,]+/i,  // "to $899" pattern
    /\b(barista|oracle|breville|delonghi|rocket|ecm|eureka)\b/i  // Product names
  ];
  const hasSpecificValues = specificValuePatterns.some(pattern => pattern.test(message));
  
  // Check for lists of items
  const hasItemList = /\b(and|,)\s*(sku|id|product|item)\b/i.test(message) || 
                      message.split(',').length > 2;
  
  // Check for imperative commands (including polite forms)
  const imperativePatterns = [
    /^(update|set|change|modify|create|add|remove|delete|publish|unpublish|activate|deactivate|fix|make)\b/i,
    /\b(please\s+)?(update|set|change|modify|create|add|remove|delete|fix|make)\b/i,
    /\b(can|could|would|will)\s+you\s+(please\s+)?(update|set|change|modify|create|add|remove|delete|make|fix)\b/i,
    /\b(need|want)\s+(to|you\s+to)\s+(update|set|change|modify|create|add|remove|delete|make|fix)\b/i
  ];
  const isImperative = imperativePatterns.some(pattern => pattern.test(message));
  
  // Check for questions that are actually commands (have specific values)
  const questionAsCommand = /^(can|could|would|will|is it possible|are you able)\s+/i.test(message) && hasSpecificValues;
  
  // Check for high-risk operations
  const highRiskPatterns = [
    /\b(all|every|entire|whole)\s+(products?|items?|skus?|variants?)\b/i,
    /\bdelete\s+(all|everything|products?|items?)\b/i,
    /\b(increase|decrease|change).*\b(all|every).*price/i,
    /\bprice.*\b[5-9]\d%|\d{3,}%/i, // Price changes > 50%
  ];
  const isHighRisk = highRiskPatterns.some(pattern => pattern.test(message));
  
  // Check for exploratory/question patterns
  const questionPatterns = [
    /^(can|could|would|should)\s+(you|i)\b/i,
    /\?$/,
    /\b(what|how|when|where|why)\b.*\?/i
  ];
  const isQuestion = questionPatterns.some(pattern => pattern.test(message));
  
  // Determine autonomy level
  if (isHighRisk && !hasSpecificValues) {
    return {
      level: 'medium',
      reason: 'High-risk operation detected - will confirm before executing',
      confidence: 0.9
    };
  }
  
  // Questions with specific values are commands!
  if (questionAsCommand) {
    return {
      level: 'high',
      reason: 'Question contains specific values - treating as command and executing immediately',
      confidence: 0.95
    };
  }
  
  if (hasSpecificValues && isImperative) {
    return {
      level: 'high',
      reason: 'Clear command with specific values - executing immediately',
      confidence: 0.95
    };
  }
  
  if (hasSpecificValues && !isQuestion) {
    return {
      level: 'high',
      reason: 'Specific values provided - executing immediately',
      confidence: 0.9
    };
  }
  
  if (hasItemList && !isQuestion) {
    return {
      level: 'high',
      reason: 'Specific list of items provided - executing immediately',
      confidence: 0.9
    };
  }
  
  if (isImperative && !isQuestion) {
    return {
      level: 'high',
      reason: 'Direct command detected - executing immediately',
      confidence: 0.85
    };
  }
  
  if (isQuestion && !hasSpecificValues && !isImperative) {
    return {
      level: 'low',
      reason: 'Question without specific values - will confirm approach',
      confidence: 0.8
    };
  }
  
  // Default to high autonomy for clear instructions
  return {
    level: 'high',
    reason: 'Instructions appear clear - proceeding with execution',
    confidence: 0.7
  };
};

/**
 * Intent analysis tool for agents
 */
export const intentAnalysisTool = tool({
  name: 'analyze_user_intent',
  description: 'Analyze user message to determine appropriate autonomy level for task execution',
  parameters: z.object({
    message: z.string().describe('The user message to analyze')
  }),
  execute: async ({ message }) => {
    const analysis = analyzeIntent(message);
    
    console.log(`[Intent Analysis] Message: "${message.substring(0, 100)}..."`);
    console.log(`[Intent Analysis] Autonomy: ${analysis.level} (${analysis.confidence * 100}% confidence)`);
    console.log(`[Intent Analysis] Reason: ${analysis.reason}`);
    
    return analysis;
  }
});

/**
 * Check if operation affects many items
 */
export const checkOperationScale = (items) => {
  const itemCount = Array.isArray(items) ? items.length : 1;
  
  if (itemCount >= 50) {
    return {
      scale: 'large',
      requiresConfirmation: true,
      message: `This operation will affect ${itemCount} items`
    };
  } else if (itemCount >= 10) {
    return {
      scale: 'medium',
      requiresConfirmation: false,
      message: `This operation will affect ${itemCount} items`
    };
  } else {
    return {
      scale: 'small',
      requiresConfirmation: false,
      message: `This operation will affect ${itemCount} item${itemCount > 1 ? 's' : ''}`
    };
  }
};