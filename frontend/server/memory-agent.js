import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { memoryStore } from './memory-store.js';
import OpenAI from 'openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

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

// Create memory tool for the agent
const createMemoryTool = {
  name: 'create_memory',
  description: 'Save important information about the user or their preferences for future reference',
  execute: async ({ content, category, importance }) => {
    try {
      // Generate embedding for the memory
      const embeddingResponse = await openai.embeddings.create({
        model: 'text-embedding-3-small',
        input: content,
      });
      
      const embedding = embeddingResponse.data[0].embedding;
      
      const memory = memoryStore.createMemory(
        1, // Default user ID - should be passed from context
        content,
        {
          category,
          importance,
          embedding,
          source: 'memory_agent'
        }
      );
      
      return `Memory saved: ${memory.id}`;
    } catch (error) {
      console.error('Error creating memory:', error);
      return 'Failed to save memory';
    }
  },
  parameters: {
    type: 'object',
    properties: {
      content: {
        type: 'string',
        description: 'The information to remember'
      },
      category: {
        type: 'string',
        enum: ['preference', 'configuration', 'workflow', 'constraint', 'context', 'general'],
        description: 'The category of information'
      },
      importance: {
        type: 'string',
        enum: ['high', 'medium', 'low'],
        description: 'How important this information is'
      }
    },
    required: ['content', 'category', 'importance']
  }
};

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

When you identify something worth remembering, use the create_memory tool.`,
  model: process.env.OPENAI_MODEL || 'gpt-4o-mini',
  modelSettings: { 
    temperature: 0.3, // Lower temperature for more consistent extraction
    parallelToolCalls: false
  },
  tools: [createMemoryTool]
});

// Function to analyze a message for memory-worthy content
export async function analyzeForMemories(message, userId = 1, conversationId = null) {
  try {
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
    const result = await memoryAgent.run(`
Analyze this message for important information to remember:

"${message}"

Extract any preferences, configurations, workflows, constraints, or business context that should be remembered for future conversations.
    `);
    
    return result;
  } catch (error) {
    console.error('Error analyzing for memories:', error);
    return null;
  }
}

// Function to run memory agent in parallel with main conversation
export async function runMemoryExtraction(conversationHistory, userId = 1, conversationId = null) {
  try {
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
`;

    const result = await memoryAgent.run(prompt);
    console.log('Memory extraction completed');
    
    // Prune memories if needed
    memoryStore.pruneMemories(userId);
    
    return result;
  } catch (error) {
    console.error('Error in memory extraction:', error);
    return null;
  }
}