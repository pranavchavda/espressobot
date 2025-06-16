import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { v4 as uuidv4 } from 'uuid';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const MEMORIES_DIR = join(__dirname, '../memories');
const MEMORIES_FILE = join(MEMORIES_DIR, 'user_memories.json');

// Ensure memories directory exists
if (!existsSync(MEMORIES_DIR)) {
  mkdirSync(MEMORIES_DIR, { recursive: true });
}

// Initialize memories file if it doesn't exist
if (!existsSync(MEMORIES_FILE)) {
  writeFileSync(MEMORIES_FILE, JSON.stringify({ memories: [] }, null, 2));
}

class MemoryStore {
  constructor() {
    this.memories = this.loadMemories();
    this.saveDebounceTimer = null;
  }

  loadMemories() {
    try {
      const data = readFileSync(MEMORIES_FILE, 'utf-8');
      const parsed = JSON.parse(data);
      return parsed.memories || [];
    } catch (error) {
      console.error('Error loading memories:', error);
      return [];
    }
  }

  saveMemories() {
    try {
      writeFileSync(MEMORIES_FILE, JSON.stringify({ memories: this.memories }, null, 2));
    } catch (error) {
      console.error('Error saving memories:', error);
    }
  }

  // Debounced save to avoid too many file writes
  debouncedSave() {
    if (this.saveDebounceTimer) {
      clearTimeout(this.saveDebounceTimer);
    }
    this.saveDebounceTimer = setTimeout(() => {
      this.saveMemories();
    }, 1000);
  }

  createMemory(userId, content, metadata = {}) {
    const memory = {
      id: `mem_${uuidv4()}`,
      user_id: userId,
      conversation_id: metadata.conversation_id || null,
      content: content,
      timestamp: new Date().toISOString(),
      category: metadata.category || 'general',
      embedding: metadata.embedding || null,
      metadata: {
        importance: metadata.importance || 'medium',
        source: metadata.source || 'conversation',
        ...metadata
      }
    };

    this.memories.push(memory);
    this.debouncedSave();
    return memory;
  }

  getMemoriesByUser(userId) {
    return this.memories.filter(m => m.user_id === userId);
  }

  getMemoryById(memoryId) {
    return this.memories.find(m => m.id === memoryId);
  }

  updateMemory(memoryId, updates) {
    const index = this.memories.findIndex(m => m.id === memoryId);
    if (index !== -1) {
      this.memories[index] = { ...this.memories[index], ...updates };
      this.debouncedSave();
      return this.memories[index];
    }
    return null;
  }

  deleteMemory(memoryId) {
    const index = this.memories.findIndex(m => m.id === memoryId);
    if (index !== -1) {
      const deleted = this.memories.splice(index, 1)[0];
      this.debouncedSave();
      return deleted;
    }
    return null;
  }

  // Prune old memories if over limit
  pruneMemories(userId, maxMemories = 1000) {
    const userMemories = this.getMemoriesByUser(userId);
    if (userMemories.length > maxMemories) {
      // Sort by timestamp and importance, keep most recent/important
      const sorted = userMemories.sort((a, b) => {
        // First sort by importance
        const importanceOrder = { high: 3, medium: 2, low: 1 };
        const importanceDiff = (importanceOrder[b.metadata.importance] || 2) - 
                               (importanceOrder[a.metadata.importance] || 2);
        if (importanceDiff !== 0) return importanceDiff;
        
        // Then by timestamp
        return new Date(b.timestamp) - new Date(a.timestamp);
      });

      // Keep top memories, remove the rest
      const toRemove = sorted.slice(maxMemories);
      toRemove.forEach(memory => {
        const index = this.memories.findIndex(m => m.id === memory.id);
        if (index !== -1) {
          this.memories.splice(index, 1);
        }
      });
      
      this.debouncedSave();
    }
  }

  // Check for duplicate memories
  findSimilarMemory(userId, content, threshold = 0.9) {
    const userMemories = this.getMemoriesByUser(userId);
    
    // Simple text similarity check (can be enhanced with embeddings)
    for (const memory of userMemories) {
      const similarity = this.calculateTextSimilarity(memory.content, content);
      if (similarity > threshold) {
        return memory;
      }
    }
    
    return null;
  }

  // Simple text similarity (Jaccard similarity)
  calculateTextSimilarity(text1, text2) {
    const words1 = new Set(text1.toLowerCase().split(/\s+/));
    const words2 = new Set(text2.toLowerCase().split(/\s+/));
    
    const intersection = new Set([...words1].filter(x => words2.has(x)));
    const union = new Set([...words1, ...words2]);
    
    return intersection.size / union.size;
  }

  // Get memories with embeddings for semantic search
  getMemoriesWithEmbeddings(userId) {
    return this.getMemoriesByUser(userId).filter(m => m.embedding !== null);
  }
}

// Export singleton instance
export const memoryStore = new MemoryStore();