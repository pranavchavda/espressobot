/**
 * GraphQL Agent - Specialized agent for Shopify GraphQL operations
 * Features integrated documentation agent connectivity and strict safety protocols
 */

import { Agent, tool, handoff } from '@openai/agents';
import { MCPServerStdio } from '@openai/agents-core';
import { buildAgentInstructions } from '../utils/agent-context-builder.js';
import { initializeTracing } from '../config/tracing-config.js';
import { z } from 'zod';
import path from 'path';
import { fileURLToPath } from 'url';

// Import documentation agent for handoffs
import { createDocumentationMCPAgent } from './documentation-mcp-agent.js';

// Initialize tracing configuration for this agent
initializeTracing('GraphQL Agent');

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// GraphQL server configuration
const GRAPHQL_SERVER = {
  name: 'GraphQL Server',
  command: 'python3',
  args: [path.join(__dirname, '../../python-tools/mcp-graphql-server.py')],
  env: {
    ...process.env,
    PYTHONPATH: path.join(__dirname, '../../python-tools')
  }
};

// Cache server connection
let serverInstance = null;

// Schema for documentation research handoff
const DocumentationResearchRequest = z.object({
  research_query: z.string().describe('Specific documentation research needed for GraphQL operation'),
  operation_type: z.enum(['query', 'mutation']).describe('Type of GraphQL operation being researched'),
  target_objects: z.string().describe('Objects/types being queried or modified (e.g., Product, Collection)'),
  urgency: z.enum(['low', 'medium', 'high']).default('medium').describe('Research urgency level')
});

// Schema for GraphQL execution response
const GraphQLExecutionResponse = z.object({
  research_complete: z.boolean().describe('Whether documentation research is complete'),
  operation_approved: z.boolean().describe('Whether operation is approved for execution'),
  graphql_operation: z.string().nullable().describe('The validated GraphQL query/mutation to execute'),
  documentation_summary: z.string().describe('Summary of documentation research findings'),
  safety_notes: z.string().nullable().describe('Any safety considerations or warnings')
});

/**
 * Get or create MCP server connection
 */
async function getGraphQLServer() {
  if (serverInstance) {
    return serverInstance;
  }
  
  const server = new MCPServerStdio(GRAPHQL_SERVER);
  
  console.log('[GraphQL Agent] Connecting to GraphQL Server...');
  await server.connect();
  
  const tools = await server.listTools();
  console.log(`[GraphQL Agent] Connected with ${tools.length} tools:`, 
    tools.map(t => t.name).join(', '));
  
  serverInstance = server;
  return server;
}

/**
 * Create documentation agent for handoffs
 */
async function createDocumentationAgentForHandoff(conversationId) {
  const documentationAgent = await createDocumentationMCPAgent(
    'GraphQL documentation research and schema analysis',
    conversationId,
    {
      currentTask: 'Providing documentation research support for GraphQL operations',
      graphqlContext: true
    }
  );
  
  // Update the documentation agent's instructions to include GraphQL handoff context
  documentationAgent.instructions += `

## HANDOFF CONTEXT
You are working in a handoff relationship with a GraphQL Agent that needs your documentation research expertise.

When the GraphQL Agent hands off to you:
1. **Research thoroughly** using all your tools (introspect_admin_schema, search_dev_docs, perplexity_research, web_search)
2. **Provide comprehensive findings** including schema details, examples, constraints, and safety considerations
3. **Be specific** about field requirements, data types, and relationships
4. **Include examples** of proper GraphQL syntax when available
5. **Identify risks** or important limitations
6. **Hand back to GraphQL Agent** with complete research summary

Your research will directly inform whether GraphQL operations are safe to execute.`;

  return documentationAgent;
}

/**
 * Safety validation tool - validates GraphQL operations before execution
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
          recommendation: 'Use research_documentation tool to complete missing research.'
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
 * Create a GraphQL-specialized agent with documentation handoff
 */
