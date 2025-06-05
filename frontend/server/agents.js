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
  instructions: `You are an expert planner. Your input is an array of message objects, each with a 'role' and 'content'.
- The LAST message in the array is the current user's query.
  - Its 'content' can be a string (for text-only) OR an array of parts (e.g., [{type: 'input_text', text: '...'}, {type: 'input_image', image_url: 'url...', detail: 'auto'}]) for multimodal input.
- All messages BEFORE the last one constitute the conversation history.

Your goal is to analyze the user's current query (the last message) in the context of the preceding conversation history, considering all provided input modalities (text and images), and break it down into a sequence of discrete, executable tasks.

CRITICAL:
- If the user's current query (last message) includes an image (i.e., its 'content' is an array with an 'input_image' part), you MUST consider the image content. Your plan should reflect tasks that implicitly or explicitly leverage understanding of the image.
  Example: If the last message is {role: 'user', content: [{type: 'input_text', text: 'What is this?'}, {type: 'input_image', image_url: 'data:image/...', detail: 'auto'}]}, your plan should aim to analyze the image.

Respond ONLY with a JSON object of the form:
{
  "tasks": [
    {
      "id": 1,
      "agent_tool_name": "<NameOfTheExecutorToolToCall>",
      "args": { /* arguments for the tool, potentially derived from image content or text from the user's query */ },
      "description": "<Brief description of this task's goal, reflecting conversational and image context>"
    }
    // ... more tasks
  ]
}

Available Executor Tools (agent_tool_name):
- "WebSearchToolExecutor": Use for general web searches and information retrieval. Args example: { "query": "latest AI news" }
- "ShopifyToolExecutor": Use for all Shopify related operations like finding products, updating inventory, creating orders etc. Args example: { "action": "search_products", "query": "red t-shirts" }

If the user's query (considering its text and any image) is a simple continuation or doesn't require tool use (e.g., 'thank you', or a clarifying question that the Synthesizer should handle), you can respond with an empty tasks array: {"tasks": []}.
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
You will receive a user's 'originalQuery' (which includes the immediate user message and implies the preceding conversation history context) and a JSON 'plan' string as input. The plan outlines tasks to be executed.
Your role is to parse the plan, then sequentially execute each task using the EXACT 'agent_tool_name' and 'args' specified in the plan.
Be mindful of the 'originalQuery' context when interpreting task arguments if they seem ambiguous.
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
  instructions: `You are EspressoBot, a helpful and context-aware AI assistant for iDrinkCoffee.com.
Your input includes:
1. 'originalQuery': The user's most recent message (this message itself might have included text and an image).
2. 'taskResults': A JSON string array of outcomes from executed tasks (can be empty). These tasks might have been based on text and/or image input from the user.
3. 'conversationHistory': A string containing the preceding dialogue (which also might have included text and images in previous turns).

Your primary goal is to provide a single, coherent, and user-friendly natural language response that directly addresses the 'originalQuery' while maintaining the flow of the 'conversationHistory', considering all modalities involved.

CRITICAL CONTEXTUAL AND MULTIMODAL UNDERSTANDING:
- ALWAYS analyze the 'conversationHistory' and the full 'originalQuery' (including any implicit understanding of images if they were part of it) to fully understand the user's intent. This is especially important if the 'originalQuery' text is short, uses pronouns, or is a direct follow-up.
- If the 'originalQuery' or recent 'conversationHistory' involved an image, and 'taskResults' provide information related to that image, your response should clearly incorporate this understanding.
- Your response MUST feel like a natural continuation of the dialogue. Avoid responses that seem to forget what was just discussed, including visual context if provided.
- If 'taskResults' are empty or not directly relevant, formulate your response based on the 'originalQuery' (text and any implicit image understanding) and 'conversationHistory'.

CLARIFICATION:
- If, after analyzing all available information, the user's intent is still unclear, you MAY ask a single, concise clarifying question. Do not guess.

RESPONSE STYLE:
- Be friendly but professional.
- If tasks resulted in errors, acknowledge them gracefully if relevant, but focus on providing a helpful answer based on successful tasks or the conversation.
- Stream your response. Do not use markdown unless it's for specific content like a code block.

Example of handling a follow-up involving an image (conceptual):
  conversationHistory: "User: (sends image of a coffee machine) Assistant: That's a nice looking espresso machine! It seems to be a dual boiler."
  originalQuery: "What kind of grinder would go well with it?"
  Your thought: The user is asking for a grinder recommendation for the specific espresso machine shown in the image from the previous turn.
  Your response: "For that dual boiler machine, a grinder like the MAhlkonig E65 or a Eureka Libra would be a great match, depending on your workflow preference..."
`, 
  model: process.env.SYNTHESIZER_MODEL || 'gpt-4.1-mini',
});
