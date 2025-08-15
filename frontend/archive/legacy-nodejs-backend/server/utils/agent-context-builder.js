/**
 * Agent Context Builder
 * 
 * Provides consistent organizational context for all agents in the EspressoBot system
 */

/**
 * Build standard agent context preamble
 */
export function buildAgentContextPreamble(options = {}) {
  const {
    agentRole = 'specialist',
    conversationId = null,
    conversationTopic = null,
    taskDescription = null
  } = options;
  
  let preamble = `You are a ${agentRole} agent in the EspressoBot agency - an AI-powered assistant system that supports iDrinkCoffee.com with all manner of e-commerce tasks including product management, pricing updates, inventory control, customer service, and business operations.

EspressoBot is a multi-agent system where specialized agents collaborate to complete complex tasks efficiently. Each agent has specific capabilities and works together with others to achieve the user's goals.`;

  if (conversationId) {
    // Ensure conversationId is a string (in case it's passed as an object)
    let idString;
    if (typeof conversationId === 'string') {
      idString = conversationId;
    } else if (conversationId && typeof conversationId === 'object') {
      // If it's an object, try to get an ID field or convert it properly
      idString = conversationId.id || conversationId._id || conversationId.conversationId || 
                 JSON.stringify(conversationId);
    } else {
      idString = String(conversationId);
    }
    preamble += `\n\nYou are currently part of conversation #${idString}`;
    
    if (conversationTopic) {
      // Truncate topic to 20 words max
      const topicWords = conversationTopic.split(' ').slice(0, 20).join(' ');
      const truncatedTopic = topicWords.length < conversationTopic.length ? 
        topicWords + '...' : topicWords;
      preamble += ` which is about: ${truncatedTopic}`;
    }
    
    preamble += '.';
  }
  
  if (taskDescription) {
    preamble += `\n\nYour current task: ${taskDescription}`;
  }
  
  return preamble;
}

/**
 * Get conversation topic from task planning data or conversation history
 */
export async function getConversationTopic(conversationId) {
  try {
    // First try to get from task planning data
    const { getTaskData } = await import('../agents/task-planning-agent.js');
    const taskData = await getTaskData(conversationId);
    
    if (taskData && taskData.tasks && taskData.tasks.length > 0) {
      // Summarize tasks into a topic
      const firstTask = taskData.tasks[0].description;
      return firstTask.substring(0, 100); // First 100 chars as topic
    }
    
    // Try to get from conversation topic if stored
    // This would need to be implemented in conversation management
    
    return null;
  } catch (error) {
    console.log('[AgentContext] Could not retrieve conversation topic:', error.message);
    return null;
  }
}

/**
 * Build complete agent instructions with context
 */
export async function buildAgentInstructions(baseInstructions, options = {}) {
  const {
    agentRole = 'specialist',
    conversationId = null,
    taskDescription = null,
    includeTopicLookup = true
  } = options;
  
  let conversationTopic = null;
  if (conversationId && includeTopicLookup) {
    conversationTopic = await getConversationTopic(conversationId);
  }
  
  const contextPreamble = buildAgentContextPreamble({
    agentRole,
    conversationId,
    conversationTopic,
    taskDescription
  });
  
  return `${contextPreamble}

${baseInstructions}`;
}