import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import logger from './logger.js';
import { saveTaskPlan, loadTaskPlan } from './task-manager.js';
import { validateAndFixBase64 } from './vision-preprocessor.js';
import { runWithVisionRetry } from './vision-retry-wrapper.js';
import { openAITools } from './tools/openai-tool-converter.js';

// Set API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Import all specialized agents
import catalogQueryAgent from './agents/specialized/catalog_query_agent.js';
import channelSpecialsAgent from './agents/specialized/channel_specials_agent.js';
import inventoryAgent from './agents/specialized/inventory_agent.js';
import productCreationAgent from './agents/specialized/product_creation_agent.js';
import productUpdateAgent from './agents/specialized/product_update_agent.js';
import secureDataAgent from './agents/specialized/secure_data_agent.js';
import systemHealthAgent from './agents/specialized/system_health_agent.js';
import taskPlanningAgent from './agents/specialized/task_planning_agent.js';
import userClarificationAgent from './agents/specialized/user_clarification_agent.js';

// Import existing memory agent
import { memoryAgent } from './agents/memory-agent.js';

// Function to assign OpenAI tools to agents
function assignOpenAITools(agent, toolNames) {
  const assignedTools = [];
  
  // Keep existing non-string tools (like handoffs)
  agent.tools.forEach(tool => {
    if (typeof tool !== 'string') {
      assignedTools.push(tool);
    }
  });
  
  // Add OpenAI format tools
  toolNames.forEach(toolName => {
    const tool = openAITools[toolName];
    if (tool) {
      assignedTools.push(tool);
      logger.info(`Assigned tool ${toolName} to ${agent.name}`);
    } else {
      logger.warn(`Tool ${toolName} not found for ${agent.name}`);
    }
  });
  
  agent.tools = assignedTools;
}

// Assign tools to all agents
assignOpenAITools(catalogQueryAgent, ['search_products', 'get_product']);
assignOpenAITools(channelSpecialsAgent, ['manage_map_sales', 'manage_miele_sales']);
assignOpenAITools(inventoryAgent, [
  'manage_inventory_policy', 'manage_skuvault_kits', 'upload_to_skuvault',
  'update_skuvault_prices', 'update_skuvault_prices_v2'
]);
assignOpenAITools(productCreationAgent, [
  'create_product', 'product_create_full', 'create_combo', 
  'create_open_box', 'add_product_images'
]);
assignOpenAITools(productUpdateAgent, [
  'update_pricing', 'bulk_price_update', 'manage_features_json',
  'manage_features_metaobjects', 'manage_tags', 'manage_variant_links',
  'update_status', 'manage_redirects', 'search_products'
]);
assignOpenAITools(secureDataAgent, ['graphql_query', 'graphql_mutation']);
assignOpenAITools(systemHealthAgent, ['test_connection']);
// Task Planning and User Clarification agents have no tools
// Memory agent already has its tools defined

// Create the enhanced orchestrator agent
const enhancedOrchestrator = new Agent({
  name: 'Enhanced_EspressoBot_Orchestrator',
  description: 'Main orchestrator that analyzes requests and delegates to specialized agents',
  instructions: `You are the main orchestrator for EspressoBot. Your role is to analyze user requests and delegate them to the most appropriate specialized agent. 

Available agents and their purposes:
1. **Catalog_Query_Agent** - For product searches and lookups
2. **Product_Creation_Agent** - For creating new products, combos, or open box items
3. **Product_Update_Agent** - For updating existing products (prices, tags, status, etc.)
4. **Inventory_Agent** - For inventory policy and SkuVault synchronization
5. **Channel_Specials_Agent** - For MAP sales and vendor-specific promotions
6. **Secure_Data_Agent** - For sensitive order/customer data (requires justification)
7. **System_Health_Agent** - For system diagnostics and health checks
8. **Task_Planning_Agent** - For breaking down complex multi-step requests
9. **User_Clarification_Agent** - When you need to clarify ambiguous requests
10. **Memory_Agent** - For storing important conversation context

Decision process:
1. First, determine if the request is ambiguous - use User_Clarification_Agent
2. For complex multi-step requests - use Task_Planning_Agent first
3. For simple, single-purpose requests - route directly to the appropriate specialized agent
4. Always save important context to Memory_Agent after completing tasks

IMPORTANT: You MUST delegate ALL requests to the appropriate specialized agent. You should NEVER answer questions directly or use tools yourself. Your ONLY job is to analyze the request and hand it off to the right agent.

For example:
- "Search for products" → Hand off to Catalog_Query_Agent
- "Create a product" → Hand off to Product_Creation_Agent
- "Update pricing" → Hand off to Product_Update_Agent

Always use the handoff function to delegate to specialized agents.`,
  model: 'gpt-4.1',  // Using same model as working orchestrator
  handoffs: [
    catalogQueryAgent,
    productCreationAgent,
    productUpdateAgent,
    inventoryAgent,
    channelSpecialsAgent,
    secureDataAgent,
    systemHealthAgent,
    taskPlanningAgent,
    userClarificationAgent,
    memoryAgent
  ]
});

