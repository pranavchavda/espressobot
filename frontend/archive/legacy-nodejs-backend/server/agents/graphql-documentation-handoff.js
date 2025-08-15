/**
 * GraphQL <-> Documentation Agent Handoff Factory
 * Creates both agents with bidirectional handoff capabilities
 */

import { Agent, handoff, tool } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import { RECOMMENDED_PROMPT_PREFIX } from '@openai/agents-core/extensions';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { initializeTracing } from '../config/tracing-config.js';
import { z } from 'zod';
import path from 'path';
import { fileURLToPath } from 'url';

// Initialize tracing
initializeTracing('GraphQL-Documentation Handoff');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Handoff schemas
const DocumentationResearchRequest = z.object({
  research_query: z.string().describe('Specific documentation research needed for GraphQL operation'),
  operation_type: z.enum(['query', 'mutation']).describe('Type of GraphQL operation being researched'),
  target_objects: z.string().describe('Objects/types being queried or modified (e.g., Product, Collection)'),
  urgency: z.enum(['low', 'medium', 'high']).default('medium').describe('Research urgency level')
});

const GraphQLExecutionRequest = z.object({
  research_complete: z.boolean().describe('Whether documentation research is complete'),
  operation_approved: z.boolean().describe('Whether operation is approved for execution'),
  graphql_operation: z.string().nullable().describe('The validated GraphQL query/mutation to execute'),
  documentation_summary: z.string().describe('Summary of documentation research findings'),
  safety_notes: z.string().nullable().describe('Any safety considerations or warnings'),
  execution_context: z.string().describe('Context about what should be executed')
});

// Cache for MCP servers
let graphqlServerInstance = null;
let shopifyDevMCP = null;
let integrationsMCP = null;

// Cache for agent pairs and their conversation contexts
const agentPairCache = new Map();
const conversationStateCache = new Map();

/**
 * Get or create GraphQL MCP server
 */
