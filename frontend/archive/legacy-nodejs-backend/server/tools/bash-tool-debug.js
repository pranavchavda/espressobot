import { tool } from '@openai/agents';
import { z } from 'zod';
import { executeBashCommand } from './bash-tool.js';

/**
 * Debug version of bash tool that logs all parameters
 */
export const bashToolDebug = tool({
  name: 'bash',
  description: 'Execute bash commands with detailed debugging',
  parameters: z.object({
    command: z.string().describe('The bash command to execute'),
    cwd: z.string().default('/tmp').describe('Working directory for command execution'),
    timeout: z.number().default(300000).describe('Timeout in milliseconds'),
  }),
  execute: async (params) => {
    console.log('[BASH DEBUG] Raw params:', JSON.stringify(params, null, 2));
    console.log('[BASH DEBUG] Params type:', typeof params);
    console.log('[BASH DEBUG] Params keys:', Object.keys(params));
    
    // Check each parameter
    console.log('[BASH DEBUG] command:', params.command, 'type:', typeof params.command);
    console.log('[BASH DEBUG] cwd:', params.cwd, 'type:', typeof params.cwd);
    console.log('[BASH DEBUG] timeout:', params.timeout, 'type:', typeof params.timeout);
    
    // Try to detect the error
    try {
      // Check if params is properly structured
      if (!params || typeof params !== 'object') {
        throw new Error('params is not an object');
      }
      
      if (!params.command) {
        throw new Error('command is missing');
      }
      
      // Get SSE emitter if available
      let sseEmitter = global.currentSseEmitter;
      
      console.log('[BASH DEBUG] Calling executeBashCommand...');
      const result = await executeBashCommand(params, sseEmitter);
      console.log('[BASH DEBUG] Result:', result);
      
      return result;
    } catch (error) {
      console.error('[BASH DEBUG] Error:', error);
      console.error('[BASH DEBUG] Error stack:', error.stack);
      throw error;
    }
  }
});

export default bashToolDebug;