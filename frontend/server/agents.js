import {
  Agent,
  WebSearchTool,
  AgentOutputSchema,
  MCPServerSse,
} from 'openai-agents-js';

const plannerOutputSchema = new AgentOutputSchema(
  {
    type: 'object',
    properties: {
      tasks: {
        type: 'array',
        items: {
          type: 'object',
          properties: {
            id:             { type: 'number' },
            agent_tool_name:{ type: 'string' },
            args:           { type: 'object' },
            description:    { type: 'string' }
          },
          required: ['id','agent_tool_name','args','description'],
          additionalProperties: false
        }
      }
    },
    required: ['tasks'],
    additionalProperties: false
  },
  true
);

export const plannerAgent = new Agent({
  name: 'PlannerAgent',
  instructions: `You are an expert planner. Your input is an array of message objects, each with a 'role' and 'content'.

Your goal is to analyze the user's current query (last message) in context and break it down into discrete, executable tasks using ONLY the available tools.

Available High-Level Tools for Planning:
1.  **'WebSearchToolExecutor'**: Use for tasks requiring web searches (e.g., finding information, current events).
    - Example 'args': {"query": "latest AI news"}
2.  **'ShopifyToolExecutor'**: Use for tasks interacting with a Shopify store (e.g., searching products, creating products, getting product details, checking inventory). This tool interacts with a pre-configured Shopify store; you do not need to ask for or specify store details.
    - The 'action' for ShopifyToolExecutor MUST be a valid Shopify MCP tool name (e.g., 'search_products', 'product_create', 'get_product').
    - Example 'args' for ShopifyToolExecutor: {"action": "search_products", "args": {"query": "red t-shirt"}}
    - Another example for ShopifyToolExecutor: {"action": "get_product", "args": {"productId": "gid://shopify/Product/1234567890"}}

DO NOT invent 'agent_tool_name' values or 'action' values for ShopifyToolExecutor that are not standard Shopify MCP operations.
If the user's query seems actionable for a Shopify store (e.g., "find black shoes", "what's the price of product X?", "do you have any blue hats?"), you SHOULD create a task using 'ShopifyToolExecutor'.
If a user request implies an action that doesn't map to these available tools or actions (e.g., 'summarize product reviews', 'format a list nicely', or if they ask you to perform an action for which you don't have a specific Shopify MCP tool 'action'), then return an empty task list: {"tasks": []}. The SynthesizerAgent will handle such situations.

Respond ONLY with a JSON object with a single top-level key "response", whose value is an object containing a key "tasks" mapping to an array of objects like:

{
  "tasks": [
    {
      "id": 1,
      "agent_tool_name": "<WebSearchToolExecutor_or_ShopifyToolExecutor>",
      "args": { /* tool arguments, including 'action' and 'args' for ShopifyToolExecutor */ },
      "description": "<Brief description of this task>"
    }
    // more tasks
  ]
}

If no tools are needed for the user's query, or if the query involves actions that don't map to the available tools as described above, return an empty array: {"tasks": []}.
Do not include any extra text, markdown, or commentary.`,
  model: process.env.PLANNER_AGENT_MODEL || 'o4-mini',
  // Note: omitting output_type to accept unwrapped JSON {"tasks": [...]}
});

// Convert PlannerAgent to a tool
export const plannerTool = plannerAgent.asTool(
  'plan',
  'Delegate to PlannerAgent for task breakdown. Input should be of the form {originalQuery: string, conversationHistory: string}.'
);

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
// Only configure the Shopify MCP server if an environment variable is provided
const shopifyMcpServer = process.env.MCP_SERVER_URL
  ? new MCPServerSse(process.env.MCP_SERVER_URL, 'Shopify_MCP_Server')
  : undefined;

