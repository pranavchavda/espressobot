import { tool } from '@openai/agents';
import { z } from 'zod';
import ragSystemPromptManager from '../memory/rag-system-prompt-manager.js';
import { memoryOperations } from '../memory/memory-operations-local.js';

/**
 * Tool for agents to learn from experience and update system prompts
 */
export const learningTool = tool({
  name: 'learn_from_experience',
  description: 'Add new knowledge to system prompt database based on learned experience',
  parameters: z.object({
    learning: z.string().describe('What was learned - a clear guideline or insight'),
    category: z.enum(['tools', 'workflows', 'constraints', 'patterns', 'errors', 'domain', 'general'])
      .describe('Category of learning'),
    tags: z.array(z.string()).describe('Tags for retrieval (e.g., ["bash", "error-handling"])'),
    agentType: z.enum(['all', 'bash', 'swe', 'orchestrator'])
      .describe('Which agent types should use this learning'),
    priority: z.enum(['high', 'medium', 'low'])
      .describe('Priority of this learning'),
    context: z.string().nullable().describe('Optional context about when/how this was learned')
  }),
  execute: async ({ learning, category, tags, agentType, priority, context }) => {
    try {
      // Add the learning as a system prompt fragment
      const result = await memoryOperations.addSystemPromptFragment(learning, {
        category,
        tags,
        agent_type: agentType || 'all',
        priority: priority || 'medium',
        learned_from_agent: global.currentAgentName || 'unknown',
        learned_context: context,
        learned_at: new Date().toISOString()
      });
      
      if (result.success) {
        // Clear the cache to ensure new learnings are used immediately
        await ragSystemPromptManager.clearCache();
        
        return {
          success: true,
          message: `Learning added to system prompts: "${learning.slice(0, 50)}..."`,
          id: result.id,
          details: {
            category,
            tags,
            agentType,
            priority
          }
        };
      } else {
        return {
          success: false,
          message: `Failed to add learning: ${result.message || 'Unknown error'}`,
          reason: result.reason
        };
      }
    } catch (error) {
      console.error('[Learning Tool] Error:', error);
      return {
        success: false,
        message: `Error adding learning: ${error.message}`,
        error: error.toString()
      };
    }
  }
});

/**
 * Tool for agents to reflect on experience and extract multiple learnings
 */
export const reflectAndLearnTool = tool({
  name: 'reflect_and_learn',
  description: 'Analyze an experience and extract multiple learnings for future use',
  parameters: z.object({
    experience: z.string().describe('Description of what happened (task, approach, outcome)'),
    whatWorked: z.string().nullable().describe('What worked well'),
    whatFailed: z.string().nullable().describe('What didn\'t work or caused issues'),
    category: z.enum(['tools', 'workflows', 'constraints', 'patterns', 'errors', 'domain', 'general'])
      .describe('Primary category of experience'),
    tags: z.array(z.string()).describe('Tags for retrieval'),
    agentType: z.enum(['all', 'bash', 'swe', 'orchestrator'])
      .describe('Which agent types should learn from this')
  }),
  execute: async ({ experience, whatWorked, whatFailed, category, tags, agentType }) => {
    try {
      const fullExperience = `
Experience: ${experience}
${whatWorked ? `\nWhat worked: ${whatWorked}` : ''}
${whatFailed ? `\nWhat failed: ${whatFailed}` : ''}
      `.trim();
      
      // Use the RAG manager to extract learnings
      const learnings = await ragSystemPromptManager.updateFromExperience(fullExperience, {
        category,
        tags,
        agent_type: agentType || 'all',
        priority: whatFailed ? 'high' : 'medium',
        learned_from_agent: global.currentAgentName || 'unknown'
      });
      
      if (learnings && learnings.length > 0) {
        // Clear cache for immediate use
        await ragSystemPromptManager.clearCache();
        
        return {
          success: true,
          message: `Extracted and stored ${learnings.length} learnings from experience`,
          learnings: learnings.map(l => ({
            id: l.id,
            content: l.memory,
            metadata: l.metadata
          })),
          summary: `Successfully reflected on experience and updated system knowledge`
        };
      } else {
        return {
          success: false,
          message: 'No learnings could be extracted from the experience',
          experience: fullExperience
        };
      }
    } catch (error) {
      console.error('[Reflect & Learn Tool] Error:', error);
      return {
        success: false,
        message: `Error reflecting on experience: ${error.message}`,
        error: error.toString()
      };
    }
  }
});

/**
 * Tool to search existing system prompt knowledge
 */
export const searchKnowledgeTool = tool({
  name: 'search_knowledge',
  description: 'Search existing system prompt knowledge base',
  parameters: z.object({
    query: z.string().describe('What to search for'),
    category: z.enum(['tools', 'workflows', 'constraints', 'patterns', 'errors', 'domain', 'general', 'all'])
      .describe('Category to search in'),
    limit: z.number().min(1).max(20).describe('Maximum results to return')
  }),
  execute: async ({ query, category, limit }) => {
    try {
      const results = await memoryOperations.searchSystemPromptFragments(query, (limit || 5) * 2);
      
      // Filter by category if specified
      const filtered = (category || 'all') === 'all' 
        ? results 
        : results.filter(r => r.metadata?.category === category);
      
      const finalResults = filtered.slice(0, limit || 5);
      
      return {
        success: true,
        count: finalResults.length,
        results: finalResults.map(r => ({
          content: r.memory,
          score: r.score,
          category: r.metadata?.category || 'general',
          tags: r.metadata?.tags || [],
          priority: r.metadata?.priority || 'medium',
          agentType: r.metadata?.agent_type || 'all',
          learnedFrom: r.metadata?.learned_from_agent,
          learnedAt: r.metadata?.learned_at
        })),
        query,
        category
      };
    } catch (error) {
      console.error('[Search Knowledge Tool] Error:', error);
      return {
        success: false,
        message: `Error searching knowledge: ${error.message}`,
        error: error.toString()
      };
    }
  }
});

// Export all learning tools
export const learningTools = [learningTool, reflectAndLearnTool, searchKnowledgeTool];