import { Agent, WebSearchTool } from 'openai-agents-js';
// Attempting direct import for MCPServerSse and AgentOutputSchema, adjust if SDK exports them differently
// e.g., from 'openai-agents-js/dist/mcp' or 'openai-agents-js/dist/agent-outputs'
import { MCPServerSse } from 'openai-agents-js/dist/mcp'; 
import { AgentOutputSchema } from 'openai-agents-js/dist/agent-outputs';

// --- 1. Planner Agent ---
const plannerOutputSchema = new AgentOutputSchema({
  name: 'PlannerOutput',
  description: 'A JSON object containing a list of tasks to be executed.',
  // If the SDK supports detailed JSON schema for output_type, define it here.
  // For now, instructions will guide the JSON format.
  // Example structure: { tasks: Array<{ id: number; agent_tool_name: string; args: Record<string, any>; description: string }> }
});

export const plannerAgent = new Agent({
  name: 'PlannerAgent',
  instructions: `You are an expert planner. Your goal is to break down a user's request (and conversation history if provided) into a sequence of discrete, executable tasks.
Respond ONLY with a JSON object of the form:
{
  "tasks": [
    {
      "id": 1,
      "agent_tool_name": "<NameOfTheExecutorToolToCall>",
      "args": { /* arguments for the tool */ },
      "description": "<Brief description of this task's goal>"
    }
    // ... more tasks
  ]
}
Available Executor Tools (agent_tool_name):
- "WebSearchToolExecutor": Use for general web searches and information retrieval. Args example: { "query": "latest AI news" }
- "ShopifyToolExecutor": Use for all Shopify related operations like finding products, updating inventory, creating orders etc. Args example: { "action": "search_products", "query": "red t-shirts" }
Do not include any additional commentary, markdown, or text beyond this JSON structure.
The 'id' should be sequential starting from 1.
The 'description' should be a concise summary of what the task aims to achieve.`, 
  model: process.env.PLANNER_AGENT_MODEL || 'o4-mini',
  // output_type: plannerOutputSchema, // Uncomment if SDK properly supports and uses this for validation
});

// --- 2. Executor Agents ---

// WebSearchExecutorAgent
export const webSearchExecutorAgent = new Agent({
  name: 'WebSearchExecutorAgentInternal',
  instructions: 'You are a web search specialist. Execute the web search task precisely based on the provided query and return the result.',
  model: process.env.EXECUTOR_MODEL || 'gpt-4.1',
  tools: [
    new WebSearchTool({
      search_context_size: 'medium',
    }),
  ],
  tool_use_behavior: 'stop_on_first_tool',
});

// ShopifyExecutorAgent
const shopifyMcpServer = new MCPServerSse(
  process.env.MCP_SERVER_URL || 'https://webhook-listener-pranavchavda.replit.app/mcp',
  'Shopify_MCP_Server'
);

export const shopifyExecutorAgent = new Agent({
  name: 'ShopifyExecutorAgentInternal',
  instructions: `You are a Shopify operations specialist. You will be given an action and arguments.
Use your available Shopify tools to perform the requested Shopify operation and return its result.
For example, if the input is '{"action": "search_products", "query": "red t-shirts"}', you should use the 'search_products' tool with the query 'red t-shirts'.`, 
  model: process.env.EXECUTOR_MODEL || 'gpt-4.1',
  mcp_servers: [shopifyMcpServer],
});


// --- 3. Task Dispatcher Agent ---
const webSearchExecutorAsTool = webSearchExecutorAgent.asTool(
  'WebSearchToolExecutor',
  'Performs a web search. Input should be an object like {"query": "search terms"}. Returns search results.'
);

const shopifyExecutorAsTool = shopifyExecutorAgent.asTool(
  'ShopifyToolExecutor',
  'Performs Shopify operations. Input should be an object like {"action": "tool_to_call_on_shopify_mcp", ...args}. Returns the result of the Shopify operation.'
);

export const taskDispatcherAgent = new Agent({
  name: 'TaskDispatcherAgent',
  instructions: `You are a meticulous task dispatcher.
You will receive a user's original query and a JSON plan string as input. The plan outlines tasks to be executed.
Your role is to parse the plan, then sequentially execute each task using the EXACT 'agent_tool_name' and 'args' specified in the plan.
You have access to the following tools: WebSearchToolExecutor, ShopifyToolExecutor.
After all tasks are completed, compile all their outputs into a JSON array string.
Respond ONLY with this JSON array string, mapping task ID to its output. Example:
[
  {"taskId": 1, "output": "Output of task 1"},
  {"taskId": 2, "output": "Error: Something went wrong with task 2"}
]
Do not add any commentary. If a tool call results in an error, include the error message as its output.`, 
  model: process.env.DISPATCHER_MODEL || 'gpt-4.1-mini',
  tools: [
    webSearchExecutorAsTool,
    shopifyExecutorAsTool,
  ],
});


// --- 4. Synthesizer Agent ---
export const synthesizerAgent = new Agent({
  name: 'SynthesizerAgent',
  instructions: `You are a helpful AI assistant.
You will receive the user's original query and a JSON string representing an array of task results (from the TaskDispatcherAgent).
Your goal is to synthesize this information into a single, coherent, and user-friendly natural language response.
Address the user's original query directly.
If some tasks resulted in errors, acknowledge them gracefully if relevant to the user's query, but focus on providing a helpful answer based on successful tasks.
Stream your response back to the user. Do not use markdown for your final response unless specifically part of the content (e.g. code block).`, 
  model: process.env.SYNTHESIZER_MODEL || 'gpt-4.1-mini',
});
