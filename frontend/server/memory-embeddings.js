import OpenAI from 'openai';
import { memoryStore } from './memory-store.js';

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY
});

// Calculate cosine similarity between two vectors
export function cosineSimilarity(vecA, vecB) {
  if (!vecA || !vecB || vecA.length !== vecB.length) {
    return 0;
  }
  
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  
  for (let i = 0; i < vecA.length; i++) {
    dotProduct += vecA[i] * vecB[i];
    normA += vecA[i] * vecA[i];
    normB += vecB[i] * vecB[i];
  }
  
  normA = Math.sqrt(normA);
  normB = Math.sqrt(normB);
  
  if (normA === 0 || normB === 0) {
    return 0;
  }
  
  return dotProduct / (normA * normB);
}

// Generate embedding for a text
export async function generateEmbedding(text) {
  try {
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: text,
    });
    
    return response.data[0].embedding;
  } catch (error) {
    console.error('Error generating embedding:', error);
    return null;
  }
}

// Find most relevant memories using semantic search
export async function findRelevantMemories(query, userId, topK = 3) {
  try {
    // Generate embedding for the query
    const queryEmbedding = await generateEmbedding(query);
    if (!queryEmbedding) {
      console.error('Failed to generate query embedding');
      return [];
    }
    
    // Get all memories with embeddings for this user
    const memories = memoryStore.getMemoriesWithEmbeddings(userId);
    
    if (memories.length === 0) {
      return [];
    }
    
    // Calculate similarity scores
    const memoriesWithScores = memories.map(memory => ({
      memory,
      score: cosineSimilarity(queryEmbedding, memory.embedding)
    }));
    
    // Sort by similarity score (descending)
    memoriesWithScores.sort((a, b) => b.score - a.score);
    
    // Filter out low relevance memories (threshold: 0.7)
    const relevantMemories = memoriesWithScores
      .filter(item => item.score > 0.7)
      .slice(0, topK)
      .map(item => ({
        ...item.memory,
        relevance_score: item.score
      }));
    
    console.log(`Found ${relevantMemories.length} relevant memories for query`);
    return relevantMemories;
  } catch (error) {
    console.error('Error finding relevant memories:', error);
    return [];
  }
}

// Update embeddings for memories that don't have them
export async function updateMissingEmbeddings(userId) {
  try {
    const memories = memoryStore.getMemoriesByUser(userId);
    let updated = 0;
    
    for (const memory of memories) {
      if (!memory.embedding) {
        const embedding = await generateEmbedding(memory.content);
        if (embedding) {
          memoryStore.updateMemory(memory.id, { embedding });
          updated++;
        }
        
        // Rate limit: wait 100ms between requests
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }
    
    console.log(`Updated embeddings for ${updated} memories`);
    return updated;
  } catch (error) {
    console.error('Error updating embeddings:', error);
    return 0;
  }
}

// Format memories for agent context
export function formatMemoriesForContext(memories) {
  if (!memories || memories.length === 0) {
    return '';
  }
  
  const formattedMemories = memories.map((memory, index) => {
    const importance = memory.metadata?.importance || 'medium';
    const category = memory.category || 'general';
    return `${index + 1}. [${category.toUpperCase()} - ${importance}] ${memory.content}`;
  }).join('\n');
  
  return `
=== RELEVANT MEMORIES FROM PREVIOUS CONVERSATIONS ===
${formattedMemories}
=== END OF MEMORIES ===
`;
}