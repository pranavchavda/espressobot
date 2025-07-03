/**
 * Simple Local Memory Implementation
 * Uses SQLite for storage and OpenAI embeddings for semantic search
 * More reliable than the mem0ai OSS package
 */

import Database from 'better-sqlite3';
import { OpenAI } from 'openai';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Ensure data directory exists
const dataDir = path.join(__dirname, 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const dbPath = path.join(dataDir, 'espressobot_memory.db');
const db = new Database(dbPath);

// Initialize OpenAI
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Initialize database schema
db.exec(`
  CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    embedding BLOB,
    metadata TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  );
  
  CREATE INDEX IF NOT EXISTS idx_user_id ON memories(user_id);
  CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at);
`);

// Helper function to calculate cosine similarity
function cosineSimilarity(a, b) {
  if (a.length !== b.length) return 0;
  
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

// Generate embeddings using OpenAI
async function generateEmbedding(text) {
  try {
    // Truncate text to stay within token limits
    // Rough estimate: 1 token ≈ 4 characters for English text
    // 8192 token limit, use 7000 to be safe = ~28000 characters
    const maxLength = 28000;
    const truncatedText = text.length > maxLength 
      ? text.substring(0, maxLength) + '...' 
      : text;
    
    if (text.length > maxLength) {
      console.log(`[Memory] Truncated embedding input from ${text.length} to ${maxLength} characters`);
    }
    
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: truncatedText
    });
    return response.data[0].embedding;
  } catch (error) {
    console.error('Error generating embedding:', error);
    return null;
  }
}

class SimpleLocalMemory {
  /**
   * Check if a similar memory already exists with multiple strategies
   */
  async isDuplicate(content, userId, options = {}) {
    const {
      semanticThreshold = 0.85,    // Threshold for semantic similarity
      exactMatchCheck = true,       // Check for exact string matches
      fuzzyMatchCheck = true,       // Check for fuzzy string matches
      checkAllMemories = false,     // Check all memories (not just recent)
      recentLimit = 100,           // How many recent memories to check
      keyPhraseCheck = true        // Check for key phrase overlap
    } = options;
    
    try {
      // 1. Exact match check (fastest)
      if (exactMatchCheck) {
        const exactStmt = db.prepare(`
          SELECT COUNT(*) as count 
          FROM memories 
          WHERE user_id = ? AND LOWER(content) = LOWER(?)
        `);
        const exactResult = exactStmt.get(userId, content);
        if (exactResult.count > 0) {
          console.log(`[Memory] Found exact duplicate: "${content.substring(0, 50)}..."`);
          return { isDuplicate: true, reason: 'exact_match' };
        }
      }
      
      // 2. Fuzzy match check (normalized comparison)
      if (fuzzyMatchCheck) {
        const normalizedContent = this.normalizeText(content);
        const fuzzyStmt = db.prepare(`
          SELECT id, content 
          FROM memories 
          WHERE user_id = ?
          ORDER BY created_at DESC
          LIMIT ?
        `);
        const memories = fuzzyStmt.all(userId, recentLimit);
        
        for (const mem of memories) {
          const normalizedMem = this.normalizeText(mem.content);
          const similarity = this.calculateTextSimilarity(normalizedContent, normalizedMem);
          if (similarity > 0.9) { // Very high text similarity
            console.log(`[Memory] Found fuzzy duplicate (${similarity.toFixed(3)}): "${mem.content.substring(0, 50)}..."`);
            return { isDuplicate: true, reason: 'fuzzy_match', similarity };
          }
        }
      }
      
      // 3. Key phrase overlap check
      if (keyPhraseCheck) {
        const keyPhrases = this.extractKeyPhrases(content);
        if (keyPhrases.length > 0) {
          for (const phrase of keyPhrases) {
            const phraseStmt = db.prepare(`
              SELECT COUNT(*) as count 
              FROM memories 
              WHERE user_id = ? AND content LIKE ?
            `);
            const result = phraseStmt.get(userId, `%${phrase}%`);
            if (result.count > 0) {
              console.log(`[Memory] Found key phrase duplicate: "${phrase}"`);
              // Don't return here, continue to semantic check for better context
            }
          }
        }
      }
      
      // 4. Semantic similarity check (most expensive)
      const embedding = await generateEmbedding(content);
      if (!embedding) return { isDuplicate: false, reason: 'no_embedding' };
      
      // Get memories to check
      const semanticStmt = db.prepare(`
        SELECT id, content, embedding
        FROM memories 
        WHERE user_id = ?
        ORDER BY created_at DESC
        ${checkAllMemories ? '' : 'LIMIT ?'}
      `);
      
      const memoriesToCheck = checkAllMemories 
        ? semanticStmt.all(userId)
        : semanticStmt.all(userId, recentLimit);
      
      // Check similarity with memories
      let highestSimilarity = 0;
      let mostSimilarContent = null;
      
      for (const mem of memoriesToCheck) {
        const memEmbedding = JSON.parse(mem.embedding);
        const similarity = cosineSimilarity(embedding, memEmbedding);
        
        if (similarity > highestSimilarity) {
          highestSimilarity = similarity;
          mostSimilarContent = mem.content;
        }
        
        if (similarity > semanticThreshold) {
          console.log(`[Memory] Found semantic duplicate (${similarity.toFixed(3)}): "${mem.content.substring(0, 50)}..."`);
          return { 
            isDuplicate: true, 
            reason: 'semantic_match', 
            similarity,
            existingContent: mem.content
          };
        }
      }
      
      // Log near-duplicates for monitoring
      if (highestSimilarity > 0.7) {
        console.log(`[Memory] Near duplicate (${highestSimilarity.toFixed(3)}): "${mostSimilarContent?.substring(0, 50)}..."`);
      }
      
      return { isDuplicate: false, highestSimilarity };
    } catch (error) {
      console.error('Error checking duplicate:', error);
      return { isDuplicate: false, error: error.message };
    }
  }
  
