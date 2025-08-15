/**
 * Conversation Cleanup Utility
 * 
 * Prevents database growth and context explosion by cleaning up old conversation data
 */

import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

/**
 * Clean up old conversation messages to prevent database bloat
 * @param {number} daysOld - Delete messages older than this many days (default: 30)
 * @param {number} maxMessagesPerConversation - Keep at most this many recent messages per conversation (default: 50)
 */
export async function cleanupOldMessages(daysOld = 30, maxMessagesPerConversation = 50) {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - daysOld);
  
  console.log(`[CLEANUP] Starting cleanup of messages older than ${daysOld} days (before ${cutoffDate.toISOString()})`);
  
  try {
    // 1. Delete very old messages (older than cutoffDate)
    const oldMessagesResult = await prisma.message.deleteMany({
      where: {
        created_at: {
          lt: cutoffDate
        }
      }
    });
    
    console.log(`[CLEANUP] Deleted ${oldMessagesResult.count} old messages`);
    
    // 2. For each conversation, keep only the most recent messages
    const conversations = await prisma.conversation.findMany({
      select: {
        id: true,
        _count: {
          select: {
            messages: true
          }
        }
      }
    });
    
    let totalTrimmed = 0;
    
    for (const conversation of conversations) {
      if (conversation._count.messages > maxMessagesPerConversation) {
        // Get all messages for this conversation, ordered by created_at DESC
        const allMessages = await prisma.message.findMany({
          where: {
            conversation_id: conversation.id
          },
          orderBy: {
            created_at: 'desc'
          },
          select: {
            id: true
          }
        });
        
        // Keep only the most recent messages
        const messagesToDelete = allMessages.slice(maxMessagesPerConversation);
        
        if (messagesToDelete.length > 0) {
          const deleteResult = await prisma.message.deleteMany({
            where: {
              id: {
                in: messagesToDelete.map(m => m.id)
              }
            }
          });
          
          totalTrimmed += deleteResult.count;
          console.log(`[CLEANUP] Trimmed ${deleteResult.count} excess messages from conversation ${conversation.id}`);
        }
      }
    }
    
    console.log(`[CLEANUP] Trimmed ${totalTrimmed} excess messages from conversations`);
    
    // 3. Clean up empty conversations
    const emptyConversationsResult = await prisma.conversation.deleteMany({
      where: {
        messages: {
          none: {}
        }
      }
    });
    
    console.log(`[CLEANUP] Deleted ${emptyConversationsResult.count} empty conversations`);
    
    return {
      oldMessagesDeleted: oldMessagesResult.count,
      excessMessagesTrimmed: totalTrimmed,
      emptyConversationsDeleted: emptyConversationsResult.count
    };
    
  } catch (error) {
    console.error(`[CLEANUP] Error during cleanup:`, error);
    throw error;
  }
}

/**
 * Get database size statistics
 */
export async function getDatabaseStats() {
  try {
    const [
      totalMessages,
      totalConversations,
      oldestMessage,
      newestMessage,
      largestMessage
    ] = await Promise.all([
      prisma.message.count(),
      prisma.conversation.count(),
      prisma.message.findFirst({
        orderBy: { created_at: 'asc' },
        select: { created_at: true }
      }),
      prisma.message.findFirst({
        orderBy: { created_at: 'desc' },
        select: { created_at: true }
      }),
      prisma.message.findFirst({
        orderBy: { content: 'desc' }, // This is a rough approximation
        select: { content: true }
      })
    ]);
    
    const avgContentLength = largestMessage ? largestMessage.content.length : 0;
    
    return {
      totalMessages,
      totalConversations,
      oldestMessage: oldestMessage?.created_at,
      newestMessage: newestMessage?.created_at,
      approximateSize: totalMessages * avgContentLength,
      largestMessageSize: avgContentLength
    };
    
  } catch (error) {
    console.error(`[CLEANUP] Error getting database stats:`, error);
    throw error;
  }
}

/**
 * Automatic cleanup that can be run periodically
 */
export async function performRoutineCleanup() {
  console.log(`[CLEANUP] Performing routine cleanup...`);
  
  // Get current stats
  const statsBefore = await getDatabaseStats();
  console.log(`[CLEANUP] Database stats before cleanup:`, statsBefore);
  
  // Perform cleanup
  const result = await cleanupOldMessages(30, 50); // 30 days, max 50 messages per conversation
  
  // Get stats after cleanup
  const statsAfter = await getDatabaseStats();
  console.log(`[CLEANUP] Database stats after cleanup:`, statsAfter);
  
  return {
    ...result,
    statsBefore,
    statsAfter
  };
}

// Export for CLI usage
if (import.meta.url === `file://${process.argv[1]}`) {
  performRoutineCleanup()
    .then(result => {
      console.log('Cleanup completed:', result);
      process.exit(0);
    })
    .catch(error => {
      console.error('Cleanup failed:', error);
      process.exit(1);
    });
}