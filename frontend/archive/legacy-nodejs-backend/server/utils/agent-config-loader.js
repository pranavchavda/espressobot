/**
 * Agent Configuration Loader
 * Dynamically loads agent configurations from database and applies them
 */

import { db, withRetry } from '../config/database.js';
import { OpenRouterProvider, AGENT_MODEL_MAP } from '../models/openrouter-provider.js';

let configCache = new Map();
let cacheTimestamp = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

/**
 * Load all agent configurations from database
 */
export async function loadAgentConfigs(forceRefresh = false) {
  const now = Date.now();
  
  // Return cached configs if still valid and not forcing refresh
  if (!forceRefresh && configCache.size > 0 && (now - cacheTimestamp) < CACHE_DURATION) {
    return configCache;
  }

  try {
    const configs = await withRetry(async (client) => {
      return await client.$queryRaw`
        SELECT agent_name, agent_type, model_slug, system_prompt, is_active
        FROM agent_configs 
        WHERE is_active = true
        ORDER BY agent_name
      `;
    });

    // Clear and rebuild cache
    configCache.clear();
    
    configs.forEach(config => {
      configCache.set(config.agent_name, {
        name: config.agent_name,
        type: config.agent_type,
        model: config.model_slug,
        systemPrompt: config.system_prompt,
        isActive: config.is_active
      });
    });

    cacheTimestamp = now;
    console.log(`[Agent Config] Loaded ${configs.length} agent configurations`);
    
    return configCache;

  } catch (error) {
    console.error('[Agent Config] Error loading configurations:', error);
    // Return existing cache or empty map
    return configCache.size > 0 ? configCache : new Map();
  }
}

/**
 * Get configuration for a specific agent
 */
export async function getAgentConfig(agentName) {
  const configs = await loadAgentConfigs();
  return configs.get(agentName) || null;
}

/**
 * Get model slug for an agent (with fallback to environment variables)
 */
export async function getAgentModel(agentName) {
  const config = await getAgentConfig(agentName);
  
  if (config && config.model) {
    return config.model;
  }
  
  // Check environment variable fallbacks based on agent type
  // First try to get agent type from config or use a mapping
  const agentType = config?.type || getAgentTypeFromName(agentName);
  
  switch (agentType) {
    case 'orchestrator':
      return process.env.FALLBACK_ORCHESTRATOR_MODEL || 'gpt-4.1-turbo';
    case 'planner':
      return process.env.FALLBACK_PLANNER_MODEL || 'gpt-4-turbo';
    case 'software_engineer':
      return process.env.FALLBACK_SOFTWARE_ENGINEER_MODEL || 'claude-3.5-sonnet';
    case 'execution':
      return process.env.FALLBACK_EXECUTION_AGENT_MODEL || 'gpt-3.5-turbo';
    default:
      // Fallback to hardcoded map or default
      return AGENT_MODEL_MAP[agentName] || AGENT_MODEL_MAP.default || process.env.FALLBACK_ORCHESTRATOR_MODEL || 'gpt-4.1-turbo';
  }
}

/**
 * Determine agent type from agent name
 */
function getAgentTypeFromName(agentName) {
  const name = agentName.toLowerCase();
  
  if (name.includes('orchestrator') || name === 'espressobot1') {
    return 'orchestrator';
  } else if (name.includes('planner') || name.includes('planning')) {
    return 'planner';
  } else if (name.includes('swe') || name.includes('software') || name.includes('engineer')) {
    return 'software_engineer';
  } else if (name.includes('execution') || name.includes('bash')) {
    return 'execution';
  }
  
  return 'specialized';
}

/**
 * Get system prompt for an agent
 */
export async function getAgentSystemPrompt(agentName) {
  const config = await getAgentConfig(agentName);
  
  if (config && config.systemPrompt) {
    return config.systemPrompt;
  }
  
  return null; // Agent will use its hardcoded prompt
}

/**
 * Create model provider for an agent with dynamic configuration
 */
export async function createAgentModelProvider(agentName) {
  const modelSlug = await getAgentModel(agentName);
  const provider = process.env.MODEL_PROVIDER || 'openai';
  
  // Import the createModelProvider function from espressobot1.js
  const { createModelProvider } = await import('../espressobot1.js');
  
  // Create provider with the model slug
  return createModelProvider(modelSlug);
}

/**
 * Discover all available agents dynamically
 */
export async function discoverAvailableAgents() {
  const agents = new Set();
  
  // Add agents from database
  const configs = await loadAgentConfigs();
  configs.forEach((config, name) => {
    agents.add(name);
  });
  
  // Add agents from hardcoded map (in case some aren't in DB yet)
  Object.keys(AGENT_MODEL_MAP).forEach(agentName => {
    if (agentName !== 'default') {
      agents.add(agentName);
    }
  });
  
  return Array.from(agents).sort();
}

/**
 * Update agent configuration in database
 */
export async function updateAgentConfig(agentName, updates) {
  try {
    const result = await withRetry(async (client) => {
      const setClaus = [];
      const values = [];
      let paramIndex = 1;

      if (updates.model_slug !== undefined) {
        setClaus.push(`model_slug = $${paramIndex++}`);
        values.push(updates.model_slug);
      }
      
      if (updates.system_prompt !== undefined) {
        setClaus.push(`system_prompt = $${paramIndex++}`);
        values.push(updates.system_prompt);
      }
      
      if (updates.is_active !== undefined) {
        setClaus.push(`is_active = $${paramIndex++}`);
        values.push(updates.is_active);
      }

      if (setClaus.length === 0) {
        throw new Error('No updates provided');
      }

      setClaus.push(`updated_at = CURRENT_TIMESTAMP`);
      values.push(agentName);

      const query = `
        UPDATE agent_configs 
        SET ${setClaus.join(', ')}
        WHERE agent_name = $${paramIndex}
        RETURNING *
      `;

      return await client.$queryRawUnsafe(query, ...values);
    });

    if (result && result.length > 0) {
      // Clear cache to force reload
      configCache.clear();
      console.log(`[Agent Config] Updated configuration for ${agentName}`);
      return result[0];
    }
    
    return null;

  } catch (error) {
    console.error(`[Agent Config] Error updating ${agentName}:`, error);
    throw error;
  }
}

/**
 * Initialize agent configuration system
 */
export async function initializeAgentConfigs() {
  console.log('[Agent Config] Initializing agent configuration system...');
  
  try {
    const configs = await loadAgentConfigs(true);
    console.log(`[Agent Config] Initialized with ${configs.size} agent configurations`);
    
    // Log summary
    const summary = {};
    configs.forEach((config, name) => {
      const provider = config.model.split('/')[0];
      summary[provider] = (summary[provider] || 0) + 1;
    });
    
    console.log('[Agent Config] Model provider distribution:', summary);
    
    return true;
  } catch (error) {
    console.error('[Agent Config] Failed to initialize:', error);
    return false;
  }
}

export default {
  loadAgentConfigs,
  getAgentConfig,
  getAgentModel,
  getAgentSystemPrompt,
  createAgentModelProvider,
  discoverAvailableAgents,
  updateAgentConfig,
  initializeAgentConfigs
};