  /**
   * Normalize text for fuzzy matching
   */
  normalizeText(text) {
    return text
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ')  // Remove punctuation
      .replace(/\s+/g, ' ')      // Normalize whitespace
      .trim();
  }
  
  /**
   * Calculate text similarity using Jaccard index
   */
  calculateTextSimilarity(text1, text2) {
    const words1 = new Set(text1.split(' '));
    const words2 = new Set(text2.split(' '));
    
    const intersection = new Set([...words1].filter(x => words2.has(x)));
    const union = new Set([...words1, ...words2]);
    
    return intersection.size / union.size;
  }
  
  /**
   * Extract key phrases from content
   */
  extractKeyPhrases(content) {
    const keyPhrases = [];
    
    // Extract quoted phrases
    const quotedMatches = content.match(/"([^"]+)"/g);
    if (quotedMatches) {
      keyPhrases.push(...quotedMatches.map(m => m.replace(/"/g, '')));
    }
    
    // Extract email addresses
    const emailMatches = content.match(/[\w.-]+@[\w.-]+\.\w+/g);
    if (emailMatches) {
      keyPhrases.push(...emailMatches);
    }
    
    // Extract names (capitalized words)
    const nameMatches = content.match(/\b[A-Z][a-z]+ [A-Z][a-z]+\b/g);
    if (nameMatches) {
      keyPhrases.push(...nameMatches);
    }
    
    // Extract specific patterns (dates, prices, percentages)
    const patternMatches = content.match(/\b\d+%|\$\d+\.?\d*|\b\d{4}-\d{2}-\d{2}\b/g);
    if (patternMatches) {
      keyPhrases.push(...patternMatches);
    }
    
    return [...new Set(keyPhrases)]; // Remove duplicates
  }
  
  /**
   * Add a memory with strong deduplication
   */
  async add(content, userId, metadata = {}) {
    try {
      // Filter out system/metric entries (but allow system_prompts)
      if (userId === 'system_metrics' || (userId.startsWith('system_') && userId !== 'system_prompts')) {
        console.log(`[Memory] Skipping system entry for ${userId}`);
        return {
          success: false,
          reason: 'system_entry',
          message: 'System entries are not stored as user memories'
        };
      }
      
      // Validate content is meaningful
      if (!content || typeof content !== 'string' || content.trim().length < 10) {
        console.log(`[Memory] Skipping invalid content: "${content}"`);
        return {
          success: false,
          reason: 'invalid_content',
          message: 'Content too short or invalid'
        };
      }
      
      // Skip if content looks like system logs
      if (content.includes('"type":"context_usage"') || 
          content.includes('"responseTime":') ||
          content.includes('"timestamp":')) {
        console.log(`[Memory] Skipping system log content`);
        return {
          success: false,
          reason: 'system_log',
          message: 'System logs are not stored as memories'
        };
      }
      // Check for duplicates with multiple strategies
      const dupeCheck = await this.isDuplicate(content, userId, {
        semanticThreshold: 0.85,
        exactMatchCheck: true,
        fuzzyMatchCheck: true,
        keyPhraseCheck: true,
        recentLimit: 200  // Check more memories for better deduplication
      });
      
      if (dupeCheck.isDuplicate) {
        console.log(`[Memory] Skipping duplicate memory (${dupeCheck.reason}): "${content.substring(0, 50)}..."`);
        return {
          success: false,
          reason: dupeCheck.reason,
          message: `Memory already exists (${dupeCheck.reason})`,
          similarity: dupeCheck.similarity,
          existingContent: dupeCheck.existingContent
        };
      }
      
      const id = `mem_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const embedding = await generateEmbedding(content);
      
      if (!embedding) {
        throw new Error('Failed to generate embedding');
      }
      
      // Store embedding as JSON string
      const embeddingBlob = JSON.stringify(embedding);
      const metadataStr = JSON.stringify(metadata);
      
      const stmt = db.prepare(`
        INSERT INTO memories (id, user_id, content, embedding, metadata)
        VALUES (?, ?, ?, ?, ?)
      `);
      
      stmt.run(id, userId, content, embeddingBlob, metadataStr);
      
      console.log(`Memory added: ${id} for user ${userId}`);
      return {
        id,
        memory: content,
        metadata,
        success: true
      };
    } catch (error) {
      console.error('Error adding memory:', error);
      throw error;
    }
  }

  /**
   * Search memories
   */
  async search(query, userId, limit = 10) {
    try {
      const queryEmbedding = await generateEmbedding(query);
      if (!queryEmbedding) {
        throw new Error('Failed to generate query embedding');
      }
      
      // Get all memories for user
      const stmt = db.prepare(`
        SELECT id, content, embedding, metadata, created_at
        FROM memories 
        WHERE user_id = ?
        ORDER BY created_at DESC
      `);
      
      const memories = stmt.all(userId);
      
      // Calculate similarities
      const results = memories.map(mem => {
        const memEmbedding = JSON.parse(mem.embedding);
        const similarity = cosineSimilarity(queryEmbedding, memEmbedding);
        
        return {
          id: mem.id,
          memory: mem.content,
          score: similarity,
          metadata: JSON.parse(mem.metadata || '{}'),
          createdAt: mem.created_at
        };
      });
      
      // Sort by similarity and limit results
      const sortedResults = results
        .sort((a, b) => b.score - a.score)
        .slice(0, limit)
        .filter(r => r.score > 0.1); // Filter out very low similarity
      
      console.log(`Found ${sortedResults.length} memories for query "${query}"`);
      return sortedResults;
    } catch (error) {
      console.error('Error searching memories:', error);
      return [];
    }
  }

  /**
   * Get a specific memory by ID
   */
  async get(memoryId) {
    try {
      const stmt = db.prepare(`
        SELECT id, user_id, content, metadata, created_at
        FROM memories 
        WHERE id = ?
      `);
      
      const memory = stmt.get(memoryId);
      
      if (!memory) {
        return null;
      }
      
      return {
        id: memory.id,
        userId: memory.user_id,
        memory: memory.content,
        metadata: JSON.parse(memory.metadata || '{}'),
        createdAt: memory.created_at
      };
    } catch (error) {
      console.error('Error getting memory:', error);
      return null;
    }
  }

  /**
   * Get all memories for a user
   */
  async getAll(userId, limit = 100) {
    try {
      let stmt, memories;
      
      if (userId) {
        stmt = db.prepare(`
          SELECT id, user_id, content, metadata, created_at
          FROM memories 
          WHERE user_id = ?
          ORDER BY created_at DESC
          LIMIT ?
        `);
        memories = stmt.all(userId, limit);
      } else {
        // Get all memories from all users
        stmt = db.prepare(`
          SELECT id, user_id, content, metadata, created_at
          FROM memories 
          ORDER BY created_at DESC
          LIMIT ?
        `);
        memories = stmt.all(limit);
      }
      
      return memories.map(mem => ({
        id: mem.id,
        userId: mem.user_id,
        memory: mem.content,
        metadata: JSON.parse(mem.metadata || '{}'),
        createdAt: mem.created_at
      }));
    } catch (error) {
      console.error('Error getting all memories:', error);
      return [];
    }
  }

  /**
   * Update a memory
   */
  async update(memoryId, content) {
    try {
      const embedding = await generateEmbedding(content);
      if (!embedding) {
        throw new Error('Failed to generate embedding');
      }
      
      const embeddingBlob = JSON.stringify(embedding);
      
      const stmt = db.prepare(`
        UPDATE memories 
        SET content = ?, embedding = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
      `);
      
      const result = stmt.run(content, embeddingBlob, memoryId);
      
      if (result.changes === 0) {
        throw new Error('Memory not found');
      }
      
      return { success: true, message: 'Memory updated successfully' };
    } catch (error) {
      console.error('Error updating memory:', error);
      throw error;
    }
  }

  /**
   * Delete a memory
   */
  async delete(memoryId) {
    try {
      const stmt = db.prepare('DELETE FROM memories WHERE id = ?');
      const result = stmt.run(memoryId);
      
      if (result.changes === 0) {
        throw new Error('Memory not found');
      }
      
      return { success: true, message: 'Memory deleted successfully' };
    } catch (error) {
      console.error('Error deleting memory:', error);
      throw error;
    }
  }

  /**
   * Delete all memories for a user
   */
  async deleteAll(userId) {
    try {
      const stmt = db.prepare('DELETE FROM memories WHERE user_id = ?');
      const result = stmt.run(userId);
      
      return { 
        success: true, 
        message: `Deleted ${result.changes} memories for user ${userId}` 
      };
    } catch (error) {
      console.error('Error deleting all memories:', error);
      throw error;
    }
  }

  /**
   * Split conversation into exchanges (user message + assistant response pairs)
   */
  splitIntoExchanges(conversationText) {
    // Try to split by User:/Assistant: pattern
    const lines = conversationText.split('\n');
    const exchanges = [];
    let currentExchange = '';
    
    for (const line of lines) {
      if (line.startsWith('User:') && currentExchange.includes('Assistant:')) {
        // Start of new exchange, save the previous one
        exchanges.push(currentExchange.trim());
        currentExchange = line;
      } else {
        currentExchange += '\n' + line;
      }
    }
    
    // Don't forget the last exchange
    if (currentExchange.trim()) {
      exchanges.push(currentExchange.trim());
    }
    
    // If no clear pattern, just return the whole conversation
    if (exchanges.length === 0) {
      return [conversationText];
    }
    
    return exchanges;
  }
  
  /**
   * Extract memory summary using GPT-4.1-mini or nano
   */
  async extractMemorySummary(conversationText, context = {}) {
    // Determine which model to use based on context or environment
    const useNano = process.env.USE_GPT_NANO_FOR_MEMORY === 'true' || context.useNano;
    const model = useNano ? 'gpt-4.1-nano' : 'o4-mini';
    
    try {
      console.log(`[Memory] Using ${model} for extraction`);
      
      // Split long conversations into exchanges
      const exchanges = this.splitIntoExchanges(conversationText);
      const allFacts = [];
      
      // Process each exchange separately (max 2 facts per exchange)
      for (const exchange of exchanges) {
        if (exchange.trim().length < 20) continue; // Skip very short exchanges
        
        // Use GPT to extract key facts from this exchange
        const response = await openai.chat.completions.create({
          model: model,
          messages: [
          {
            role: 'system',
            content: `You are a memory extraction system. Extract important facts from conversations as single, self-contained sentences. Each fact should be independently understandable without context.

Rules:
1. Extract facts worth remembering long-term, not temporary conversation state
2. Each fact must be a complete, standalone sentence
3. Maximum 2 facts per message exchange (user message + assistant response)
4. You don't have to extract facts from every exchange. If you don't see any facts, just return an empty list.
5. ALWAYS extract when user says "remember that" or "remember this" or similar
6. Include confirmed facts from assistant responses (e.g., "The CEO is X" when user confirms)
7. Focus on: personal info, preferences, business context, decisions, confirmed information, future plans, and any other relevant information.
8. Format: Return each fact on a new line

Priority facts to extract:
- Explicit "remember" requests: User says to remember something
- Personal information: Names, roles, birthdays, locations
- Preferences: "I prefer X", "I like Y", "My favorite is Z"  
- Business facts: Company info, project names, important metrics
- Confirmed corrections: When user corrects or confirms information

Good examples:
- The user's name is Pranav.
- Pranav works as a generalist at iDrinkCoffee.com.
- Bruno is a customer support chatbot project.
- Espressobot is one of Pranav's recent projects.
- The user prefers to review changes before applying them.
- The CEO of iDrinkCoffee.com is Slawek Janicki.

Do NOT extract:
- Questions or requests: "Can you help with X?"
- Temporary states: "User is looking at Y"
- Process descriptions: "User is focused on gathering requirements"
- Unconfirmed suggestions: "You might want to try X"`
          },
          {
            role: 'user',
            content: exchange
          }
        ],
        // max_tokens: 200  // Less tokens needed per exchange
        reasoning_effort: 'low'
      });

      const exchangeFacts = response.choices[0].message.content
        .split('\n')
        .filter(line => line.trim().length > 0)
        .map(fact => fact.trim())
        .slice(0, 2);  // Enforce max 2 facts per exchange

      allFacts.push(...exchangeFacts);
    }

    console.log(`[Memory] Extracted ${allFacts.length} total facts from ${exchanges.length} exchanges`);
    
    return allFacts.map(fact => ({
      content: fact,
      metadata: {
        timestamp: new Date().toISOString(),
        conversationId: context.conversationId || 'unknown',
        agent: context.agent || 'unknown',
        extractedFrom: 'conversation',
        source: model
      }
      }));
    } catch (error) {
      console.error(`Error extracting memory with ${model}:`, error);
      
      // Fallback to simple extraction
      const lines = conversationText.trim().split('\n').filter(line => line.trim());
      const summary = lines
        .filter(line => line.includes('User:') || line.includes('Assistant:'))
        .join(' ')
        .replace(/User:|Assistant:/g, '')
        .trim();
      
      return [{
        content: summary,
        metadata: {
          timestamp: new Date().toISOString(),
          conversationId: context.conversationId || 'unknown',
          agent: context.agent || 'unknown',
          extractedFrom: 'conversation',
          source: 'fallback'
        }
      }];
    }
  }

  /**
   * Merge related memories to consolidate information
   */
  async mergeRelatedMemories(userId, options = {}) {
    const {
      mergeThreshold = 0.75,  // Similarity threshold for merging
      dryRun = false          // If true, only returns what would be merged
    } = options;
    
    try {
      console.log(`[Memory] Starting memory consolidation for user ${userId}`);
      
      // Get all memories for user
      const stmt = db.prepare(`
        SELECT id, content, embedding, metadata, created_at
        FROM memories 
        WHERE user_id = ?
        ORDER BY created_at DESC
      `);
      const memories = stmt.all(userId);
      
      const mergeGroups = [];
      const processed = new Set();
      
      // Find groups of related memories
      for (let i = 0; i < memories.length; i++) {
        if (processed.has(memories[i].id)) continue;
        
        const group = [memories[i]];
        const embedding1 = JSON.parse(memories[i].embedding);
        
        for (let j = i + 1; j < memories.length; j++) {
          if (processed.has(memories[j].id)) continue;
          
          const embedding2 = JSON.parse(memories[j].embedding);
          const similarity = cosineSimilarity(embedding1, embedding2);
          
          if (similarity > mergeThreshold) {
            group.push(memories[j]);
            processed.add(memories[j].id);
          }
        }
        
        if (group.length > 1) {
          mergeGroups.push(group);
          group.forEach(mem => processed.add(mem.id));
        }
      }
      
      console.log(`[Memory] Found ${mergeGroups.length} groups to merge`);
      
      if (dryRun) {
        return {
          groups: mergeGroups.map(group => ({
            count: group.length,
            memories: group.map(m => m.content)
          }))
        };
      }
      
      // Perform merges
      const mergeResults = [];
      for (const group of mergeGroups) {
        // Use GPT-4.1-mini to create a consolidated memory
        const contents = group.map(m => m.content).join('\n- ');
        const consolidatedFact = await this.consolidateMemories(contents);
        
        if (consolidatedFact) {
          // Delete old memories
          const deleteStmt = db.prepare('DELETE FROM memories WHERE id = ?');
          group.forEach(mem => deleteStmt.run(mem.id));
          
          // Add consolidated memory
          await this.add(consolidatedFact, userId, {
            ...group[0].metadata,
            consolidated: true,
            originalCount: group.length,
            consolidatedAt: new Date().toISOString()
          });
          
          mergeResults.push({
            original: group.map(m => m.content),
            consolidated: consolidatedFact
          });
        }
      }
      
      return {
        success: true,
        merged: mergeResults.length,
        results: mergeResults
      };
    } catch (error) {
      console.error('Error merging memories:', error);
      return { success: false, error: error.message };
    }
  }
  
  /**
   * Use GPT to consolidate related memories
   */
  async consolidateMemories(memories) {
    try {
      const response = await openai.chat.completions.create({
        model: 'gpt-4.1-mini',
        messages: [
          {
            role: 'system',
            content: 'Consolidate the following related facts into a single, comprehensive fact. Keep all important information but remove redundancy. Output only the consolidated fact.'
          },
          {
            role: 'user',
            content: memories
          }
        ],
        temperature: 0.3,
        max_tokens: 150
      });
      
      return response.choices[0].message.content.trim();
    } catch (error) {
      console.error('Error consolidating with GPT:', error);
      return null;
    }
  }
  
  /**
   * Get database statistics
   */
  getStats() {
    try {
      const totalStmt = db.prepare('SELECT COUNT(*) as total FROM memories');
      const userStmt = db.prepare('SELECT user_id, COUNT(*) as count FROM memories GROUP BY user_id');
      
      const total = totalStmt.get().total;
      const byUser = userStmt.all();
      
      return { total, byUser };
    } catch (error) {
      console.error('Error getting stats:', error);
      return { total: 0, byUser: [] };
    }
  }
}

// Export singleton instance
export const simpleLocalMemory = new SimpleLocalMemory();

console.log('Simple Local Memory initialized with SQLite storage');