/**
 * Agent Management API
 * Provides endpoints for dynamic agent configuration and model assignment
 */

import express from 'express';
import { db, withRetry } from '../config/database.js';
import { getAllAgents, syncAgentsToDatabase } from '../utils/dynamic-agent-discovery.js';

const router = express.Router();

/**
 * Get all agent configurations (database + discovered)
 */
router.get('/agents', async (req, res) => {
  try {
    const agents = await getAllAgents();

    res.json({
      success: true,
      agents: agents.map(agent => ({
        id: agent.id || `discovered_${agent.name.replace(/\s+/g, '_').toLowerCase()}`,
        agent_name: agent.name,
        agent_type: agent.type,
        model_slug: agent.model,
        hardcoded_model: agent.hardcodedModel,
        description: agent.description,
        is_active: agent.isActive !== false,
        source: agent.source,
        configurable: agent.configurable !== false,
        capabilities: agent.capabilities || [],
        tools: agent.tools || [],
        created_at: agent.created_at || new Date(),
        updated_at: agent.updated_at || new Date()
      }))
    });
  } catch (error) {
    console.error('[Agent Management] Error fetching agents:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch agent configurations'
    });
  }
});

/**
 * Sync discovered agents to database
 */
router.post('/sync', async (req, res) => {
  try {
    const syncedCount = await syncAgentsToDatabase();
    
    res.json({
      success: true,
      message: `Synced ${syncedCount} agents to database`,
      synced: syncedCount
    });
  } catch (error) {
    console.error('[Agent Management] Error syncing agents:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to sync agents'
    });
  }
});

/**
 * Force database reconnection (for debugging connection issues)
 */
router.post('/reconnect-db', async (req, res) => {
  try {
    const { testConnection, disconnectDatabase } = await import('../config/database.js');
    
    console.log('[Agent Management] Forcing database reconnection...');
    
    // Disconnect completely
    await disconnectDatabase();
    
    // Wait for cleanup
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Test new connection
    const success = await testConnection(3);
    
    res.json({
      success,
      message: success ? 'Database reconnection successful' : 'Database reconnection failed'
    });
  } catch (error) {
    console.error('[Agent Management] Error reconnecting database:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to reconnect database'
    });
  }
});

/**
 * Format model ID to human-readable name
 */