// Configure handoffs back to orchestrator from all agents
catalogQueryAgent.handoffs = [enhancedOrchestrator];
productCreationAgent.handoffs = [enhancedOrchestrator];
productUpdateAgent.handoffs = [enhancedOrchestrator];
inventoryAgent.handoffs = [enhancedOrchestrator];
channelSpecialsAgent.handoffs = [enhancedOrchestrator];
secureDataAgent.handoffs = [enhancedOrchestrator];
systemHealthAgent.handoffs = [enhancedOrchestrator];
taskPlanningAgent.handoffs = [enhancedOrchestrator];
userClarificationAgent.handoffs = [enhancedOrchestrator];
memoryAgent.handoffs = [enhancedOrchestrator];

export async function handleEnhancedMultiAgentRequest(message, imageUrl, conversation, sendEvent) {
  try {
    sendEvent('agent_status', 'Starting enhanced multi-agent processing...');

    // Prepare context
    const context = {
      conversationId: conversation.id,
      messages: conversation.messages || [],
      taskProgress: []
    };

    // Prepare the prompt with context
    let prompt = message;
    if (conversation.messages && conversation.messages.length > 0) {
      const recentMessages = conversation.messages.slice(-10); // Last 10 messages
      const contextStr = recentMessages.map(m => 
        `${m.role}: ${m.content.substring(0, 200)}${m.content.length > 200 ? '...' : ''}`
      ).join('\n');
      prompt = `Previous conversation context:\n${contextStr}\n\nUser: ${message}`;
    }

    // Add image if provided
    if (imageUrl) {
      try {
        // If imageUrl is already a data URL, validate it; otherwise convert it
        const dataUrl = imageUrl.startsWith('data:') 
          ? validateAndFixBase64(imageUrl)
          : imageUrl; // Assume it's already a valid URL
        prompt = [
          { type: 'text', text: prompt },
          { type: 'image_url', image_url: { url: dataUrl } }
        ];
      } catch (error) {
        logger.error('Error processing image:', error);
        sendEvent('error', `Image processing failed: ${error.message}`);
      }
    }

    // Run the orchestrator
    const result = await runWithVisionRetry(enhancedOrchestrator, prompt, {
        threadId: conversation.id,
        maxTurns: 10,
        context: context,
        onStepStart: (step) => {
          logger.info('Step started:', step);
          
          if (step.type === 'handoff') {
            const fromAgent = step.agent?.name || 'unknown';
            const toAgent = step.handoff_to || 'unknown';
            
            sendEvent('handoff', {
              from: fromAgent,
              to: toAgent,
              reason: 'Processing request'
            });
            
            sendEvent('agent_processing', {
              agent: toAgent,
              message: `${toAgent} is processing your request...`,
              status: 'processing'
            });
          } else if (step.type === 'tool_call') {
            const agentName = step.agent?.name || 'unknown';
            const toolName = step.tool?.name || step.tool_name || 'unknown';
            
            sendEvent('tool_call', {
              agent: agentName,
              tool: toolName,
              status: 'started'
            });
            
            sendEvent('agent_processing', {
              agent: agentName,
              tool: toolName,
              message: `${agentName} is using ${toolName}...`,
              status: 'processing'
            });
          }
        },
        onStepFinish: (step, output) => {
          logger.info('Step finished:', { step, output });
          
          if (step.type === 'tool_call' && output) {
            sendEvent('tool_result', {
              agent: step.agent?.name || 'unknown',
              tool: step.tool?.name || step.tool_name || 'unknown',
              result: output
            });
          }
        },
        onMessage: (message) => {
          logger.info('Agent message:', message);
          sendEvent('assistant_message', message);
        }
      });

    // Extract the final response
    let response = 'No response generated';
    
    if (result?.state?._currentStep?.output) {
      response = result.state._currentStep.output;
    } else if (result?.messages?.length > 0) {
      const lastMessage = result.messages[result.messages.length - 1];
      response = lastMessage.content || response;
    }

    // Check if there's a task plan
    const taskPlanPath = `/server/plans/${conversation.id}-plan.md`;
    try {
      const taskPlan = await loadTaskPlan(taskPlanPath);
      if (taskPlan) {
        sendEvent('task_markdown', taskPlan);
      }
    } catch (error) {
      // No task plan exists, which is fine
    }

    sendEvent('agent_status', 'Processing complete');
    return response;

  } catch (error) {
    logger.error('Enhanced multi-agent orchestrator error:', error);
    sendEvent('error', error.message);
    throw error;
  }
}

export default enhancedOrchestrator;