async function createAgent(task, conversationId, richContext = {}) {
  // Connect to GraphQL server
  const mcpServer = await getGraphQLServer();
  
  // Create documentation agent for handoffs
  const documentationAgent = await createDocumentationAgentForHandoff(conversationId);
  
  // Build system prompt with GraphQL expertise and safety protocols
  let systemPrompt = `You are a GraphQL specialist agent with deep expertise in Shopify Admin API GraphQL operations.

Your task: ${task}

## CRITICAL SAFETY PROTOCOL - HANDOFF WORKFLOW

🚨 **NEVER execute graphql_query or graphql_mutation without completing this handoff workflow:**

1. **ALWAYS** hand off to Documentation Agent first for comprehensive research
2. **WAIT** for Documentation Agent to return with complete findings
3. **VALIDATE** the research before proceeding with GraphQL execution
4. **NEVER** execute operations without proper documentation validation

## Your Handoff & Workflow:

### Step 1: Documentation Research Handoff (REQUIRED)
**Hand off to Documentation Agent** for schema research:
- Provide specific research requirements
- Include operation type (query/mutation) and target objects
- Let Documentation Agent use all research tools comprehensively
- Wait for complete research findings

### Step 2: Safety Validation (REQUIRED)
**validate_operation_safety** - Validate based on documentation research
- Ensures handoff research was comprehensive
- Validates operation structure and safety
- Ensures error handling for mutations
- BLOCKS unsafe operations

### Step 3: GraphQL Execution (Only after handoff + validation)
**graphql_query** - Execute read-only GraphQL queries
**graphql_mutation** - Execute GraphQL mutations (data changes)

## GraphQL Expertise Areas:
- Shopify Admin API schema navigation
- Product, Collection, Order, Customer operations
- Metafield and metaobject management
- Bulk operations and background jobs
- Cost optimization and rate limiting
- Error handling and validation

## Business Context:
- You're working with iDrinkCoffee.com's Shopify store
- All operations affect live production data
- Mutations can cause irreversible changes
- Rate limits and costs apply to all operations

## Safety Rules:
1. **Research First**: Never execute without documentation research
2. **Validate Always**: Use safety validation before execution
3. **Start Small**: Test with single items before bulk operations
4. **Handle Errors**: Always check userErrors in mutation responses
5. **Monitor Costs**: Be aware of GraphQL cost implications
6. **Log Operations**: Document all mutations for audit trail

## Common Patterns You Handle:
- Product CRUD operations
- Collection management and product assignments
- Inventory and pricing updates
- Metafield operations
- Order status changes
- Customer data management

## Error Recovery:
- If documentation research fails, retry with different queries
- If safety validation fails, fix issues before proceeding
- If GraphQL execution fails, analyze userErrors and retry
- Always provide clear error messages and next steps

Remember: Your role is to be the safe, knowledgeable interface to GraphQL operations. The documentation agent is your research partner - use it extensively!`;

  // Add context if provided
  if (richContext) {
    if (richContext.currentTask) {
      systemPrompt += `\n\nCurrent Development Task: ${richContext.currentTask}`;
    }
    if (richContext.recentErrors) {
      systemPrompt += `\n\nRecent Errors to Consider:\n${richContext.recentErrors.join('\n')}`;
    }
  }

  // Add the specific task
  if (task) {
    systemPrompt += `\n\nGraphQL Task: ${task}`;
  }

  // Build final instructions with agency context
  const finalInstructions = await buildAgentInstructions(systemPrompt, {
    agentRole: 'GraphQL specialist',
    conversationId,
    taskDescription: task
  });

  // Create safety validation tool (keep this as a tool)
  const safetyTool = createSafetyValidationTool();

  // Create handoff to documentation agent
  const documentationHandoff = handoff(documentationAgent, {
    name: 'research_with_documentation_agent',
    description: 'Hand off to Documentation Agent for comprehensive GraphQL schema research. Use this BEFORE any GraphQL operation.',
    inputType: DocumentationResearchRequest,
    onHandoff: (context, input) => {
      console.log(`[GraphQL Agent] Handing off to Documentation Agent for: ${input?.research_query}`);
      console.log(`[GraphQL Agent] Operation type: ${input?.operation_type}, Targets: ${input?.target_objects}`);
    }
  });

  // Create the agent with handoffs
  const agent = new Agent({
    name: 'GraphQL Agent',
    instructions: finalInstructions,
    mcpServers: [mcpServer],
    handoffs: [documentationHandoff],
    tools: [safetyTool],
    model: process.env.OPENAI_MODEL || 'gpt-4.1',
    // toolUseBehavior removed to prevent loops
  });

  return agent;
}

