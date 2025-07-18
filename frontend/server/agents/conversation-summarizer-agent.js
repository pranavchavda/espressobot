import { Agent, run, tool } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { z } from 'zod';
import { initializeTracing } from '../config/tracing-config.js';

// Initialize tracing configuration for this agent
initializeTracing('Conversation Summarizer Agent');

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

/**
 * Configuration for conversation summarization
 */
export const SUMMARIZATION_CONFIG = {
  TURNS_PER_CHUNK: 8,  // Summarize every 8 turns (4 user + 4 assistant)
  MAX_SUMMARY_LENGTH: 1000,  // Maximum characters per summary
  MODEL: 'gpt-4.1-mini',  // Fast model for summarization
};

/**
 * Creates a conversation summarizer agent
 */
export function createConversationSummarizerAgent() {
  return new Agent({
    name: 'ConversationSummarizer',
    model: SUMMARIZATION_CONFIG.MODEL,
    instructions: `You are a conversation summarizer for an e-commerce assistant. Your job is to create concise, factual summaries that preserve important context for future interactions.

When summarizing conversations:
1. Focus on key topics, decisions, and actions taken
2. Preserve specific product names, SKUs, and prices mentioned
3. Note any unresolved issues or pending tasks
4. Keep summaries under ${SUMMARIZATION_CONFIG.MAX_SUMMARY_LENGTH} characters
5. Use clear, factual language without interpretation

For recursive summaries (summary of summaries):
- Maintain chronological flow
- Remove redundancy while preserving all key information
- Focus on the overall narrative and outcomes`,
    
    tools: [
      tool({
        name: 'create_summary',
        description: 'Create a summary of the provided conversation or summaries',
        parameters: z.object({
          summary: z.string().describe('The generated summary'),
          key_points: z.array(z.string()).describe('Key points extracted from the conversation'),
          pending_items: z.array(z.string()).nullable().default(null).describe('Any unresolved issues or pending tasks')
        }),
        execute: async ({ summary, key_points, pending_items }) => {
          return {
            summary,
            key_points,
            pending_items: pending_items || [],
            length: summary.length
          };
        }
      })
    ]
  });
}

/**
 * Summarizes a chunk of conversation messages
 */
export async function summarizeConversationChunk(messages, previousSummary = null) {
  const agent = createConversationSummarizerAgent();
  
  // Format messages for summarization
  const conversationText = messages.map((msg, index) => 
    `[Message ${index + 1}] ${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`
  ).join('\n\n');

  const prompt = `${previousSummary ? `Previous conversation summary:\n${previousSummary}\n\n` : ''}Please summarize the following conversation chunk:

${conversationText}

Create a concise summary focusing on key business decisions, product interactions, and any pending tasks.`;

  try {
    const result = await run(agent, prompt, { maxTurns: 2 }); // Allow one turn for tool call
    
    // Check if the result is the structured output from the tool
    if (result.finalOutput) {
      console.log('[DEBUG] Result finalOutput type:', typeof result.finalOutput);
      console.log('[DEBUG] Result finalOutput:', result.finalOutput);
      
      // If finalOutput is a string, it means the agent didn't use the tool
      if (typeof result.finalOutput === 'string') {
        return {
          summary: result.finalOutput,
          keyPoints: [],
          pendingItems: []
        };
      }
      
      // Otherwise, the finalOutput should be the return value from our tool
      return result.finalOutput;
    }
    
    // Fallback if structured output fails
    return {
      summary: `Conversation chunk containing ${messages.length} messages`,
      keyPoints: [],
      pendingItems: []
    };
  } catch (error) {
    console.error('[SummarizerAgent] Error summarizing conversation:', error);
    return {
      summary: `Conversation chunk containing ${messages.length} messages`,
      keyPoints: [],
      pendingItems: []
    };
  }
}

/**
 * Combines multiple summaries into a higher-level summary
 */
export async function combineSummaries(summaries) {
  if (summaries.length === 0) return null;
  if (summaries.length === 1) return summaries[0];

  const agent = createConversationSummarizerAgent();
  
  const summariesText = summaries.map((summary, index) => 
    `[Summary ${index + 1}]:\n${summary.summary}\nKey points: ${summary.keyPoints?.join(', ') || 'None'}`
  ).join('\n\n');

  const prompt = `Please combine these conversation summaries into a single cohesive summary:

${summariesText}

Create a unified summary that maintains chronological flow and removes redundancy while preserving all important information.`;

  try {
    const result = await run(agent, prompt, { maxTurns: 2 }); // Allow one turn for tool call
    
    // Check if the result is the structured output from the tool
    if (result.finalOutput) {
      // If finalOutput is a string, it means the agent didn't use the tool
      if (typeof result.finalOutput === 'string') {
        return {
          summary: result.finalOutput,
          keyPoints: [],
          pendingItems: []
        };
      }
      
      return result.finalOutput;
    }
    
    return summaries[0]; // Fallback to first summary
  } catch (error) {
    console.error('[SummarizerAgent] Error combining summaries:', error);
    return summaries[0];
  }
}

/**
 * Builds compressed conversation context using summaries
 */
export async function buildCompressedContext(messages, options = {}) {
  const { maxRecentTurns = 8 } = options;
  
  // If conversation is short, no compression needed
  if (messages.length <= maxRecentTurns) {
    return {
      summaries: [],
      recentMessages: messages,
      totalMessages: messages.length
    };
  }

  // Calculate how many messages need summarization
  const messagesNeedingSummary = messages.length - maxRecentTurns;
  const chunksNeeded = Math.ceil(messagesNeedingSummary / SUMMARIZATION_CONFIG.TURNS_PER_CHUNK);
  
  console.log(`[SummarizerAgent] Processing ${messages.length} messages: ${chunksNeeded} chunks to summarize, ${maxRecentTurns} recent messages`);

  const summaries = [];
  let currentIndex = 0;

  // Process messages in chunks
  for (let i = 0; i < chunksNeeded; i++) {
    const chunkEnd = Math.min(
      currentIndex + SUMMARIZATION_CONFIG.TURNS_PER_CHUNK,
      messages.length - maxRecentTurns
    );
    
    const chunk = messages.slice(currentIndex, chunkEnd);
    console.log(`[SummarizerAgent] Summarizing chunk ${i + 1}: messages ${currentIndex + 1}-${chunkEnd}`);
    
    const previousSummary = summaries.length > 0 ? summaries[summaries.length - 1].summary : null;
    const chunkSummary = await summarizeConversationChunk(chunk, previousSummary);
    
    summaries.push({
      ...chunkSummary,
      startIndex: currentIndex,
      endIndex: chunkEnd,
      chunkNumber: i + 1
    });
    
    currentIndex = chunkEnd;
  }

  // If we have multiple summaries, combine them
  let finalSummary = null;
  if (summaries.length > 1) {
    console.log(`[SummarizerAgent] Combining ${summaries.length} summaries into final summary`);
    finalSummary = await combineSummaries(summaries);
  } else if (summaries.length === 1) {
    finalSummary = summaries[0];
  }

  // Get recent messages that won't be summarized
  const recentMessages = messages.slice(-maxRecentTurns);

  return {
    summaries,
    finalSummary,
    recentMessages,
    totalMessages: messages.length,
    summarizedCount: messagesNeedingSummary
  };
}