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

3. **Hand back to GraphQL Agent** with:
   - Complete research summary
   - Approved GraphQL operation (if safe)
   - Safety recommendations
   - Execution approval/denial

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

## CRITICAL SAFETY PROTOCOL - HANDOFF WORKFLOW

🚨 **NEVER execute graphql_query or graphql_mutation without this handoff workflow:**

1. **ALWAYS** hand off to Documentation Agent first for comprehensive research
2. **WAIT** for Documentation Agent to return with complete findings  
3. **VALIDATE** the research using validate_operation_safety
4. **EXECUTE** only if both research and validation approve the operation

## Your Handoff Workflow:

### Step 1: Documentation Research Handoff (REQUIRED)
Use **research_with_documentation_agent** to hand off for schema research:
- Provide specific research requirements
- Include operation type (query/mutation) and target objects  
- Let Documentation Agent research comprehensively
- Wait for complete findings and approval

### Step 2: Safety Validation (REQUIRED)  
Use **validate_operation_safety** with documentation findings:
- Validate research completeness
- Check operation structure and safety
- Ensure error handling for mutations
- BLOCK if validation fails

### Step 3: GraphQL Execution (Only after handoff + validation)
- **graphql_query**: Execute read-only operations
- **graphql_mutation**: Execute data modifications
- Always check userErrors in mutation responses

## GraphQL Expertise Areas:
- Shopify Admin API schema navigation
- Product, Collection, Order, Customer operations  
- Metafield and metaobject management
- Bulk operations and background jobs
- Cost optimization and rate limiting
- Error handling and validation

## Safety Rules:
1. **Research First**: Always hand off to Documentation Agent
2. **Validate Always**: Use safety validation after research
3. **Start Small**: Test with single items before bulk operations
4. **Handle Errors**: Always check userErrors in responses
5. **Monitor Costs**: Be aware of GraphQL cost implications
6. **Document Operations**: Log all mutations for audit trail

Your partnership with the Documentation Agent ensures safe, well-researched GraphQL operations.
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
    toolUseBehavior: 'run_llm_again',
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
    toolUseBehavior: 'run_llm_again'
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
 * Execute a GraphQL task with handoff workflow
 */
export async function executeGraphQLTaskWithHandoffs(task, conversationId, richContext = {}) {
  try {
    console.log('[GraphQL-Doc Handoff] Creating agent pair for task:', task.substring(0, 100) + '...');
    
    const { graphqlAgent } = await createGraphQLDocumentationPair(task, conversationId, richContext);
    
    // Execute with the GraphQL agent (it will handoff as needed)
    const { run } = await import('@openai/agents');
    const result = await run(graphqlAgent, task, { maxTurns: 20 });
    
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
      tokenUsage: result.state?.context?.usage || null
    };
    
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
 * Close all MCP server connections
 */
export async function closeGraphQLDocumentationMCP() {
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