/**
 * Parallel Executor Agent
 * 
 * Optimized for light-bulk operations (10-50 items) with controlled parallelism.
 * Uses GPT-4.1-mini for speed/cost optimization with built-in safety features.
 */

import { Agent, tool } from '@openai/agents';
import { z } from 'zod';
import { setTracingDisabled } from '@openai/agents-core';
import { bashTool } from '../tools/bash-tool.js';

// Disable tracing to prevent 7MB span output errors
setTracingDisabled(true);
import { createSpawnMCPAgentTool } from '../tools/spawn-mcp-agent-tool.js';

// Concurrency control
const CONCURRENCY_LIMIT = 5; // Max concurrent operations
const BATCH_SIZE_THRESHOLD = 50; // Recommend SWE agent above this
const OPTIMAL_BATCH_SIZE = 10; // Optimal items per agent instance

/**
 * Create a parallel executor agent instance
 */
export async function createParallelExecutorAgent(instanceId, items, operation, options = {}) {
  const {
    dryRun = false,
    retryLimit = 2,
    throttleMs = 1000, // Delay between operations
    customContext = ''
  } = options;

  console.log(`[ParallelExecutor-${instanceId}] Creating agent for ${items.length} items`);

  const instructions = `You are Parallel Executor Instance ${instanceId}, optimized for light-bulk operations.

## YOUR TASK
Process ${items.length} items in parallel for the following operation:
${operation}

## EXECUTION PARAMETERS
- Concurrency Limit: ${CONCURRENCY_LIMIT} operations at once
- Throttle Delay: ${throttleMs}ms between operations
- Retry Limit: ${retryLimit} attempts per item
- Mode: ${dryRun ? 'DRY RUN - Simulate only' : 'LIVE - Execute operations'}

## ITEMS TO PROCESS
${JSON.stringify(items, null, 2)}

${customContext ? `## ADDITIONAL CONTEXT\n${customContext}\n` : ''}

## EXECUTION STRATEGY
1. Use spawn_mcp_agent tool for each item - DO NOT use bash with fake shopify commands
2. Process items in batches of ${CONCURRENCY_LIMIT}
3. Track success/failure for each item
4. Retry failed items up to ${retryLimit} times
5. Report progress after each batch
6. Return aggregated results

## CRITICAL TOOL USAGE
- ALWAYS use spawn_mcp_agent for Shopify operations (search_products, get_product, update_pricing)
- DO NOT use bash with "shopify" CLI commands - they don't exist
- DO NOT write Python scripts with placeholder URLs
- Use sleep tool for throttling between operations

## SAFETY RULES
- NEVER exceed ${CONCURRENCY_LIMIT} concurrent operations
- Wait ${throttleMs}ms between operations to avoid rate limits
- If an operation fails, log the error and continue with others
- In dry run mode, simulate operations without executing

## EXPECTED OUTPUT FORMAT
Return a JSON object with:
{
  "instanceId": "${instanceId}",
  "totalItems": ${items.length},
  "successful": <count>,
  "failed": <count>,
  "results": [
    {"item": <item>, "status": "success", "result": <result>},
    {"item": <item>, "status": "failed", "error": <error>, "retries": <count>}
  ],
  "executionTime": <seconds>
}

Start processing immediately. Emit progress updates using the report_progress tool.`;

  // Create progress reporting tool
  const progressTool = tool({
    name: 'report_progress',
    description: 'Report execution progress',
    parameters: z.object({
      processed: z.number().describe('Number of items processed so far'),
      successful: z.number().describe('Number of successful operations'),
      failed: z.number().describe('Number of failed operations'),
      currentBatch: z.number().nullable().describe('Current batch number (null if not applicable)'),
      message: z.string().nullable().describe('Progress message (null if not applicable)')
    }),
    execute: async ({ processed, successful, failed, currentBatch, message }) => {
      const progress = {
        instanceId,
        processed,
        successful,
        failed,
        remaining: items.length - processed,
        percentage: Math.round((processed / items.length) * 100)
      };

      if (currentBatch) progress.currentBatch = currentBatch;
      if (message) progress.message = message;

      console.log(`[ParallelExecutor-${instanceId}] Progress:`, progress);

      // Emit SSE event if available
      if (global.currentSseEmitter) {
        global.currentSseEmitter('parallel_executor_progress', progress);
      }

      return `Progress reported: ${processed}/${items.length} items (${progress.percentage}%)`;
    }
  });

  // Create sleep tool for throttling
  const sleepTool = tool({
    name: 'sleep',
    description: 'Sleep for specified milliseconds to implement throttling',
    parameters: z.object({
      ms: z.number().describe('Milliseconds to sleep')
    }),
    execute: async ({ ms }) => {
      await new Promise(resolve => setTimeout(resolve, ms));
      return `Slept for ${ms}ms`;
    }
  });

  // Create spawn_mcp_agent tool for this executor
  const spawnMCPAgentTool = await createSpawnMCPAgentTool();

  return new Agent({
    name: `ParallelExecutor_${instanceId}`,
    instructions,
    tools: [spawnMCPAgentTool, progressTool, sleepTool, bashTool],
    model: 'gpt-4.1-mini' // Optimized for speed/cost
  });
}

// Tool definition removed - now defined in espressobot1.js
// to avoid Zod validation issues with optional fields

/**
 * Helper function to validate parallel execution is appropriate
 */
export function validateParallelExecution(items, operation) {
  const validations = {
    appropriate: true,
    warnings: [],
    recommendations: []
  };

  // Check item count
  if (items.length < 5) {
    validations.warnings.push('Less than 5 items - consider sequential execution');
    validations.appropriate = false;
  }

  if (items.length > BATCH_SIZE_THRESHOLD) {
    validations.warnings.push(`${items.length} items exceeds recommended threshold of ${BATCH_SIZE_THRESHOLD}`);
    validations.recommendations.push('Use SWE agent for better performance');
    validations.appropriate = false;
  }

  // Check operation type
  const bulkKeywords = ['update', 'add', 'remove', 'delete', 'modify', 'set', 'change'];
  const hasBuilkKeyword = bulkKeywords.some(keyword => 
    operation.toLowerCase().includes(keyword)
  );

  if (!hasBuilkKeyword) {
    validations.warnings.push('Operation may not be suitable for parallel execution');
  }

  // Check for complex operations
  const complexKeywords = ['if', 'when', 'unless', 'except', 'conditional'];
  const hasComplexLogic = complexKeywords.some(keyword => 
    operation.toLowerCase().includes(keyword)
  );

  if (hasComplexLogic) {
    validations.warnings.push('Complex conditional logic detected');
    validations.recommendations.push('Consider SWE agent for custom script');
  }

  return validations;
}