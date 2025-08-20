/**
 * OpenAI Tracing Configuration
 * 
 * Controls OpenAI agents tracing for debugging and monitoring.
 * Tracing can be expensive due to token usage in logs.
 * 
 * Environment Variables:
 * - OPENAI_TRACING_ENABLED: 'true' to enable tracing (default: false)
 * - OPENAI_TRACING_AGENTS: Comma-separated list of agents to trace (default: all)
 * - OPENAI_TRACING_MAX_OUTPUT: Max output size in KB (default: 500)
 */

import { setTracingDisabled } from '@openai/agents-core';

// Configuration
const config = {
  // Global tracing toggle
  enabled: process.env.OPENAI_TRACING_ENABLED === 'true',
  
  // Specific agents to trace (empty = all agents)
  agentsToTrace: process.env.OPENAI_TRACING_AGENTS 
    ? process.env.OPENAI_TRACING_AGENTS.split(',').map(a => a.trim())
    : [],
  
  // Max output size in KB (to prevent huge traces)
  maxOutputSizeKB: parseInt(process.env.OPENAI_TRACING_MAX_OUTPUT) || 500,
  
  // Log configuration on startup
  logConfig: process.env.OPENAI_TRACING_LOG_CONFIG !== 'false'
};

/**
 * Initialize tracing based on configuration
 */
export function initializeTracing(agentName = 'global') {
  // Check if tracing should be enabled for this agent
  const shouldTrace = config.enabled && 
    (config.agentsToTrace.length === 0 || config.agentsToTrace.includes(agentName));
  
  // Set tracing state
  setTracingDisabled(!shouldTrace);
  
  // Log configuration if enabled
  if (config.logConfig && agentName === 'global') {
    console.log('[Tracing Config] OpenAI tracing settings:');
    console.log(`  - Enabled: ${config.enabled}`);
    console.log(`  - Agents to trace: ${config.agentsToTrace.length === 0 ? 'all' : config.agentsToTrace.join(', ')}`);
    console.log(`  - Max output size: ${config.maxOutputSizeKB}KB`);
    console.log(`  - Current state: ${shouldTrace ? 'ENABLED' : 'DISABLED'}`);
  }
  
  return shouldTrace;
}

/**
 * Check if a specific agent should have tracing enabled
 */
export function isTracingEnabledForAgent(agentName) {
  return config.enabled && 
    (config.agentsToTrace.length === 0 || config.agentsToTrace.includes(agentName));
}

/**
 * Get tracing configuration
 */
export function getTracingConfig() {
  return { ...config };
}

/**
 * Truncate output to prevent massive traces
 */
export function truncateTracingOutput(output, agentName = 'unknown') {
  if (typeof output !== 'string') {
    output = JSON.stringify(output, null, 2);
  }
  
  const maxBytes = config.maxOutputSizeKB * 1024;
  const outputBytes = Buffer.byteLength(output, 'utf8');
  
  if (outputBytes > maxBytes) {
    const truncated = output.substring(0, maxBytes - 100) + 
      `\n\n[TRUNCATED: Output was ${(outputBytes / 1024).toFixed(1)}KB, max is ${config.maxOutputSizeKB}KB]`;
    
    console.warn(`[Tracing] Output truncated for ${agentName}: ${(outputBytes / 1024).toFixed(1)}KB -> ${config.maxOutputSizeKB}KB`);
    return truncated;
  }
  
  return output;
}

// Export config for testing
export { config as tracingConfig };