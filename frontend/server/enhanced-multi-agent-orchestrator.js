import { Agent, run, handoff } from '@openai/agents';
import logger from './logger';
import { saveTaskPlan, loadTaskPlan } from './task-manager';
import { convertImageToDataUrl } from './vision-preprocessor';
import retryVisionCall from './vision-retry-wrapper';
import { initializeCustomTools } from './custom-tool-discovery';

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

// Import existing agents
import espressobotOrchestrator from './agents/espressobot-orchestrator';
import memoryAgent from './agents/memory-agent';

// Initialize tools
const customTools = await initializeCustomTools();

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

Be concise in your responses and focus on routing to the right agent efficiently.`,
  tools: [
    handoff(catalogQueryAgent, "Hand off to Catalog Query Agent for product searches"),
    handoff(productCreationAgent, "Hand off to Product Creation Agent for new products"),
    handoff(productUpdateAgent, "Hand off to Product Update Agent for modifications"),
    handoff(inventoryAgent, "Hand off to Inventory Agent for stock management"),
    handoff(channelSpecialsAgent, "Hand off to Channel Specials Agent for promotions"),
    handoff(secureDataAgent, "Hand off to Secure Data Agent for sensitive data"),
    handoff(systemHealthAgent, "Hand off to System Health Agent for diagnostics"),
    handoff(taskPlanningAgent, "Hand off to Task Planning Agent for complex tasks"),
    handoff(userClarificationAgent, "Hand off to User Clarification Agent for ambiguity"),
    handoff(memoryAgent, "Hand off to Memory Agent to save context")
  ],
  model: 'gpt-4.1'
});

// Configure handoffs back to orchestrator from all agents
const handoffToOrchestrator = handoff(enhancedOrchestrator, "Hand back to orchestrator");

// Add handoff back to orchestrator for all specialized agents
catalogQueryAgent.tools.push(handoffToOrchestrator);
productCreationAgent.tools.push(handoffToOrchestrator);
productUpdateAgent.tools.push(handoffToOrchestrator);
inventoryAgent.tools.push(handoffToOrchestrator);
channelSpecialsAgent.tools.push(handoffToOrchestrator);
secureDataAgent.tools.push(handoffToOrchestrator);
systemHealthAgent.tools.push(handoffToOrchestrator);
taskPlanningAgent.tools.push(handoffToOrchestrator);
userClarificationAgent.tools.push(handoffToOrchestrator);
memoryAgent.tools.push(handoffToOrchestrator);

// Add actual tools to the agents that need them
// Note: The tools referenced in the agent definitions need to be registered in the tool registry
function assignToolsToAgent(agent, toolNames) {
  const assignedTools = [];
  for (const toolName of toolNames) {
    const tool = customTools.find(t => t.name === toolName || t.name === toolName.replace('.py', ''));
    if (tool) {
      assignedTools.push(tool);
    } else {
      logger.warn(`Tool ${toolName} not found in registry for agent ${agent.name}`);
    }
  }
  // Replace the tool names with actual tool objects
  agent.tools = [...assignedTools, handoffToOrchestrator];
}

// Assign tools based on agent definitions
assignToolsToAgent(catalogQueryAgent, ['search_products', 'get_product']);
assignToolsToAgent(productCreationAgent, [
  'create_product', 'create_full_product', 'create_combo', 
  'create_open_box', 'add_product_images'
]);
assignToolsToAgent(productUpdateAgent, [
  'update_pricing', 'bulk_price_update', 'manage_features_json',
  'manage_features_metaobjects', 'manage_tags', 'manage_variant_links',
  'update_status', 'manage_redirects', 'search_products'
]);
assignToolsToAgent(inventoryAgent, [
  'manage_inventory_policy', 'manage_skuvault_kits', 'upload_to_skuvault',
  'update_skuvault', 'update_skuvault_prices', 'update_skuvault_prices_v2'
]);
assignToolsToAgent(channelSpecialsAgent, ['manage_map_sales', 'manage_miele_sales']);
assignToolsToAgent(secureDataAgent, ['graphql_query', 'graphql_mutation']);
assignToolsToAgent(systemHealthAgent, ['test_connection']);
// Task Planning and User Clarification agents have no tools (only handoff)
// Memory agent tools are already assigned in its definition

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
        const dataUrl = await convertImageToDataUrl(imageUrl);
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
    const result = await retryVisionCall(async () => {
      return await run(enhancedOrchestrator, prompt, {
        threadId: conversation.id,
        maxTurns: 10,
        context: context,
        onStepStart: (step) => {
          logger.info('Step started:', step);
          if (step.type === 'handoff') {
            sendEvent('handoff', {
              from: step.agent?.name || 'unknown',
              to: step.targetAgent?.name || 'unknown',
              reason: step.reason || 'Processing request'
            });
          } else if (step.type === 'tool_call') {
            sendEvent('tool_call', {
              agent: step.agent?.name || 'unknown',
              tool: step.tool?.name || 'unknown',
              args: step.args
            });
          }
        },
        onStepFinish: (step, output) => {
          logger.info('Step finished:', { step, output });
          if (step.type === 'tool_call' && output) {
            sendEvent('tool_result', {
              agent: step.agent?.name || 'unknown',
              tool: step.tool?.name || 'unknown',
              result: output
            });
          }
        },
        onMessage: (message) => {
          logger.info('Agent message:', message);
          sendEvent('assistant_message', message);
        }
      });
    });

    // Extract the final response
    const lastMessage = result.messages[result.messages.length - 1];
    const response = lastMessage?.content || 'No response generated';

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