function formatModelName(modelId) {
  // Handle special cases
  const specialCases = {
    'gpt-4-turbo-preview': 'GPT-4 Turbo Preview',
    'gpt-4-turbo': 'GPT-4 Turbo',
    'gpt-4': 'GPT-4',
    'gpt-3.5-turbo': 'GPT-3.5 Turbo',
    'gpt-3.5-turbo-16k': 'GPT-3.5 Turbo 16K',
    'o1-preview': 'O1 Preview',
    'o1-mini': 'O1 Mini',
    'o3': 'O3',
    'o3-mini': 'O3 Mini',
    'o4': 'O4',
    'o4-mini': 'O4 Mini'
  };
  
  if (specialCases[modelId]) {
    return specialCases[modelId];
  }
  
  // Generic formatting
  return modelId
    .split('-')
    .map(part => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

/**
 * Get available models based on configured provider
 */
let modelCache = null;
let cacheTimestamp = 0;
let cachedProvider = null;
const CACHE_DURATION = 30 * 60 * 1000; // 30 minutes

router.get('/models', async (req, res) => {
  try {
    const provider = process.env.MODEL_PROVIDER || 'openai';
    const now = Date.now();
    
    // Return cached models if still valid and provider hasn't changed
    if (modelCache && cachedProvider === provider && (now - cacheTimestamp) < CACHE_DURATION) {
      return res.json({
        success: true,
        provider,
        models: modelCache,
        cached: true
      });
    }

    let processedModels = [];

    switch (provider) {
      case 'openai':
        // Fetch models from OpenAI API
        try {
          const openaiResponse = await fetch('https://api.openai.com/v1/models', {
            headers: {
              'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
              'Content-Type': 'application/json'
            }
          });

          if (!openaiResponse.ok) {
            throw new Error(`OpenAI API error: ${openaiResponse.status}`);
          }

          const openaiData = await openaiResponse.json();
          
          // Filter for chat models only
          const chatModels = openaiData.data
            .filter(model => 
              model.id.includes('gpt') || 
              model.id.includes('o1') || 
              model.id.includes('o3') ||
              model.id.includes('o4')
            )
            .filter(model => !model.id.includes('instruct')) // Exclude instruct models
            .map(model => ({
              id: model.id,
              name: formatModelName(model.id),
              provider: 'openai',
              description: `OpenAI ${formatModelName(model.id)}`,
              created: model.created
            }))
            .sort((a, b) => {
              // Sort by model family and version
              const getPriority = (id) => {
                if (id.includes('o4')) return 1;
                if (id.includes('o3')) return 2;
                if (id.includes('gpt-4')) return 3;
                if (id.includes('o1')) return 4;
                if (id.includes('gpt-3.5')) return 5;
                return 6;
              };
              return getPriority(a.id) - getPriority(b.id);
            });

          processedModels = chatModels;
        } catch (error) {
          console.error('[Agent Management] Error fetching OpenAI models:', error);
          // Fallback to some common models
          processedModels = [
            { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', provider: 'openai', description: 'Latest GPT-4 Turbo' },
            { id: 'gpt-4', name: 'GPT-4', provider: 'openai', description: 'GPT-4 base model' },
            { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'openai', description: 'Fast and efficient' }
          ];
        }
        break;

      case 'anthropic':
        // Fetch models from Anthropic API
        try {
          const anthropicResponse = await fetch('https://api.anthropic.com/v1/models', {
            headers: {
              'x-api-key': process.env.ANTHROPIC_API_KEY,
              'anthropic-version': '2023-06-01',
              'Content-Type': 'application/json'
            }
          });

          if (!anthropicResponse.ok) {
            throw new Error(`Anthropic API error: ${anthropicResponse.status}`);
          }

          const anthropicData = await anthropicResponse.json();
          
          processedModels = anthropicData.data
            .filter(model => model.type === 'model') // Anthropic uses 'model' type
            .map(model => ({
              id: model.id,
              name: model.display_name || formatModelName(model.id),
              provider: 'anthropic',
              description: `Anthropic ${model.display_name || formatModelName(model.id)}`,
              created: model.created_at
            }))
            .sort((a, b) => {
              // Sort by model family and version
              const getPriority = (id) => {
                if (id.includes('opus')) return 1;
                if (id.includes('sonnet')) return 2;
                if (id.includes('haiku')) return 3;
                return 4;
              };
              return getPriority(a.id) - getPriority(b.id);
            });

        } catch (error) {
          console.error('[Agent Management] Error fetching Anthropic models:', error);
          // Fallback to some known models
          processedModels = [
            { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus', provider: 'anthropic', description: 'Most capable model' },
            { id: 'claude-3-sonnet-20240229', name: 'Claude 3 Sonnet', provider: 'anthropic', description: 'Balanced model' },
            { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', provider: 'anthropic', description: 'Fast model' }
          ];
        }
        break;

      case 'openrouter':
        // Fetch from OpenRouter API
        const response = await fetch('https://openrouter.ai/api/v1/models', {
          headers: {
            'Authorization': `Bearer ${process.env.OPENROUTER_API_KEY}`,
            'Content-Type': 'application/json'
          }
        });

        if (!response.ok) {
          throw new Error(`OpenRouter API error: ${response.status}`);
        }

        const data = await response.json();
        
        // Process and categorize models
        processedModels = data.data
          .filter(model => !model.id.includes('moderated')) // Filter out moderated models
          .map(model => ({
            id: model.id,
            name: model.name || model.id,
            provider: model.id.split('/')[0],
            description: model.description,
            context_length: model.context_length,
            pricing: model.pricing,
            top_provider: model.top_provider
          }))
          .sort((a, b) => {
            // Sort by provider, then by name
            if (a.provider !== b.provider) {
              return a.provider.localeCompare(b.provider);
            }
            return a.name.localeCompare(b.name);
          });
        break;

      default:
        throw new Error(`Unknown provider: ${provider}`);
    }

    // Cache the results
    modelCache = processedModels;
    cacheTimestamp = now;
    cachedProvider = provider;

    res.json({
      success: true,
      provider,
      models: processedModels,
      cached: false,
      count: processedModels.length
    });

  } catch (error) {
    console.error('[Agent Management] Error fetching models:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch available models'
    });
  }
});

/**
 * Update agent configuration
 */
router.put('/agents/:id', async (req, res) => {
  const { id } = req.params;
  const { model_slug, system_prompt, description, is_active } = req.body;

  try {
    // Handle different ID formats: numeric, discovered_, or agent names
    let updatedAgent;
    
    console.log(`[Agent Management] Updating agent with ID: "${id}" (type: ${typeof id})`);
    
    if (id.startsWith('discovered_')) {
      // For discovered agents, extract the agent name and create/update by name
      let agentName = id.replace('discovered_', '').replace(/_/g, ' ')
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
      
      // Special case fixes for known agent names
      if (agentName === 'Espressobot1') {
        agentName = 'EspressoBot1';
      } else if (agentName === 'Contextanalyzer') {
        agentName = 'ContextAnalyzer';
      }
      
      console.log(`[Agent Management] Discovered agent name: "${agentName}" (from ID: "${id}")`);
      
      // First try to update
      updatedAgent = await withRetry(async (client) => {
        return await client.$queryRaw`
          UPDATE agent_configs 
          SET 
            model_slug = COALESCE(${model_slug}, model_slug),
            system_prompt = ${system_prompt}, 
            description = COALESCE(${description}, description),
            is_active = COALESCE(${is_active}, is_active),
            updated_at = CURRENT_TIMESTAMP
          WHERE agent_name = ${agentName}
          RETURNING *
        `;
      });
      
      // If not found, create it
      if (!updatedAgent || updatedAgent.length === 0) {
        console.log(`[Agent Management] Agent not found in database, creating: ${agentName}`);
        
        // Get agent info from discovery
        const { getAllAgents } = await import('../utils/dynamic-agent-discovery.js');
        const allAgents = await getAllAgents();
        const discoveredAgent = allAgents.find(a => a.name === agentName);
        
        if (discoveredAgent) {
          updatedAgent = await withRetry(async (client) => {
            return await client.$queryRaw`
              INSERT INTO agent_configs (
                agent_name, agent_type, model_slug, system_prompt, 
                description, is_active, created_at, updated_at
              ) VALUES (
                ${agentName},
                ${discoveredAgent.type || 'specialized'},
                ${model_slug || discoveredAgent.model || 'gpt-4-turbo'},
                ${system_prompt},
                ${description || discoveredAgent.description || `${discoveredAgent.type || 'specialized'} agent`},
                ${is_active !== undefined ? is_active : true},
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
              )
              RETURNING *
            `;
          });
        }
      }
    } else if (!isNaN(parseInt(id))) {
      // Handle numeric IDs (both string and number)
      const numericId = parseInt(id);
      console.log(`[Agent Management] Using numeric ID: ${numericId}`);
      
      updatedAgent = await withRetry(async (client) => {
        return await client.$queryRaw`
          UPDATE agent_configs 
          SET 
            model_slug = COALESCE(${model_slug}, model_slug),
            system_prompt = ${system_prompt},
            description = COALESCE(${description}, description),
            is_active = COALESCE(${is_active}, is_active),
            updated_at = CURRENT_TIMESTAMP
          WHERE id = ${numericId}
          RETURNING *
        `;
      });
    } else {
      // Try to find by agent name directly
      console.log(`[Agent Management] Trying to find by agent name: "${id}"`);
      
      updatedAgent = await withRetry(async (client) => {
        return await client.$queryRaw`
          UPDATE agent_configs 
          SET 
            model_slug = COALESCE(${model_slug}, model_slug),
            system_prompt = ${system_prompt},
            description = COALESCE(${description}, description),
            is_active = COALESCE(${is_active}, is_active),
            updated_at = CURRENT_TIMESTAMP
          WHERE agent_name = ${id}
          RETURNING *
        `;
      });
    }

    if (!updatedAgent || updatedAgent.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Agent configuration not found'
      });
    }

    // Clear agent config cache to force refresh
    try {
      const { loadAgentConfigs } = await import('../utils/agent-config-loader.js');
      await loadAgentConfigs(true); // Force refresh cache
    } catch (error) {
      console.warn('[Agent Management] Failed to refresh agent config cache:', error.message);
    }

    res.json({
      success: true,
      agent: updatedAgent[0],
      message: 'Agent configuration updated successfully'
    });

  } catch (error) {
    console.error('[Agent Management] Error updating agent:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update agent configuration'
    });
  }
});

/**
 * Get agent system prompt for editing
 */
router.get('/agents/:id/prompt', async (req, res) => {
  const { id } = req.params;

  try {
    const agent = await withRetry(async (client) => {
      return await client.$queryRaw`
        SELECT agent_name, system_prompt
        FROM agent_configs 
        WHERE id = ${parseInt(id)}
      `;
    });

    if (!agent || agent.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Agent not found'
      });
    }

    res.json({
      success: true,
      agent_name: agent[0].agent_name,
      system_prompt: agent[0].system_prompt
    });

  } catch (error) {
    console.error('[Agent Management] Error fetching agent prompt:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch agent prompt'
    });
  }
});