/**
 * Execute a GraphQL task with timeout and retry logic
 */
async function executeWithTimeout(agent, task, options = {}) {
  const { run } = await import('@openai/agents');
  const { maxTurns = 15, timeout = 300000, retries = 2 } = options; // 5 minute timeout, 2 retries
  
  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      console.log(`[GraphQL Agent] Attempt ${attempt}/${retries} - Executing task with ${timeout/1000}s timeout...`);
      
      // Create a timeout promise
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => {
          reject(new Error(`GraphQL task execution timed out after ${timeout/1000} seconds`));
        }, timeout);
      });
      
      // Race between the actual execution and timeout
      const executionPromise = run(agent, task, { maxTurns });
      const result = await Promise.race([executionPromise, timeoutPromise]);
      
      console.log('[GraphQL Agent] Task completed successfully');
      
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
      else if (result.state && result.state.currentStep && result.state.currentStep.output) {
        finalOutput = result.state.currentStep.output;
      }
      
      // Log token usage if available
      if (result.state?.context?.usage) {
        const usage = result.state.context.usage;
        console.log(`[GraphQL Agent] Token usage - Input: ${usage.inputTokens}, Output: ${usage.outputTokens}, Total: ${usage.totalTokens}`);
      }
      
      return {
        success: true,
        result: finalOutput || 'GraphQL task completed but no output generated',
        agent: 'graphql',
        tokenUsage: result.state?.context?.usage || null
      };
      
    } catch (error) {
      const isTimeoutError = error.message.includes('timeout') || 
                           error.message.includes('terminated') || 
                           error.message.includes('ECONNRESET');
      
      console.log(`[GraphQL Agent] Attempt ${attempt} failed:`, error.message);
      
      if (isTimeoutError && attempt < retries) {
        const delay = Math.min(2000 * Math.pow(2, attempt - 1), 10000); // Exponential backoff, max 10s
        console.log(`[GraphQL Agent] Network/timeout error, retrying in ${delay}ms...`);
        await new Promise(resolve => setTimeout(resolve, delay));
        continue;
      }
      
      throw error;
    }
  }
}

/**
 * Execute a GraphQL task
 */
export async function executeGraphQLTask(task, conversationId, richContext = {}) {
  try {
    console.log('[GraphQL Agent] Creating agent for task:', task.substring(0, 100) + '...');
    const agent = await createAgent(task, conversationId, richContext);
    
    // Execute with timeout and retry logic
    return await executeWithTimeout(agent, task, {
      maxTurns: 15,
      timeout: 300000, // 5 minutes
      retries: 2
    });
    
  } catch (error) {
    console.error('[GraphQL Agent] Task failed after all retries:', error);
    
    return {
      success: false,
      error: error.message,
      errorType: error.message.includes('timeout') ? 'timeout' : 'execution',
      message: `GraphQL Agent failed: ${error.message}`
    };
  }
}

/**
 * Close the GraphQL MCP server connection
 */
export async function closeGraphQLMCP() {
  if (serverInstance) {
    console.log('[GraphQL Agent] Closing GraphQL MCP server...');
    await serverInstance.close();
    serverInstance = null;
  }
}