import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

/**
 * Configuration for conversation summarization
 */
export const SUMMARIZATION_CONFIG = {
  CHUNK_SIZE: 8,  // Summarize every 8 turns
  MAX_SUMMARY_LENGTH: 1000,  // Maximum characters per summary
  MODEL: 'gpt-4.1-mini',  // Fast model for summarization
};

/**
 * Summarizes a chunk of conversation history
 * @param {Array} messages - Array of message objects with role and content
 * @param {Object} options - Additional options for summarization
 * @returns {Promise<string>} - Summarized conversation
 */
export async function summarizeConversationChunk(messages, options = {}) {
  const { 
    previousSummary = null,
    includeActionItems = true,
    includeKeyDecisions = true 
  } = options;

  // Format messages for summarization
  const conversationText = messages.map(msg => 
    `${msg.role === 'user' ? 'User' : 'Assistant'}: ${msg.content}`
  ).join('\n\n');

  // Build the summarization prompt
  let prompt = `Summarize the following conversation concisely, focusing on:
- Key topics discussed
- Important decisions made
- Actions taken or planned
${includeActionItems ? '- Action items and tasks' : ''}
${includeKeyDecisions ? '- Key product/business decisions' : ''}

Keep the summary under ${SUMMARIZATION_CONFIG.MAX_SUMMARY_LENGTH} characters.
Focus on factual information that would be needed for context in future messages.

${previousSummary ? `Previous conversation summary:\n${previousSummary}\n\n` : ''}

Current conversation to summarize:
${conversationText}

Summary:`;

  try {
    const response = await openai.chat.completions.create({
      model: SUMMARIZATION_CONFIG.MODEL,
      messages: [
        {
          role: 'system',
          content: 'You are a conversation summarizer for an e-commerce assistant. Create concise, factual summaries that preserve important context for future interactions.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.3,  // Lower temperature for consistent summaries
      max_tokens: 500,
    });

    const summary = response.choices[0]?.message?.content?.trim();
    
    if (!summary) {
      throw new Error('No summary generated');
    }

    // Ensure summary doesn't exceed max length
    if (summary.length > SUMMARIZATION_CONFIG.MAX_SUMMARY_LENGTH) {
      return summary.substring(0, SUMMARIZATION_CONFIG.MAX_SUMMARY_LENGTH - 3) + '...';
    }

    return summary;
  } catch (error) {
    console.error('[Summarizer] Error summarizing conversation:', error);
    // Return a basic summary on error
    return `Conversation covering ${messages.length} messages about: ${messages[0]?.content?.substring(0, 100)}...`;
  }
}

/**
 * Combines multiple summaries into a higher-level summary
 * @param {Array<string>} summaries - Array of conversation summaries
 * @returns {Promise<string>} - Combined summary
 */
export async function combineSummaries(summaries) {
  if (summaries.length === 0) return '';
  if (summaries.length === 1) return summaries[0];

  const combinedText = summaries.map((summary, index) => 
    `Summary ${index + 1}:\n${summary}`
  ).join('\n\n');

  const prompt = `Combine these conversation summaries into a single cohesive summary.
Focus on the overall narrative and key outcomes.
Remove redundancy while preserving all important information.
Keep under ${SUMMARIZATION_CONFIG.MAX_SUMMARY_LENGTH} characters.

${combinedText}

Combined summary:`;

  try {
    const response = await openai.chat.completions.create({
      model: SUMMARIZATION_CONFIG.MODEL,
      messages: [
        {
          role: 'system',
          content: 'You are a conversation summarizer. Combine multiple summaries into a coherent overview.'
        },
        {
          role: 'user',
          content: prompt
        }
      ],
      temperature: 0.3,
      max_tokens: 500,
    });

    const summary = response.choices[0]?.message?.content?.trim();
    
    if (!summary) {
      throw new Error('No combined summary generated');
    }

    return summary.length > SUMMARIZATION_CONFIG.MAX_SUMMARY_LENGTH
      ? summary.substring(0, SUMMARIZATION_CONFIG.MAX_SUMMARY_LENGTH - 3) + '...'
      : summary;
  } catch (error) {
    console.error('[Summarizer] Error combining summaries:', error);
    // Return first summary as fallback
    return summaries[0];
  }
}

/**
 * Determines if a conversation needs summarization based on message count
 * @param {number} messageCount - Total number of messages in conversation
 * @param {number} lastSummarizedAt - Message count when last summarized
 * @returns {boolean} - Whether summarization is needed
 */
export function needsSummarization(messageCount, lastSummarizedAt = 0) {
  const messagesSinceLastSummary = messageCount - lastSummarizedAt;
  return messagesSinceLastSummary >= SUMMARIZATION_CONFIG.CHUNK_SIZE;
}

/**
 * Gets the messages that need to be summarized
 * @param {Array} allMessages - All conversation messages
 * @param {number} lastSummarizedAt - Index of last summarized message
 * @returns {Array} - Messages to summarize
 */
export function getMessagesToSummarize(allMessages, lastSummarizedAt = 0) {
  const chunks = [];
  let currentIndex = lastSummarizedAt;

  while (currentIndex + SUMMARIZATION_CONFIG.CHUNK_SIZE <= allMessages.length) {
    chunks.push({
      messages: allMessages.slice(currentIndex, currentIndex + SUMMARIZATION_CONFIG.CHUNK_SIZE),
      startIndex: currentIndex,
      endIndex: currentIndex + SUMMARIZATION_CONFIG.CHUNK_SIZE
    });
    currentIndex += SUMMARIZATION_CONFIG.CHUNK_SIZE;
  }

  return chunks;
}