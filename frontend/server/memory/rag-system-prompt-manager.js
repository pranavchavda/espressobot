import { simpleLocalMemory } from './simple-local-memory.js';
import { createOpenAIWithRetry } from '../utils/openai-with-retry.js';

const openai = createOpenAIWithRetry();

class RAGSystemPromptManager {
  constructor() {
    this.memoryStore = simpleLocalMemory;
    this.promptCache = new Map();
    this.systemPromptUserId = 'system_prompts';
  }

  async addPromptFragment(fragment, metadata) {
    return await this.memoryStore.add(
      fragment,
      this.systemPromptUserId,
      {
        type: 'system_prompt',
        category: metadata.category || 'general',
        priority: metadata.priority || 'medium',
        tags: metadata.tags || [],
        agent_type: metadata.agent_type || 'all',
        ...metadata
      }
    );
  }

  async getSystemPrompt(context, options = {}) {
    const {
      basePrompt = '',
      maxFragments = 10,
      includeMemories = true,
      userId = null,
      agentType = 'general',
      minScore = 0.6
    } = options;

    const cacheKey = `${context.slice(0, 50)}_${agentType}_${userId}`;
    
    if (this.promptCache.has(cacheKey)) {
      const cached = this.promptCache.get(cacheKey);
      if (Date.now() - cached.timestamp < 300000) { // 5 minute cache
        return cached.prompt;
      }
    }

    const fragments = await this.memoryStore.search(
      context,
      this.systemPromptUserId,
      maxFragments * 2
    );

    const relevantFragments = fragments
      .filter(f => {
        const metadata = f.metadata || {};
        return f.score >= minScore && 
               (metadata.agent_type === 'all' || metadata.agent_type === agentType);
      })
      .sort((a, b) => {
        const priorityOrder = { high: 3, medium: 2, low: 1 };
        const aPriority = priorityOrder[a.metadata?.priority] || 2;
        const bPriority = priorityOrder[b.metadata?.priority] || 2;
        
        if (aPriority !== bPriority) return bPriority - aPriority;
        return b.score - a.score;
      })
      .slice(0, maxFragments);

    let memories = [];
    if (includeMemories && userId) {
      memories = await this.memoryStore.search(
        context,
        userId,
        5
      );
    }

    const prompt = await this.constructPrompt({
      base: basePrompt,
      fragments: relevantFragments,
      memories: memories,
      context: context,
      agentType: agentType
    });

    this.promptCache.set(cacheKey, {
      prompt: prompt,
      timestamp: Date.now()
    });

    if (this.promptCache.size > 100) {
      const oldestKey = [...this.promptCache.entries()]
        .sort((a, b) => a[1].timestamp - b[1].timestamp)[0][0];
      this.promptCache.delete(oldestKey);
    }

    return prompt;
  }

  async constructPrompt({ base, fragments, memories, context, agentType }) {
    let prompt = base || '';

    if (fragments.length > 0) {
      const categorized = this.categorizeFragments(fragments);
      
      for (const [category, categoryFragments] of Object.entries(categorized)) {
        if (categoryFragments.length > 0) {
          prompt += `\n\n## ${this.formatCategoryName(category)}\n`;
          categoryFragments.forEach(f => {
            prompt += `\n${f.memory}`;
          });
        }
      }
    }

    if (memories.length > 0) {
      const summaryPrompt = `Summarize these relevant past interactions in 2-3 concise bullet points that would help with the current task: "${context}"\n\nPast interactions:\n${memories.map(m => m.memory).join('\n')}\n\nProvide only the bullet points, no other text.`;
      
      try {
        const response = await openai.chat.completions.create({
          model: 'gpt-4.1-mini',
          messages: [
            { role: 'system', content: 'You are a helpful assistant that summarizes information concisely.' },
            { role: 'user', content: summaryPrompt }
          ],
          temperature: 0.3,
          max_tokens: 150
        });
        
        if (response.choices[0]?.message?.content) {
          prompt += '\n\n## Relevant History\n' + response.choices[0].message.content;
        }
      } catch (error) {
        console.error('Error summarizing memories:', error);
        prompt += '\n\n## Relevant History\n';
        memories.slice(0, 3).forEach(m => {
          prompt += `\n- ${m.memory}`;
        });
      }
    }

    return prompt;
  }

  categorizeFragments(fragments) {
    const categories = {};
    
    fragments.forEach(f => {
      const category = f.metadata?.category || 'general';
      if (!categories[category]) {
        categories[category] = [];
      }
      categories[category].push(f);
    });
    
    return categories;
  }

  formatCategoryName(category) {
    const nameMap = {
      'tools': 'Available Tools & Capabilities',
      'workflows': 'Recommended Workflows',
      'constraints': 'Important Constraints',
      'patterns': 'Best Practices & Patterns',
      'errors': 'Common Errors & Solutions',
      'domain': 'Domain-Specific Knowledge',
      'general': 'Additional Context'
    };
    
    return nameMap[category] || category.charAt(0).toUpperCase() + category.slice(1);
  }

  async updateFromExperience(experience, metadata) {
    const analysisPrompt = `Extract key learnings from this experience that would be valuable for future similar tasks. Focus on actionable insights, patterns, and solutions. Be concise.

Experience:
${experience}

Provide 1-3 specific learnings as separate items. Format each as a clear guideline or insight.`;

    try {
      const response = await openai.chat.completions.create({
        model: 'gpt-4.1-mini',
        messages: [
          { role: 'system', content: 'You are an expert at extracting actionable learnings from experiences.' },
          { role: 'user', content: analysisPrompt }
        ],
        temperature: 0.5,
        max_tokens: 200
      });
      
      if (response.choices[0]?.message?.content) {
        const learnings = response.choices[0].message.content.split('\n').filter(l => l.trim());
        const results = [];
        
        for (const learning of learnings) {
          if (learning.trim()) {
            const result = await this.addPromptFragment(learning.trim(), {
              ...metadata,
              learned_from: experience.slice(0, 100),
              learned_at: new Date().toISOString()
            });
            results.push(result);
          }
        }
        
        return results;
      }
    } catch (error) {
      console.error('Error extracting learnings:', error);
    }
    
    return [];
  }

  async clearCache() {
    this.promptCache.clear();
  }
}

export default new RAGSystemPromptManager();