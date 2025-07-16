/**
 * Progress Tracker - 4.1-nano Agent
 * 
 * Lightweight agent for extracting progress from agent outputs and managing checkpoints.
 * Uses GPT-4.1-nano for maximum efficiency on simple extraction tasks.
 */

import { Agent, run } from '@openai/agents';
import { z } from 'zod';
import fs from 'fs/promises';
import path from 'path';
import { dirname } from 'path';
import { fileURLToPath } from 'url';
import { buildAgentContextPreamble } from '../utils/agent-context-builder.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const checkpointsDir = path.resolve(__dirname, '../data/checkpoints');

// Ensure checkpoints directory exists
fs.mkdir(checkpointsDir, { recursive: true }).catch(() => {});

/**
 * Create a progress extraction agent
 */
export function createProgressExtractor(conversationId = null) {
  const contextPreamble = buildAgentContextPreamble({
    agentRole: 'progress tracking specialist',
    conversationId
  });
  
  return new Agent({
    name: 'ProgressExtractor',
    model: 'gpt-4.1-nano',
    instructions: `${contextPreamble}

Extract task completion progress from agent output.
    
Look for:
- Completed items (success messages, "done", "created", "updated")
- Failed items (errors, "failed", "skipped")
- Items currently being processed
- Any numerical progress indicators

Be generous in detecting success - if something was attempted, assume it worked unless there's a clear error.`,
    
    outputType: z.object({
      completed: z.array(z.object({
        item: z.string(),
        result: z.string().nullable().default(null)
      })).describe('Successfully completed items'),
      
      failed: z.array(z.object({
        item: z.string(),
        error: z.string().nullable().default(null)
      })).describe('Failed items with errors'),
      
      inProgress: z.string().nullable().default(null).describe('Currently processing item'),
      
      stats: z.object({
        total: z.number().nullable().default(null),
        completed: z.number(),
        failed: z.number()
      }).describe('Progress statistics')
    })
  });
}

/**
 * Extract progress from agent output
 */
export async function extractProgress(agentOutput, expectedItems = null, conversationId = null) {
  try {
    const extractor = createProgressExtractor(conversationId);
    
    let prompt = `Agent output:\n${agentOutput}`;
    if (expectedItems) {
      prompt += `\n\nExpected items: ${JSON.stringify(expectedItems)}`;
    }
    
    console.log('[ProgressTracker] Extracting progress...');
    const result = await run(extractor, prompt, { maxTurns: 1 });
    
    if (result.finalOutput) {
      console.log('[ProgressTracker] Extraction complete:', result.finalOutput.stats);
      return {
        success: true,
        progress: result.finalOutput
      };
    }
    
    return {
      success: false,
      error: 'No extraction output'
    };
    
  } catch (error) {
    console.error('[ProgressTracker] Extraction failed:', error.message);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Save checkpoint for a conversation
 */
export async function saveCheckpoint(conversationId, checkpoint) {
  try {
    const checkpointPath = path.join(checkpointsDir, `${conversationId}-checkpoint.json`);
    
    // Load existing checkpoints
    let checkpoints = [];
    try {
      const existing = await fs.readFile(checkpointPath, 'utf-8');
      checkpoints = JSON.parse(existing);
    } catch (e) {
      // File doesn't exist yet
    }
    
    // Add new checkpoint
    checkpoints.push({
      ...checkpoint,
      timestamp: new Date().toISOString(),
      index: checkpoints.length
    });
    
    // Keep only last 10 checkpoints
    if (checkpoints.length > 10) {
      checkpoints = checkpoints.slice(-10);
    }
    
    await fs.writeFile(checkpointPath, JSON.stringify(checkpoints, null, 2));
    console.log(`[ProgressTracker] Saved checkpoint ${checkpoints.length} for conversation ${conversationId}`);
    
    return { success: true, checkpointIndex: checkpoints.length - 1 };
  } catch (error) {
    console.error('[ProgressTracker] Failed to save checkpoint:', error);
    return { success: false, error: error.message };
  }
}

/**
 * Load latest checkpoint for a conversation
 */
export async function loadLatestCheckpoint(conversationId) {
  try {
    const checkpointPath = path.join(checkpointsDir, `${conversationId}-checkpoint.json`);
    const data = await fs.readFile(checkpointPath, 'utf-8');
    const checkpoints = JSON.parse(data);
    
    if (checkpoints.length === 0) {
      return null;
    }
    
    return checkpoints[checkpoints.length - 1];
  } catch (error) {
    // No checkpoint file
    return null;
  }
}

/**
 * Create a progress summary from multiple checkpoints
 */
export async function summarizeProgress(conversationId) {
  try {
    const checkpointPath = path.join(checkpointsDir, `${conversationId}-checkpoint.json`);
    const data = await fs.readFile(checkpointPath, 'utf-8');
    const checkpoints = JSON.parse(data);
    
    if (checkpoints.length === 0) {
      return { totalCompleted: 0, totalFailed: 0, lastUpdate: null };
    }
    
    // Aggregate all completed/failed items
    const allCompleted = new Set();
    const allFailed = new Set();
    
    for (const checkpoint of checkpoints) {
      if (checkpoint.completed) {
        checkpoint.completed.forEach(item => allCompleted.add(item.item));
      }
      if (checkpoint.failed) {
        checkpoint.failed.forEach(item => allFailed.add(item.item));
      }
    }
    
    // Remove items that were retried successfully
    allFailed.forEach(item => {
      if (allCompleted.has(item)) {
        allFailed.delete(item);
      }
    });
    
    return {
      totalCompleted: allCompleted.size,
      totalFailed: allFailed.size,
      completedItems: Array.from(allCompleted),
      failedItems: Array.from(allFailed),
      lastUpdate: checkpoints[checkpoints.length - 1].timestamp
    };
  } catch (error) {
    return { totalCompleted: 0, totalFailed: 0, lastUpdate: null };
  }
}

/**
 * Clean up old checkpoints
 */
export async function cleanupOldCheckpoints(daysToKeep = 7) {
  try {
    const files = await fs.readdir(checkpointsDir);
    const now = Date.now();
    const maxAge = daysToKeep * 24 * 60 * 60 * 1000;
    
    for (const file of files) {
      if (!file.endsWith('-checkpoint.json')) continue;
      
      const filePath = path.join(checkpointsDir, file);
      const stats = await fs.stat(filePath);
      
      if (now - stats.mtime.getTime() > maxAge) {
        await fs.unlink(filePath);
        console.log(`[ProgressTracker] Cleaned up old checkpoint: ${file}`);
      }
    }
  } catch (error) {
    console.error('[ProgressTracker] Cleanup failed:', error);
  }
}