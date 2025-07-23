/**
 * Media Agent - Specialized agent for product image management
 */

import { Agent } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import path from 'path';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { fileURLToPath } from 'url';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Media Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Media server configuration
const MEDIA_SERVER = {
  name: 'Media Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-media-server.py')],
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
async function getMediaServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(MEDIA_SERVER);
  
  console.log('[Media Agent] Connecting to Media Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[Media Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create a Media-specialized agent
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to media server
  const mcpServer = await getMediaServer();
  
  // Build system prompt with media-specific expertise
  let systemPrompt = `You are a Media specialist agent with expertise in product photography, image management, and visual merchandising.

Your task: ${task}

You have access to the Media Server which provides:
- **add_product_images**: Comprehensive image management - add from URLs or local files, list, delete, or reorder

## Your Expertise:
- Product photography best practices
- Image optimization for e-commerce
- Alt text for accessibility and SEO
- Visual merchandising strategies
- Image ordering and presentation

## Tool Capabilities:

### add_product_images Actions:
- **add**: Add new images from URLs or local files
- **list**: View all current product images
- **delete**: Remove specific images by position
- **reorder**: Change the order of product images
- **clear**: Remove all images

### Key Features:
- Product identifier can be SKU, handle, or product ID
- Local files are uploaded to Shopify's staging area
- Images are processed asynchronously by Shopify
- First image becomes the featured image
- Supports alt text for each image

## Business Context:
- High-quality images drive conversions
- First image is most important (featured image)
- Alt text improves accessibility and SEO
- Multiple angles help customers make decisions
- Consistent image style builds brand trust

## Best Practices:
- Main product shot first, then angles/details
- Include lifestyle images when relevant
- Add descriptive alt text for accessibility
- Maintain consistent image dimensions
- Show product scale and context

IMPORTANT: 
- Changes may take a few seconds to appear
- Local file uploads require staging first
- Always provide alt text for accessibility
- Order matters - first image is featured`;

  // Add any additional context
  if (richContext?.imageUrls) {
    systemPrompt += `\n\n### Images to Process:\n`;
    richContext.imageUrls.forEach((url, idx) => {
      systemPrompt += `${idx + 1}. ${url}\n`;
    });
  }

  // Build final instructions
  const instructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'Media specialist',
    conversationId,
    taskDescription: task
  });

  // Create agent with media server
  const agent = new Agent({
    name: 'Media Agent',
    instructions,
    mcpServers: [mcpServer],
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    toolUseBehavior: 'run_llm_again'
  });

  return agent;
}

/**
 * Execute a media-related task
 */
export async function executeMediaTask(task, conversationId, richContext = {}) {
  const { run } = await import('@openai/agents');
  
  try {
    console.log('[Media Agent] Starting task execution...');
    console.log('[Media Agent] Task:', task);
    
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
    
    console.log('[Media Agent] Task completed successfully');
    
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
      console.log(`[Media Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
    }
    
    return {
      success: true,
      result: finalOutput || 'Task completed but no output generated',
      agent: 'media',
      tokenUsage: result.state?.context?.usage || null
    };
    
  } catch (error) {
    console.error('[Media Agent] Task execution failed:', error);
    return {
      success: false,
      error: error.message,
      details: error.stack
    };
  }
}