/**
 * Utility Agent - Specialized agent for memory operations and knowledge management
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Utility Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Utility server configuration
const UTILITY_SERVER = {
  name: 'Utility Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-utility-server.py')],
  env: {
    ...process.env,
    PYTHONPATH: path.join(__dirname, '../../python-tools')
  }
};

// Cache server connection
let serverInstance = null;

/**
 * Get or create MCP server connection
 */
async function getUtilityServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(UTILITY_SERVER);
  
  console.log('[Utility Agent] Connecting to Utility Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Utility Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create a Utility-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to utility server
  const mcpServer = await getUtilityServer();
  
  // Build system prompt with utility-specific expertise
  let systemPrompt = `You are a Utility specialist agent with expertise in memory management and knowledge operations for EspressoBot.

Your task: ${task}

You have access to the Utility Server which provides:
- **memory_operations**: Search, add, and manage memories in EspressoBot's local memory system

## Your Expertise:
- Knowledge management and retrieval
- Semantic search optimization
- Memory organization strategies
- Information storage best practices
- Context building from past interactions

## Memory Operations:

### Available Operations:
- **search**: Semantic search with similarity scoring
- **add**: Store new memories with deduplication
- **list**: View recent memories chronologically
- **delete**: Remove specific memories by ID

### Memory System Features:
- Local SQLite database storage
- OpenAI text-embedding-3-small for semantic search
- 85% similarity threshold for deduplication
- User-isolated memories for privacy
- ~100ms search, ~200ms add performance

### Use Cases:
- Store important facts about products/customers
- Remember past conversations and decisions
- Build context for future interactions
- Track business rules and patterns
- Create knowledge base entries

## Best Practices:

### When Adding Memories:
- Be specific and factual
- Include relevant context
- Use clear, searchable language
- Avoid duplicate information
- Focus on reusable knowledge

### When Searching:
- Use relevant keywords
- Try different phrasings
- Search before adding to avoid duplicates
- Combine multiple searches for context

### Memory Content Examples:
- "Breville Barista Express default price is $699.99"
- "Customer John Smith prefers dark roast, ordered 5 times"
- "Miele CM5310 requires MAP compliance, minimum $899"
- "Combo products typically offer 10-15% discount"
- "SkuVault kits use SKU1:QTY1,SKU2:QTY2 format"

IMPORTANT: 
- Always search before adding to prevent duplicates
- Focus on factual, reusable information
- Use clear, specific language for better retrieval
- Default user_id is 'user_2' if not specified
- Memories persist across conversations`;

  // Add memory context if searching
  if (richContext?.memoryQuery) {
    systemPrompt += `\n\n### Memory Search Context:\n`;
    systemPrompt += `Looking for: ${richContext.memoryQuery}\n`;
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Utility specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with utility server
  const agent = new Agent({
    name: 'Utility Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a utility task
 */
export async function executeUtilityTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Utility Agent] Starting task execution...');
    console.log('[Utility Agent] Task:', task);
    
    // Create agent
    const agent = await createAgent(task, conversationId, richContext);
    
    // Execute with timeout
    const maxTurns = 10;
    const timeout = 120000; // 2 minutes
    
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => {
        reject(new Error(`Task execution timed out after ${timeout/1000} seconds`));
      }, timeout);
    });
    
    const executionPromise = run(agent, task, { maxTurns });
    const result = await Promise.race([executionPromise, timeoutPromise]);
    
    console.log('[Utility Agent] Task completed successfully');
    
    // Extract meaningful output
    let finalOutput = '';
    
    if (result.finalOutput) {
      finalOutput = result.finalOutput;
    } else if (result.state && result.state._generatedItems) {
      const messages = result.state._generatedItems
        .filter(item => item.type === 'message_output_item')
        .map(item => item.rawItem?.content?.[0]?.text || '')
        .filter(text => text);
      
      if (messages.length > 0) {
        finalOutput = messages[messages.length - 1];
      }
    } else if (result.state && result.state.currentStep && result.state.currentStep.output) {
      finalOutput = result.state.currentStep.output;
    }
    
    // Log token usage
    if (result.state?.context?.usage) {
      const usage = result.state.context.usage;
      console.log(`[Utility Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'utility',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Utility Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}