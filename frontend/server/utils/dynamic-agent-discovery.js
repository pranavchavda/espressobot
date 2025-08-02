/**
 * Dynamic Agent Discovery System
 * Scans codebase to find all agents and their configurations
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Scan agent files to extract agent definitions
 */
async function scanAgentFiles() {
  const agentsDir = path.join(__dirname, '../agents');
  const agents = [];

  try {
    const files = await fs.readdir(agentsDir);
    const agentFiles = files.filter(file => file.endsWith('.js') && !file.includes('test'));

    for (const file of agentFiles) {
      const filePath = path.join(agentsDir, file);
      const content = await fs.readFile(filePath, 'utf8');
      
      const agentInfo = extractAgentInfo(content, file);
      if (agentInfo) {
        agents.push(agentInfo);
      }
    }

    // Also scan main orchestrator
    const orchestratorPath = path.join(__dirname, '../espressobot1.js');
    const orchestratorContent = await fs.readFile(orchestratorPath, 'utf8');
    const orchestratorInfo = extractAgentInfo(orchestratorContent, 'espressobot1.js');
    if (orchestratorInfo) {
      agents.push(orchestratorInfo);
    }

  } catch (error) {
    console.error('[Agent Discovery] Error scanning agent files:', error);
  }

  return agents;
}

/**
 * Extract agent information from file content
 */
function extractAgentInfo(content, filename) {
  const agentInfo = {
    filename,
    name: null,
    model: null,
    type: 'unknown',
    description: null,
    capabilities: [],
    tools: [],
    hardcodedModel: null
  };

  // Extract agent name from new Agent() calls
  const agentNameRegex = /new Agent\(\s*\{\s*name:\s*['"`]([^'"`]+)['"`]/g;
  const nameMatch = agentNameRegex.exec(content);
  if (nameMatch) {
    agentInfo.name = nameMatch[1];
  }

  // Extract model from new Agent() calls
  const modelRegex = /model:\s*['"`]?([^'"`\s,}]+)['"`]?/g;
  const modelMatch = modelRegex.exec(content);
  if (modelMatch) {
    agentInfo.hardcodedModel = modelMatch[1];
  }

  // Extract type from comments or patterns
  if (content.includes('MCP') || content.includes('mcp')) {
    agentInfo.type = 'mcp';
  } else if (content.includes('orchestrator') || content.includes('Orchestrator')) {
    agentInfo.type = 'orchestrator';
  } else if (content.includes('task') || content.includes('Task')) {
    agentInfo.type = 'task';
  } else if (content.includes('summariz') || content.includes('Summariz')) {
    agentInfo.type = 'summarizer';
  } else if (content.includes('SWE') || content.includes('swe')) {
    agentInfo.type = 'swe';
  } else if (content.includes('bash') || content.includes('Bash')) {
    agentInfo.type = 'bash';
  }

  // Extract description from comments
  const descriptionRegex = /\*\s*([A-Z][^*\n]+(?:agent|Agent|tool|Tool|system|System)[^*\n]*)/;
  const descMatch = descriptionRegex.exec(content);
  if (descMatch) {
    agentInfo.description = descMatch[1].trim();
  }

  // Extract capabilities from export default or comments
  const capabilitiesRegex = /capabilities:\s*\[([\s\S]*?)\]/;
  const capMatch = capabilitiesRegex.exec(content);
  if (capMatch) {
    const caps = capMatch[1].split(',').map(c => c.trim().replace(/['"]/g, ''));
    agentInfo.capabilities = caps.filter(c => c.length > 0);
  }

  // Extract tools list
  const toolsRegex = /tools:\s*\[([\s\S]*?)\]/;
  const toolsMatch = toolsRegex.exec(content);
  if (toolsMatch) {
    const tools = toolsMatch[1].split(',').map(t => t.trim().replace(/['"]/g, ''));
    agentInfo.tools = tools.filter(t => t.length > 0);
  }

  // Infer name from filename if not found
  if (!agentInfo.name) {
    agentInfo.name = filename
      .replace('.js', '')
      .split('-')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  return agentInfo;
}

/**
 * Get all agents (database + discovered)
 */
export async function getAllAgents() {
  // Get agents from database
  let databaseAgents = [];
  try {
    const { loadAgentConfigs } = await import('./agent-config-loader.js');
    const configs = await loadAgentConfigs();
    
    databaseAgents = Array.from(configs.entries()).map(([name, config]) => ({
      name,
      model: config.model,
      type: config.type || 'mcp',
      description: 'Database-configured agent',
      source: 'database',
      isActive: config.isActive
    }));
  } catch (error) {
    console.error('[Agent Discovery] Error loading database agents:', error);
  }

  // Get agents from file scanning
  const discoveredAgents = await scanAgentFiles();
  const fileAgents = discoveredAgents.map(agent => ({
    ...agent,
    source: 'file',
    model: agent.hardcodedModel,
    isActive: true
  }));

  // Merge and deduplicate
  const allAgents = new Map();
  
  // Add database agents first (they take precedence for configuration)
  databaseAgents.forEach(agent => {
    allAgents.set(agent.name, agent);
  });
  
  // Add file agents, but don't override database ones
  fileAgents.forEach(agent => {
    if (!allAgents.has(agent.name)) {
      allAgents.set(agent.name, {
        ...agent,
        configurable: false // Not in database, so not configurable via admin
      });
    } else {
      // Merge additional info from file into database agent
      const existing = allAgents.get(agent.name);
      allAgents.set(agent.name, {
        ...existing,
        ...agent,
        model: existing.model, // Keep database model
        source: 'both',
        hardcodedModel: agent.hardcodedModel,
        configurable: true
      });
    }
  });

  return Array.from(allAgents.values()).sort((a, b) => a.name.localeCompare(b.name));
}

/**
 * Sync discovered agents to database
 */
export async function syncAgentsToDatabase() {
  try {
    const { db } = await import('../config/database.js');
    const allAgents = await getAllAgents();
    
    const agentsToSync = allAgents.filter(agent => 
      agent.source === 'file' && agent.name !== 'EspressoBot1' // Don't auto-sync orchestrator
    );

    let syncedCount = 0;
    
    for (const agent of agentsToSync) {
      try {
        await db.agent_configs.upsert({
          where: { agent_name: agent.name },
          update: {
            agent_type: agent.type,
            description: agent.description || `${agent.type} agent`,
            updated_at: new Date()
          },
          create: {
            agent_name: agent.name,
            agent_type: agent.type,
            model_slug: agent.hardcodedModel || 'openai/gpt-4.1',
            description: agent.description || `${agent.type} agent`,
            system_prompt: null, // Use hardcoded prompts
            is_active: true,
            created_at: new Date(),
            updated_at: new Date()
          }
        });
        syncedCount++;
      } catch (error) {
        console.error(`[Agent Discovery] Error syncing agent ${agent.name}:`, error);
      }
    }

    console.log(`[Agent Discovery] Synced ${syncedCount} agents to database`);
    return syncedCount;
    
  } catch (error) {
    console.error('[Agent Discovery] Error syncing agents:', error);
    return 0;
  }
}

export default {
  getAllAgents,
  syncAgentsToDatabase,
  scanAgentFiles
};