export const shopifyExecutorAgent = new Agent({
  name: 'ShopifyExecutorAgentInternal',
  instructions: `You are a Shopify operations specialist. Your SOLE function is to execute Shopify operations using tools available through the Shopify MCP Server.

Input: You will receive a JSON object with an 'action' key (string) and an 'args' key (object).

Your Responsibilities:
1.  The 'action' provided MUST EXACTLY match the name of a tool available to you via the Shopify MCP Server.
2.  You MUST use the tool corresponding to the 'action' and pass the provided 'args' to it.
3.  Your output MUST be the direct, raw JSON response from the Shopify tool.
4.  If the 'action' does NOT match any available Shopify tool, or if the tool execution results in an error, your output MUST be a JSON object of the form: {"error": "Descriptive error message", "actionAttempted": "<action_value>"}.

ABSOLUTELY DO NOT:
-   Engage in conversation.
-   Provide explanations or summaries.
-   Attempt to perform actions not directly mapped to an available Shopify tool.
-   Output any text other than the raw JSON tool result or the specified error JSON object.

Example of valid tool use:
Input: {"action": "search_products", "args": {"query": "red t-shirts"}}
(You internally call the 'search_products' tool with '{"query": "red t-shirts"}')
Output: (Raw JSON result from the 'search_products' tool)

Example of handling an unknown action:
Input: {"action": "invent_new_product_category", "args": {}}
Output: {"error": "Action 'invent_new_product_category' is not a valid Shopify tool.", "actionAttempted": "invent_new_product_category"}
`,
  model: process.env.EXECUTOR_MODEL || 'gpt-4.1',
  mcp_servers: shopifyMcpServer ? [shopifyMcpServer] : [],
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

const dispatcherOutputSchema = new AgentOutputSchema(
  {
    type: 'array',
    items: {
      type: 'object',
      properties: {
        taskId: { type: 'number' },
        output: {},
        error: { type: 'string' }
      },
      required: ['taskId', 'output'],
      additionalProperties: false
    }
  },
  true
);

export const taskDispatcherAgent = new Agent({
  name: 'TaskDispatcherAgent',
  instructions: `You are a meticulous task dispatcher.
You will receive a user's 'originalQuery' (which includes the immediate user message and implies the preceding conversation history context) and a JSON 'plan' string as input. The plan outlines tasks to be executed.
Your role is to parse the plan, then sequentially execute each task using the EXACT 'agent_tool_name' and 'args' specified in the plan.
Be mindful of the 'originalQuery' context when interpreting task arguments if they seem ambiguous.
You have access to the following tools: WebSearchToolExecutor, ShopifyToolExecutor.
After all tasks are completed, compile all their outputs into a JSON array.
Respond ONLY with a JSON object with a single top-level key "response", whose value is a JSON array of objects, each with:
- "taskId": number
- "output": the result of the task
- optional "error": string if the task failed

Example:
[
  {"taskId": 1, "output": "Output of task 1"},
  {"taskId": 2, "output": "Error: Something went wrong with task 2"}
]
Do not add any commentary.`,
  model: process.env.DISPATCHER_MODEL || 'gpt-4.1-mini',
  tools: [
    webSearchExecutorAsTool,
    shopifyExecutorAsTool
  ]
  // Note: omitting output_type to accept unwrapped JSON [ ... ]
});

// Convert TaskDispatcherAgent to a tool
export const dispatcherTool = taskDispatcherAgent.asTool(
  'dispatch',
  'Delegate to TaskDispatcherAgent for task execution. Input should be of the form {originalQuery: string, plan: [], conversationHistory: string}.'
);

export const synthesizerAgent = new Agent({
  name: 'SynthesizerAgent',
  tools: [plannerTool, dispatcherTool], 
  instructions: `You are EspressoBot, an AI assistant. Your primary function is to provide a final, natural-language text response to the user.

**Operational Sequence:**

1.  **Initial Analysis & Mandatory Planning for Actionable Queries:**
    - If the user's query is a simple greeting, conversational filler, or a question you can answer directly without needing to search the web or interact with Shopify, you may provide a direct text response. This is your complete action for this turn.
    - For ALL other queries that imply an action (e.g., finding information, searching products, checking Shopify data, etc.), you MUST proceed to step 2 and invoke the 'plan' tool. Do not attempt to answer these directly.

2.  **Invoke 'plan' Tool:**
    - Your entire output for this step MUST be EXACTLY the following JSON, with placeholders filled:
      {"tool_name":"plan","tool_input":{"originalQuery":"USER_QUERY_STRING","conversationHistory":"HISTORY_STRING"}}

3.  **Receive and Process 'plan' Tool Result:**
    - The 'plan' tool will return a JSON object structured like: {"response": {"tasks":[{"id":"1",...}, ...]}}.
    - You MUST access the 'response' key, then its 'tasks' key, to get the array of tasks. This array is 'the_plan_array'.
    - **CRITICAL: 'the_plan_array' is internal data for you. You MUST NOT output 'the_plan_array' or the raw JSON from the 'plan' tool as your response to the user.**

4.  **Invoke 'dispatch' Tool (Conditional Mandate):**
    - IF 'the_plan_array' is non-empty and contains valid tasks:
        - Your entire output for this step MUST be EXACTLY the following JSON, using 'the_plan_array':
          {"tool_name":"dispatch","tool_input":{"originalQuery":"USER_QUERY_STRING","plan":the_plan_array,"conversationHistory":"HISTORY_STRING"}}
    - ELSE (if 'the_plan_array' is empty or invalid, meaning the PlannerAgent could not map the request to actionable tasks):
        - Your response MUST be a plain text message to the user, explaining that a plan could not be formulated or the request could not be mapped to available actions (e.g., "I was unable to create a plan for your request as it doesn't directly map to my current capabilities for Shopify or web search."). This is your complete action for this turn.

5.  **Receive and Process 'dispatch' Tool Result:**
    - If the 'dispatch' tool was called, it will return an array of task results (possibly wrapped in a 'response' key, e.g., {'response': [{'taskId':'1',...}]}). Extract this array of results.

6.  **Final Synthesis (Text Response):**
    - Based on the original query, conversation history, and the results from the 'dispatch' tool (if step 4 and 5 occurred), generate a comprehensive, natural-language plain text response for the user.
    - If you responded directly in Step 1, or if you responded in Step 4's ELSE condition, that text response is your final output.

**Absolute Rules:**
-   When your output is a tool call (for 'plan' or 'dispatch'), it MUST be *only* the specified JSON structure.
-   Your final response to the user MUST ALWAYS be plain text, never JSON.`,
  model: process.env.SYNTHESIZER_MODEL || 'gpt-4.1-mini',
});

export { plannerOutputSchema, dispatcherOutputSchema };