/**
 * Update agent system prompt
 */
router.put('/agents/:id/prompt', async (req, res) => {
  const { id } = req.params;
  const { system_prompt } = req.body;

  if (!system_prompt) {
    return res.status(400).json({
      success: false,
      error: 'System prompt is required'
    });
  }

  try {
    const updatedAgent = await withRetry(async (client) => {
      return await client.$queryRaw`
        UPDATE agent_configs 
        SET 
          system_prompt = ${system_prompt},
          updated_at = CURRENT_TIMESTAMP
        WHERE id = ${parseInt(id)}
        RETURNING agent_name, system_prompt
      `;
    });

    if (!updatedAgent || updatedAgent.length === 0) {
      return res.status(404).json({
        success: false,
        error: 'Agent not found'
      });
    }

    res.json({
      success: true,
      agent_name: updatedAgent[0].agent_name,
      message: 'System prompt updated successfully'
    });

  } catch (error) {
    console.error('[Agent Management] Error updating prompt:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update system prompt'
    });
  }
});

/**
 * Get agent statistics and usage
 */
router.get('/stats', async (req, res) => {
  try {
    const stats = await withRetry(async (client) => {
      return await client.$queryRaw`
        SELECT 
          agent_type,
          COUNT(*)::integer as count,
          COUNT(CASE WHEN is_active THEN 1 END)::integer as active_count,
          COUNT(CASE WHEN model_slug LIKE '%free%' THEN 1 END)::integer as free_models,
          COUNT(CASE WHEN model_slug LIKE 'openai/%' THEN 1 END)::integer as openai_models,
          COUNT(CASE WHEN model_slug LIKE 'anthropic/%' THEN 1 END)::integer as anthropic_models,
          COUNT(CASE WHEN model_slug LIKE 'openrouter/%' THEN 1 END)::integer as openrouter_models
        FROM agent_configs 
        GROUP BY agent_type
        ORDER BY agent_type
      `;
    });

    const totalStats = await withRetry(async (client) => {
      return await client.$queryRaw`
        SELECT 
          COUNT(*)::integer as total_agents,
          COUNT(CASE WHEN is_active THEN 1 END)::integer as active_agents,
          COUNT(DISTINCT model_slug)::integer as unique_models,
          COUNT(CASE WHEN system_prompt IS NOT NULL AND LENGTH(system_prompt) > 0 THEN 1 END)::integer as agents_with_prompts
        FROM agent_configs
      `;
    });

    res.json({
      success: true,
      stats: {
        by_type: stats,
        totals: totalStats[0]
      }
    });

  } catch (error) {
    console.error('[Agent Management] Error fetching stats:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch agent statistics'
    });
  }
});

export default router;