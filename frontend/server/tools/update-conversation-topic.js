/**
 * Tool for updating conversation topic
 * Allows agents to set or update the topic title and details for a conversation
 */

import pkg from '@prisma/client';
const { PrismaClient } = pkg;

const prisma = new PrismaClient();

/**
 * Updates the topic for a conversation
 * @param {Object} params - Parameters for updating topic
 * @param {string} params.conversation_id - The conversation ID
 * @param {string} params.topic_title - Concise topic title (max 200 chars)
 * @param {string} params.topic_details - Detailed topic description
 * @returns {Object} Result of the operation
 */
export async function updateConversationTopic({ conversation_id, topic_title, topic_details }) {
  try {
    // Validate inputs
    if (!conversation_id) {
      return { 
        success: false, 
        error: 'conversation_id is required' 
      };
    }

    if (!topic_title || topic_title.trim().length === 0) {
      return { 
        success: false, 
        error: 'topic_title is required and cannot be empty' 
      };
    }

    // Truncate title if too long
    const truncatedTitle = topic_title.substring(0, 200);

    // Update the conversation
    const updated = await prisma.conversations.update({
      where: { id: parseInt(conversation_id) },
      data: {
        topic_title: truncatedTitle,
        topic_details: topic_details || null,
        updated_at: new Date()
      }
    });

    // Emit SSE event if available
    if (global.currentSseEmitter) {
      global.currentSseEmitter('topic_updated', {
        conversation_id: updated.id,
        topic_title: updated.topic_title,
        topic_details: updated.topic_details
      });
    }

    return {
      success: true,
      message: 'Topic updated successfully',
      conversation_id: updated.id,
      topic_title: updated.topic_title,
      topic_details: updated.topic_details
    };

  } catch (error) {
    console.error('Error updating conversation topic:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Tool definition for agents
export const updateConversationTopicTool = {
  name: 'update_conversation_topic',
  description: 'Update the topic title and details for the current conversation. Use this to set a clear, concise topic that summarizes what the conversation is about.',
  input_schema: {
    type: 'object',
    properties: {
      conversation_id: {
        type: 'string',
        description: 'The ID of the conversation to update'
      },
      topic_title: {
        type: 'string',
        description: 'A concise topic title (max 200 characters) that summarizes the conversation'
      },
      topic_details: {
        type: 'string',
        description: 'Optional detailed description of the topic, including key context, goals, or important information'
      }
    },
    required: ['conversation_id', 'topic_title']
  }
};

// Export for use in orchestrators
export default updateConversationTopic;