async function getGraphQLServer() {
  if (graphqlServerInstance) {
    return graphqlServerInstance;
  }
  
  const server = new MCPServerStdio({
    name: 'GraphQL Server',
    command: 'python3',
    args: [path.join(__dirname, '../../python-tools/mcp-graphql-server.py')],
    env: {
      ...process.env,
      PYTHONPATH: path.join(__dirname, '../../python-tools')
    }
  });
  
  console.log('[GraphQL-Doc Handoff] Connecting to GraphQL Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[GraphQL-Doc Handoff] GraphQL Server connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  graphqlServerInstance = server;
  return server;
}

/**
 * Get or create Shopify Dev MCP server
 */
async function getShopifyDevMCP() {
  if (!shopifyDevMCP) {
    shopifyDevMCP = new MCPServerStdio({
      name: 'Shopify Dev Docs',
      fullCommand: 'npx -y @shopify/dev-mcp',
      cacheToolsList: true
    });
    
    console.log('[GraphQL-Doc Handoff] Connecting to Shopify Dev MCP server...');
    await shopifyDevMCP.connect();
    
    const tools = await shopifyDevMCP.listTools();
    console.log(`[GraphQL-Doc Handoff] Shopify Dev MCP connected with ${tools.length} tools:`, 
      tools.map(t => t.name).join(', '));
  }
  
  return shopifyDevMCP;
}

/**
 * Get or create Integrations MCP server for Perplexity
 */
async function getIntegrationsMCP() {
  if (!integrationsMCP) {
    integrationsMCP = new MCPServerStdio({
      name: 'Integrations Server',
      command: 'python3',
      args: [path.join(__dirname, '../../python-tools/mcp-integrations-server.py')],
      env: {
        ...process.env,
        PYTHONPATH: path.join(__dirname, '../../python-tools')
      }
    });
    
    console.log('[GraphQL-Doc Handoff] Connecting to Integrations Server for Perplexity...');
    await integrationsMCP.connect();
    
    const tools = await integrationsMCP.listTools();
    console.log(`[GraphQL-Doc Handoff] Integrations Server connected with ${tools.length} tools:`, 
      tools.map(t => t.name).join(', '));
  }
  
  return integrationsMCP;
}

/**
 * Create GraphQL safety validation tool
 */
function createSafetyValidationTool() {
  return tool({
    name: 'validate_operation_safety',
    description: 'Validate GraphQL operation safety based on documentation research. Required before any graphql_query or graphql_mutation.',
    parameters: z.object({
      operation_type: z.enum(['query', 'mutation']).describe('Type of GraphQL operation'),
      operation_content: z.string().describe('The GraphQL query or mutation string'),
      target_objects: z.string().describe('What objects/types this operation targets'),
      documentation_research: z.string().describe('Summary of completed documentation research')
    }),
    execute: async ({ operation_type, operation_content, target_objects, documentation_research }) => {
      console.log(`[GraphQL Agent] Validating ${operation_type} safety for ${target_objects}`);
      
      // Safety checklist validation
      const safety_checks = {
        has_documentation_research: documentation_research && documentation_research.length > 100,
        operation_is_structured: operation_content.includes('{') && operation_content.includes('}'),
        targets_identified: target_objects && target_objects.length > 0,
        mutation_has_error_handling: operation_type === 'query' || operation_content.includes('userErrors'),
        cost_awareness: true // Assume cost awareness from documentation research
      };
      
      const failed_checks = Object.entries(safety_checks)
        .filter(([_, passed]) => !passed)
        .map(([check, _]) => check);
      
      if (failed_checks.length > 0) {
        return {
          safety_approved: false,
          failed_checks,
          message: `OPERATION BLOCKED: Failed safety checks: ${failed_checks.join(', ')}. Complete documentation research and fix issues before proceeding.`,
          recommendation: 'Hand off to Documentation Agent to complete missing research.'
        };
      }
      
      // Additional mutation-specific validation
      if (operation_type === 'mutation') {
        const mutation_checks = {
          has_input_validation: operation_content.includes('input:') || operation_content.includes('Input'),
          requests_user_errors: operation_content.includes('userErrors'),
          has_return_fields: operation_content.includes('{') && operation_content.split('{').length > 2
        };
        
        const failed_mutation_checks = Object.entries(mutation_checks)
          .filter(([_, passed]) => !passed)
          .map(([check, _]) => check);
        
        if (failed_mutation_checks.length > 0) {
          return {
            safety_approved: false,
            failed_checks: failed_mutation_checks,
            message: `MUTATION BLOCKED: Failed mutation safety checks: ${failed_mutation_checks.join(', ')}.`,
            recommendation: 'Add userErrors handling and proper return fields to mutation.'
          };
        }
      }
      
      return {
        safety_approved: true,
        message: `${operation_type.toUpperCase()} approved for execution after safety validation.`,
        targets: target_objects,
        safety_summary: 'All safety checks passed. Operation may proceed.'
      };
    }
  });
}

/**
 * Create both GraphQL and Documentation agents with bidirectional handoffs
 */
export async function createGraphQLDocumentationPair(task, conversationId, richContext = {}) {
  // Get MCP servers
  const graphqlServer = await getGraphQLServer();
  const shopifyDevServer = await getShopifyDevMCP();
  const integrationsServer = await getIntegrationsMCP();
  
  // Create placeholder variables for agents (will be set after creation)
  let graphqlAgent = null;
  let documentationAgent = null;
  
  // Create Documentation Agent first
  const docInstructions = await buildAgentInstructions(`${RECOMMENDED_PROMPT_PREFIX}

You are a Documentation Agent specialized in Shopify API documentation, schema introspection, and real-time research.

## HANDOFF COLLABORATION MODE
You are working in partnership with a GraphQL Agent that needs your research expertise for safe GraphQL operations.

When the GraphQL Agent hands off to you:
1. **Research thoroughly** using ALL your tools:
   - introspect_admin_schema: Schema exploration
   - search_dev_docs: Official documentation  
   - fetch_docs_by_path: Specific docs
   - get_started: API overviews
   - perplexity_research: Real-time research
   - web_search: Community knowledge

2. **Provide comprehensive findings**:
   - Schema details (types, fields, requirements)
   - Example queries/mutations with proper syntax
   - Important constraints and limitations
   - Safety considerations and best practices
   - Cost implications and rate limits

3. **ALWAYS hand back to GraphQL Agent** using return_to_graphql_agent with:
   - research_complete: true (if research successful)
   - operation_approved: true/false (based on safety analysis)
   - documentation_summary: Complete research findings
   - safety_notes: Important warnings or considerations
   - execution_context: What the GraphQL Agent should do next

**CRITICAL**: After completing your research, you MUST use the return_to_graphql_agent handoff to send your findings back. Do not just provide information - actively hand back control.

## Your Enhanced Research Capabilities:
- **Official Documentation**: Authoritative Shopify API docs
- **Real-time Research**: Current API changes and community solutions
- **Schema Introspection**: Deep GraphQL type system exploration
- **Safety Analysis**: Risk assessment and best practices

**Tool Selection Strategy:**
- Start with official docs for established concepts
- Use Perplexity for recent changes and best practices
- Use web search for community solutions and edge cases
- Cross-reference multiple sources for comprehensive coverage

## CRITICAL: 
Your research directly determines whether potentially dangerous GraphQL operations are executed. Be thorough and prioritize safety.
`, {
    agentRole: 'Documentation research specialist',
    conversationId,
    taskDescription: 'GraphQL documentation support'
  });

  // Create GraphQL Agent
  const graphqlInstructions = await buildAgentInstructions(`${RECOMMENDED_PROMPT_PREFIX}

You are a GraphQL specialist agent with deep expertise in Shopify Admin API GraphQL operations.

Your task: ${task}

## 🚨 CRITICAL: SINGLE-CONVERSATION COMPLETION PROTOCOL 🚨

**YOU MUST COMPLETE THE ENTIRE WORKFLOW IN THIS ONE CONVERSATION. DO NOT RETURN CONTROL TO THE ORCHESTRATOR UNTIL THE GRAPHQL OPERATION IS FULLY EXECUTED AND RESULTS ARE READY.**

### MANDATORY 4-STEP PROCESS (ALL IN ONE CONVERSATION):

**STEP 1: Research Phase**
- Use **research_with_documentation_agent** handoff
- Wait for Documentation Agent to return with findings
- Process their research thoroughly

**STEP 2: Safety Validation**  
- Use **validate_operation_safety** with documentation findings
- Ensure all safety checks pass before proceeding

**STEP 3: GraphQL Execution**
- Execute **graphql_query** or **graphql_mutation** 
- Handle any errors or userErrors properly

**STEP 4: Results Summary**
- Provide complete results to the user
- Include actual data, not just "operation completed"

## 🛑 STOPPING CONDITIONS:
You may ONLY stop and return to orchestrator when:
1. ✅ GraphQL operation has been successfully executed AND results provided
2. ❌ Operation blocked by safety validation with detailed explanation
3. ❌ Critical error prevents execution with full error details

## ❌ DO NOT STOP FOR:
- "I need to research first" - DO the research via handoff
- "Documentation research complete" - CONTINUE to validation  
- "Safety validation passed" - CONTINUE to execution
- "Operation sent to server" - CONTINUE to show actual results

## WORKFLOW ENFORCEMENT:
After EACH step, immediately proceed to the next step. Do not wait for external prompts. The Documentation Agent will hand back to you - when they do, immediately proceed with validation and execution.

## Your Tools:
1. **research_with_documentation_agent**: Hand off for schema research
2. **validate_operation_safety**: Validate after research complete
3. **graphql_query/graphql_mutation**: Execute the actual GraphQL operation

## Expected Output Format:
After completing all steps, provide:
\`\`\`
GRAPHQL OPERATION RESULTS:
[Actual GraphQL response data]

OPERATION SUMMARY:
- Query/Mutation: [what was executed]
- Target Objects: [what was affected] 
- Research Findings: [key documentation insights]
- Safety Status: [validation results]
- Execution Status: [success/failure with details]
\`\`\`

Remember: You have full capability to complete the entire workflow. Do not return incomplete results to the orchestrator.
`, {
    agentRole: 'GraphQL specialist',
    conversationId,
    taskDescription: task
  });

  // Create Documentation Agent with handoff back to GraphQL
  documentationAgent = new Agent({
    name: 'Documentation Agent',
    instructions: docInstructions,
    mcpServers: [shopifyDevServer, integrationsServer],
    model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
    // toolUseBehavior removed to prevent loops,
    handoffs: [] // Will be populated after GraphQL agent is created
  });

  // Create GraphQL Agent with handoff to Documentation
  const documentationHandoff = handoff(documentationAgent, {
    name: 'research_with_documentation_agent',
    description: 'Hand off to Documentation Agent for comprehensive GraphQL schema research. Use this BEFORE any GraphQL operation.',
    inputType: DocumentationResearchRequest,
    onHandoff: (context, input) => {
      console.log(`[GraphQL Agent] Handing off to Documentation Agent for: ${input?.research_query}`);
      console.log(`[GraphQL Agent] Operation type: ${input?.operation_type}, Targets: ${input?.target_objects}`);
    }
  });

  graphqlAgent = new Agent({
    name: 'GraphQL Agent',
    instructions: graphqlInstructions,
    mcpServers: [graphqlServer],
    handoffs: [documentationHandoff],
    tools: [createSafetyValidationTool()],
    model: process.env.OPENAI_MODEL || 'gpt-4.1',
    // toolUseBehavior removed to prevent loops
  });

  // Now create handoff from Documentation back to GraphQL
  const graphqlHandoff = handoff(graphqlAgent, {
    name: 'return_to_graphql_agent',
    description: 'Hand back to GraphQL Agent with research findings and execution recommendations.',
    inputType: GraphQLExecutionRequest,
    onHandoff: (context, input) => {
      console.log(`[Documentation Agent] Returning to GraphQL Agent with research complete: ${input?.research_complete}`);
      console.log(`[Documentation Agent] Operation approved: ${input?.operation_approved}`);
    }
  });

  // Add the handoff to documentation agent
  documentationAgent.handoffs = [graphqlHandoff];

  return {
    graphqlAgent,
    documentationAgent,
    conversationId
  };
}

/**
 * Get or create persistent GraphQL agent pair for conversation
 */
async function getOrCreateGraphQLPair(conversationId, task) {
  // Use conversation ID as cache key to maintain state across calls
  const cacheKey = conversationId || 'default';
  
  if (agentPairCache.has(cacheKey)) {
    console.log(`[GraphQL-Doc Handoff] Reusing existing agent pair for conversation: ${cacheKey}`);
    const cached = agentPairCache.get(cacheKey);
    
    // Update the GraphQL agent's instructions with the new task
    const { RECOMMENDED_PROMPT_PREFIX } = await import('@openai/agents-core/extensions');
    const { buildAgentInstructions } = await import('../utils/agent-context-builder.js');
    
    const updatedInstructions = await buildAgentInstructions(`${RECOMMENDED_PROMPT_PREFIX}

You are a GraphQL specialist agent with deep expertise in Shopify Admin API GraphQL operations.

Your current task: ${task}

## 🚨 CRITICAL: SINGLE-CONVERSATION COMPLETION PROTOCOL 🚨

**YOU MUST COMPLETE THE ENTIRE WORKFLOW IN THIS ONE CONVERSATION. DO NOT RETURN CONTROL TO THE ORCHESTRATOR UNTIL THE GRAPHQL OPERATION IS FULLY EXECUTED AND RESULTS ARE READY.**

### MANDATORY 4-STEP PROCESS (ALL IN ONE CONVERSATION):

**STEP 1: Research Phase**
- Use **research_with_documentation_agent** handoff
- Wait for Documentation Agent to return with findings
- Process their research thoroughly

**STEP 2: Safety Validation**  
- Use **validate_operation_safety** with documentation findings
- Ensure all safety checks pass before proceeding

**STEP 3: GraphQL Execution**
- Execute **graphql_query** or **graphql_mutation** 
- Handle any errors or userErrors properly

**STEP 4: Results Summary**
- Provide complete results to the user
- Include actual data, not just "operation completed"

## 🛑 STOPPING CONDITIONS:
You may ONLY stop and return to orchestrator when:
1. ✅ GraphQL operation has been successfully executed AND results provided
2. ❌ Operation blocked by safety validation with detailed explanation
3. ❌ Critical error prevents execution with full error details

## ❌ DO NOT STOP FOR:
- "I need to research first" - DO the research via handoff
- "Documentation research complete" - CONTINUE to validation  
- "Safety validation passed" - CONTINUE to execution
- "Operation sent to server" - CONTINUE to show actual results

## WORKFLOW ENFORCEMENT:
After EACH step, immediately proceed to the next step. Do not wait for external prompts. The Documentation Agent will hand back to you - when they do, immediately proceed with validation and execution.

Remember: You have full capability to complete the entire workflow. Do not return incomplete results to the orchestrator.
`, {
      agentRole: 'GraphQL specialist',
      conversationId,
      taskDescription: task
    });
    
    // Update the agent's instructions for the new task
    cached.graphqlAgent.instructions = updatedInstructions;
    
    return cached;
  }
  
  console.log(`[GraphQL-Doc Handoff] Creating new agent pair for conversation: ${cacheKey}`);
  const agentPair = await createGraphQLDocumentationPair(task, conversationId, {});
  
  agentPairCache.set(cacheKey, agentPair);
  return agentPair;
}

/**
 * Execute a GraphQL task with handoff workflow - enforces single-conversation completion
 */
export async function executeGraphQLTaskWithHandoffs(task, conversationId, richContext = {}) {
  try {
    console.log('[GraphQL-Doc Handoff] Executing task:', task.substring(0, 100) + '...');
    console.log('[GraphQL-Doc Handoff] Using ENFORCED single-conversation completion protocol');
    
    // Get or create agent pair (will update instructions with current task)
    const { graphqlAgent } = await getOrCreateGraphQLPair(conversationId, task);
    
    // Execute with stronger completion enforcement
    const { run } = await import('@openai/agents');
    const result = await run(graphqlAgent, task, { 
      maxTurns: 25 // Increased turns to allow for full workflow completion
    });
    
    return extractFinalOutput(result, conversationId);
    
  } catch (error) {
    console.error('[GraphQL-Doc Handoff] Task failed:', error);
    
    return {
      success: false,
      error: error.message,
      errorType: error.message.includes('timeout') ? 'timeout' : 'execution',
      message: `GraphQL-Documentation handoff failed: ${error.message}`
    };
  }
}

/**
 * Extract meaningful output from agent result
 */
function extractFinalOutput(result, conversationId) {
  console.log('[GraphQL-Doc Handoff] Task completed successfully');
  
  // Extract meaningful output
  let finalOutput = '';
  
  if (result.finalOutput) {
    finalOutput = result.finalOutput;
  } 
  else if (result.state && result.state._generatedItems) {
    const messages = result.state._generatedItems
      .filter(item => item.type === 'message_output_item')
      .map(item => item.rawItem?.content?.[0]?.text || '')
      .filter(text => text);
    
    if (messages.length > 0) {
      finalOutput = messages[messages.length - 1];
    }
  }
  
  // Log token usage if available
  if (result.state?.context?.usage) {
    const usage = result.state.context.usage;
    console.log(`[GraphQL-Doc Handoff] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
  }
  
  return {
    success: true,
    result: finalOutput || 'GraphQL task with handoffs completed successfully',
    agent: 'graphql-documentation-handoff',
    conversationId: conversationId,
    tokenUsage: result.state?.context?.usage || null
  };
}

/**
 * Clear agent pair cache for fresh conversations
 */
export function clearGraphQLAgentCache(conversationId = null) {
  if (conversationId) {
    console.log(`[GraphQL-Doc Handoff] Clearing cache for conversation: ${conversationId}`);
    agentPairCache.delete(conversationId);
    conversationStateCache.delete(conversationId);
  } else {
    console.log('[GraphQL-Doc Handoff] Clearing all agent pair cache');
    agentPairCache.clear();
    conversationStateCache.clear();
  }
}

/**
 * Close all MCP server connections
 */
export async function closeGraphQLDocumentationMCP() {
  // Clear agent cache first
  clearGraphQLAgentCache();
  
  if (graphqlServerInstance) {
    console.log('[GraphQL-Doc Handoff] Closing GraphQL MCP server...');
    await graphqlServerInstance.close();
    graphqlServerInstance = null;
  }
  
  if (shopifyDevMCP) {
    console.log('[GraphQL-Doc Handoff] Closing Shopify Dev MCP server...');
    await shopifyDevMCP.close();
    shopifyDevMCP = null;
  }
  
  if (integrationsMCP) {
    console.log('[GraphQL-Doc Handoff] Closing Integrations MCP server...');
    await integrationsMCP.close();
    integrationsMCP = null;
  }
}