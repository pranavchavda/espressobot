import { Agent, run, tool } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { memoryStore } from './memory-store-db.js';
import { generateEmbedding } from './memory-embeddings.js';
import { z } from 'zod';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Memory detection patterns
const MEMORY_PATTERNS = {
  preference: {
    keywords: ['prefer', 'like', 'want', 'wish', 'favorite', 'always', 'usually', 'typically'],
    importance: 'high'
  },
  configuration: {
    keywords: ['store name', 'domain', 'theme', 'settings', 'configuration', 'setup'],
    importance: 'high'
  },
  workflow: {
    keywords: ['workflow', 'process', 'steps', 'procedure', 'routine', 'regularly'],
    importance: 'medium'
  },
  constraint: {
    keywords: ['cannot', 'must not', 'should not', 'limitation', 'restriction', 'avoid'],
    importance: 'high'
  },
  context: {
    keywords: ['business', 'company', 'brand', 'product line', 'target audience'],
    importance: 'medium'
  }
};

// Store global context for tool execution
let globalUserId = 1;
let globalConversationId = null;

// Create memory tool for the agent
const createMemoryTool = tool({
  name: 'create_memory',
  description: 'Save important information about the user or their preferences for future reference',
  parameters: z.object({
    content: z.string().describe('The information to remember'),
    category: z.enum(['preference', 'configuration', 'workflow', 'constraint', 'context', 'general']).describe('The category of information'),
    importance: z.enum(['high', 'medium', 'low']).describe('How important this information is')
  }),
  execute: async ({ content, category, importance }) => {
    try {
      // Generate embedding for the memory (uses local or OpenAI based on config)
      const embedding = await generateEmbedding(content);
      
      if (!embedding) {
        console.error('Failed to generate embedding for memory');
        // Still save the memory without embedding
      }
      
      const memory = await memoryStore.createMemory(
        globalUserId,
        content,
        {
          category,
          importance,
          embedding,
          embedding_model: process.env.USE_LOCAL_EMBEDDINGS === 'true' 
            ? (process.env.LOCAL_EMBEDDING_MODEL || 'local')
            : 'text-embedding-3-small',
          source: 'memory_agent',
          conversation_id: globalConversationId
        }
      );
      
      return `Memory saved: ${memory.id}`;
    } catch (error) {
      console.error('Error creating memory:', error);
      return 'Failed to save memory';
    }
  }
});

// Memory agent that analyzes conversations and extracts important information
export const memoryAgent = new Agent({
  name: 'MemoryAgent',
  instructions: `You are a memory extraction specialist. Your job is to analyze conversations and identify important information that should be remembered for future interactions.

Focus on extracting:
1. User preferences (UI, workflows, communication style)
2. Store configuration details (theme, domain, settings)
3. Common workflows or procedures the user follows
4. Business context (products, target audience, brand identity)
5. Technical constraints or limitations

Rules:
- Only save information that would be useful in future conversations
- Avoid saving temporary or transaction-specific details
- Deduplicate similar memories
- Categorize memories appropriately
- Assign importance based on how likely it is to be needed again
- Extract ONLY the most important 3-5 memories per conversation to avoid overload

When you identify something worth remembering, use the create_memory tool.`,
  model: process.env.OPENAI_MODEL || 'gpt-4.1-mini',
  modelSettings: { 
    temperature: 0.3, // Lower temperature for more consistent extraction
    parallelToolCalls: false,
    maxOutputTokens: 2000 // Limit response size
  },
  tools: [createMemoryTool]
});

// Function to analyze a message for memory-worthy content
export async function analyzeForMemories(message, userId = 1, conversationId = null) {
  try {
    // Set global context for tool execution
    globalUserId = userId;
    globalConversationId = conversationId;
    
    // Quick pattern matching to see if message might contain memorable info
    const lowerMessage = message.toLowerCase();
    let hasMemoryPattern = false;
    
    for (const [category, config] of Object.entries(MEMORY_PATTERNS)) {
      if (config.keywords.some(keyword => lowerMessage.includes(keyword))) {
        hasMemoryPattern = true;
        break;
      }
    }
    
    // Skip if no patterns found (optimization)
    if (!hasMemoryPattern && message.length < 50) {
      return null;
    }
    
    // Run the memory agent
    const result = await run(memoryAgent, `
Analyze this message for important information to remember:

"${message}"

Extract any preferences, configurations, workflows, constraints, or business context that should be remembered for future conversations.
    `, { maxTurns: 30 });
    
    return result;
  } catch (error) {
    console.error('Error analyzing for memories:', error);
    return null;
  }
}

// Function to run memory agent in parallel with main conversation
export async function runMemoryExtraction(conversationHistory, userId = 1, conversationId = null) {
  try {
    // Set global context for tool execution
    globalUserId = userId;
    globalConversationId = conversationId;
    
    // Format conversation history for analysis
    const formattedHistory = conversationHistory
      .map(msg => `${msg.role}: ${msg.content}`)
      .join('\n\n');
    
    const prompt = `
Analyze this conversation and extract all important information that should be remembered:

${formattedHistory}

Focus on:
- User preferences and habits
- Store/business configuration
- Workflows and procedures
- Constraints and limitations
- Business context

For each piece of important information, use the create_memory tool.
IMPORTANT: Extract only the 3-5 most important memories to avoid overload.
`;

    // Create a timeout promise
    const timeoutPromise = new Promise((_, reject) => {
      setTimeout(() => reject(new Error('Memory extraction timeout')), 25000);
    });
    
    // Race between memory extraction and timeout
    const result = await Promise.race([
      run(memoryAgent, prompt, { maxTurns: 30 }),
      timeoutPromise
    ]);
    
    console.log('Memory extraction completed');
    
    // Prune memories if needed
    await memoryStore.pruneMemories(userId);
    
    return result;
  } catch (error) {
    if (error.message === 'Memory extraction timeout') {
      console.error('Memory extraction timed out after 25 seconds');
    } else {
      console.error('Error in memory extraction:', error);
    }
    return null;
  }
}