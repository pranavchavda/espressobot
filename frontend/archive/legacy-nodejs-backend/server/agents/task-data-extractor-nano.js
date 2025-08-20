/**
 * Task Data Extractor - 4.1-nano Agent
 * 
 * Lightweight agent for extracting structured data from e-commerce tasks.
 * Uses GPT-4.1-nano for efficient, low-cost extraction.
 */

import { Agent, run } from '@openai/agents';
import { z } from 'zod';
import { buildAgentContextPreamble } from '../utils/agent-context-builder.js';

/**
 * Create a task data extractor agent
 */
export function createTaskDataExtractor(conversationId = null) {
  const contextPreamble = buildAgentContextPreamble({
    agentRole: 'data extraction specialist',
    conversationId
  });
  
  return new Agent({
    name: 'TaskDataExtractor',
    model: 'gpt-4.1-nano',
    instructions: `${contextPreamble}

You are a data extraction specialist for e-commerce operations.
    
Extract structured data from user requests. Be flexible with the schema.
Common e-commerce entities: products, customers, orders, pricing, inventory, reports, campaigns, discounts, shipping, taxes, reviews

Identify:
1. What entities are involved (products, customers, etc.)
2. What action needs to be taken (create, update, delete, analyze, report)
3. Any specific attributes or filters mentioned
4. Whether this is a single item, bulk operation, or query

Be inclusive - extract all potentially relevant information.`,
    
    outputType: z.object({
      entities: z.array(z.object({
        type: z.string().describe('Entity type (product, customer, order, etc.)'),
        identifier: z.string().nullable().default(null).describe('SKU, ID, email, or other identifier')
      })).describe('All entities mentioned in the task'),
      
      action: z.string().describe('Primary action (create, update, delete, analyze, report, send, etc.)'),
      
      scope: z.enum(['single', 'bulk', 'query']).describe('Single item, multiple items, or a search/filter operation'),
      
      rawItems: z.array(z.string()).nullable().default(null).describe('If user listed specific items, include them here'),
      
      metadata: z.object({
        hasPricing: z.boolean().describe('Does this involve prices or costs?'),
        hasInventory: z.boolean().describe('Does this involve stock or inventory?'),
        hasTimeframe: z.boolean().describe('Is there a time period mentioned?'),
        urgent: z.boolean().describe('Does this seem time-sensitive?')
      }).describe('Quick flags for context building')
    })
  });
}

/**
 * Extract task data from a user message
 */
export async function extractTaskData(message, options = {}) {
  const { includeContext = '', conversationId = null } = options;
  
  try {
    const extractor = createTaskDataExtractor(conversationId);
    
    // Build the extraction prompt
    const prompt = includeContext 
      ? `Context: ${includeContext}\n\nTask: ${message}`
      : message;
    
    console.log('[TaskDataExtractor] Extracting data from message...');
    const result = await run(extractor, prompt, { maxTurns: 1 });
    
    if (result.finalOutput) {
      console.log('[TaskDataExtractor] Extraction complete:', {
        entityCount: result.finalOutput.entities.length,
        action: result.finalOutput.action,
        scope: result.finalOutput.scope
      });
      
      return {
        success: true,
        data: result.finalOutput
      };
    }
    
    return {
      success: false,
      error: 'No output from extractor'
    };
    
  } catch (error) {
    console.error('[TaskDataExtractor] Extraction failed:', error.message);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Extract bulk items from various formats
 */
export async function extractBulkItems(message) {
  const extractor = new Agent({
    name: 'BulkItemExtractor',
    model: 'gpt-4.1-nano',
    instructions: `Extract individual items from bulk operation requests.
    
Handle various formats:
- Lists (comma-separated, newline-separated, numbered)
- Natural language ("all coffee products", "items with low stock")
- Mixed formats

Return specific items when listed, or descriptive filters when general.`,
    
    outputType: z.object({
      items: z.array(z.union([
        z.string(),
        z.object({
          identifier: z.string(),
          attributes: z.record(z.any()).optional()
        })
      ])),
      isSpecificList: z.boolean().describe('True if user provided specific items, false if general criteria'),
      totalCount: z.number().nullable().default(null).describe('Estimated or exact count if mentioned')
    })
  });
  
  try {
    const result = await run(extractor, message, { maxTurns: 1 });
    return result.finalOutput || { items: [], isSpecificList: false };
  } catch (error) {
    console.error('[BulkItemExtractor] Failed:', error.message);
    return { items: [], isSpecificList: false };
  }
}

/**
 * Utility to merge extracted data with existing context
 */
export function mergeExtractedData(extracted, existingContext = {}) {
  return {
    ...existingContext,
    entities: [
      ...(existingContext.entities || []),
      ...extracted.entities
    ],
    action: extracted.action || existingContext.action,
    scope: extracted.scope || existingContext.scope,
    metadata: {
      ...existingContext.metadata,
      ...extracted.metadata
    }
  };
}