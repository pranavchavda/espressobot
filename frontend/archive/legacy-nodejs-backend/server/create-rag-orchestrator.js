import { Agent, tool, webSearchTool } from '@openai/agents';
import { z } from 'zod';
import ragSystemPromptManager from './memory/rag-system-prompt-manager.js';
import { spawnBashAgent, spawnParallelBashAgents, dynamicOrchestrator } from './espressobot1.js';
import { taskPlanningAgent } from './agents/task-planning-agent.js';
import { createConnectedSWEAgent } from './agents/swe-agent-connected.js';
import { run } from '@openai/agents';

// Base orchestrator instructions (concise)
const BASE_ORCHESTRATOR_PROMPT = `# EspressoBot Orchestrator

You orchestrate the iDrinkCoffee.com e-commerce operations by analyzing requests and delegating to specialized agents.

## Execution Rules
- **READ operations**: Execute immediately (searches, queries, reports)
- **WRITE operations**: Confirm first (updates, creates, deletes)  
- **Task completion**: Once started, complete ALL tasks without pausing
- **Results**: Always provide complete data, never partial samples

## Agent Capabilities

### Bash Agents CAN:
- Execute all Python tools (run_graphql_query, update_pricing, etc.)
- Access live Shopify data and perform mutations
- Update task status

### Bash Agents CANNOT:
- Access MCP (documentation, schema introspection)
- Use Context7 or Shopify Dev docs

### SWE Agent CAN:
- Create/modify tools
- Access MCP for documentation and schema
- Perform software engineering tasks

## Decision Tree
User Request → 
├─ Shopify Data Operation → Spawn Bash Agent
├─ Tool Creation/Modification → Handoff to SWE Agent  
├─ Documentation/Schema Lookup → Handoff to SWE Agent
├─ Multiple Independent Tasks → spawn_parallel_bash_agents
└─ Complex Multi-Step Operation → Task Planner → Execute Plan

## Task Management
- Check tasks: get_current_tasks
- Update status: update_task_status
- Complete ALL tasks before returning control
- Mark tasks as in_progress before starting, completed when done

## Reference Files
- Business rules: /home/pranav/espressobot/frontend/server/prompts/idc-business-rules.md
- Tool guide: /home/pranav/espressobot/frontend/server/tool-docs/TOOL_USAGE_GUIDE.md`;

/**
 * Creates an orchestrator with RAG-enhanced system prompt
 */
export async function createRAGOrchestrator(userMessage = '', options = {}) {
  const { conversationId, userId } = options;
  
  // Generate context query for RAG
  const contextQuery = userMessage || "orchestrate manage shopify ecommerce operations tasks agents";
  
  // Get RAG-enhanced prompt
  const enhancedPrompt = await ragSystemPromptManager.getSystemPrompt(contextQuery, {
    basePrompt: BASE_ORCHESTRATOR_PROMPT,
    maxFragments: 10,
    includeMemories: true,
    userId: userId || global.currentUserId,
    agentType: 'orchestrator',
    minScore: 0.4
  });
  
  // Copy all tools and configuration from the original orchestrator
  const orchestratorConfig = {
    ...dynamicOrchestrator,
    instructions: enhancedPrompt
  };
  
  // Create new agent with enhanced instructions
  return new Agent(orchestratorConfig);
}

/**
 * Updates the global orchestrator with RAG enhancement
 * This is useful for long-running processes where the orchestrator is reused
 */
export async function enhanceOrchestratorWithRAG(userMessage = '') {
  const userId = global.currentUserId || global.currentConversationId;
  
  // Generate enhanced prompt
  const enhancedPrompt = await ragSystemPromptManager.getSystemPrompt(
    userMessage || "orchestrate manage shopify ecommerce operations",
    {
      basePrompt: BASE_ORCHESTRATOR_PROMPT,
      maxFragments: 10,
      includeMemories: true,
      userId: userId,
      agentType: 'orchestrator',
      minScore: 0.4
    }
  );
  
  // Update the existing orchestrator's instructions
  dynamicOrchestrator.instructions = enhancedPrompt;
  
  console.log('[RAG Orchestrator] Enhanced orchestrator prompt with context');
  return dynamicOrchestrator;
}