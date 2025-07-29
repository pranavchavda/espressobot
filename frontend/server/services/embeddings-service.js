import OpenAI from 'openai';

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

class EmbeddingsService {
  constructor() {
    this.model = 'text-embedding-3-large'; // Higher accuracy model
    this.maxTokens = 8191; // Token limit for the model
  }

  // Extract coffee equipment features for better matching
  extractProductFeatures(product) {
    const features = [];
    
    const title = (product.title || '').toLowerCase();
    const vendor = (product.vendor || '').toLowerCase();
    const productType = (product.product_type || '').toLowerCase();
    const description = (product.description || '').toLowerCase();
    
    // Brand/Vendor
    if (vendor) {
      features.push(`brand: ${vendor}`);
    }
    
    // Product Type
    if (productType.includes('espresso') || title.includes('espresso')) {
      features.push('category: espresso machine');
    }
    if (productType.includes('grinder') || title.includes('grinder')) {
      features.push('category: coffee grinder');
    }
    if (title.includes('tamper')) {
      features.push('category: tamper');
    }
    if (title.includes('portafilter')) {
      features.push('category: portafilter');
    }
    if (title.includes('cup') || title.includes('mug')) {
      features.push('category: cup');
    }
    if (title.includes('pitcher') || title.includes('jug')) {
      features.push('category: pitcher');
    }
    
    // Espresso Machine Features
    if (title.includes('dual boiler') || description.includes('dual boiler')) {
      features.push('boiler: dual boiler');
    } else if (title.includes('single boiler') || description.includes('single boiler')) {
      features.push('boiler: single boiler');
    } else if (title.includes('heat exchanger') || description.includes('heat exchanger')) {
      features.push('boiler: heat exchanger');
    }
    
    if (title.includes('pid') || description.includes('pid')) {
      features.push('control: pid temperature control');
    }
    
    if (title.includes('e61') || description.includes('e61')) {
      features.push('group: e61 group head');
    }
    
    if (title.includes('profiling') || description.includes('profiling')) {
      features.push('feature: pressure profiling');
    }
    
    // Grinder Features
    if (title.includes('burr') || description.includes('burr')) {
      features.push('type: burr grinder');
    }
    if (title.includes('conical') || description.includes('conical')) {
      features.push('burr: conical burr');
    }
    if (title.includes('flat') || description.includes('flat')) {
      features.push('burr: flat burr');
    }
    
    if (title.includes('stepless') || description.includes('stepless')) {
      features.push('adjustment: stepless');
    }
    if (title.includes('stepped') || description.includes('stepped')) {
      features.push('adjustment: stepped');
    }
    
    // Size indicators
    if (title.includes('compact') || title.includes('mini')) {
      features.push('size: compact');
    }
    if (title.includes('commercial') || title.includes('pro')) {
      features.push('size: commercial grade');
    }
    
    // Materials
    if (title.includes('stainless steel') || description.includes('stainless steel')) {
      features.push('material: stainless steel');
    }
    if (title.includes('brass') || description.includes('brass')) {
      features.push('material: brass');
    }
    if (title.includes('olive wood') || title.includes('wood')) {
      features.push('material: wood');
    }
    
    // Model numbers and specific identifiers
    const modelMatch = title.match(/\b([A-Z]{2,}[-\s]?\d{2,}[A-Z]*)\b/i);
    if (modelMatch) {
      features.push(`model: ${modelMatch[1].toLowerCase()}`);
    }
    
    // Size specifications
    const sizeMatch = title.match(/(\d+)\s*mm/i);
    if (sizeMatch) {
      features.push(`size: ${sizeMatch[1]}mm`);
    }
    
    return features.join(', ');
  }

  // Generate text for embedding from product data using title + description
  generateProductText(product) {
    // Use full title and description for richer semantic matching
    const parts = [];
    
    // Add vendor/brand
    if (product.vendor) {
      parts.push(`Brand: ${product.vendor}`);
    }
    
    // Add product type
    if (product.product_type) {
      parts.push(`Type: ${product.product_type}`);
    }
    
    // Add full title
    if (product.title) {
      parts.push(`Title: ${product.title}`);
    }
    
    // Add description (clean HTML and truncate if needed)
    if (product.description) {
      const cleanDescription = product.description
        .replace(/<[^>]*>/g, ' ') // Remove HTML tags
        .replace(/\s+/g, ' ')     // Normalize whitespace
        .trim();
      
      if (cleanDescription) {
        // Truncate description to avoid token limits while keeping meaningful content
        const maxDescLength = 800; // Reasonable limit to stay under token limits
        const truncatedDesc = cleanDescription.length > maxDescLength 
          ? cleanDescription.substring(0, maxDescLength) + '...'
          : cleanDescription;
        
        parts.push(`Description: ${truncatedDesc}`);
      }
    }
    
    return parts.join(' | ');
  }

  // Generate embedding for a single product
  async generateEmbedding(product) {
    try {
      const text = this.generateProductText(product);
      
      if (!text.trim()) {
        console.warn('Empty text for embedding generation:', product.id);
        return null;
      }

      const response = await openai.embeddings.create({
        model: this.model,
        input: text,
      });

      const embedding = response.data[0].embedding;
      
      // Return as JSON string for database storage
      return JSON.stringify(embedding);
    } catch (error) {
      console.error('Error generating embedding:', error);
      throw error;
    }
  }

  // Generate embeddings for multiple products (batch processing)
  async generateEmbeddings(products) {
    const results = [];
    const batchSize = 10; // Process in smaller batches to avoid rate limits
    
    for (let i = 0; i < products.length; i += batchSize) {
      const batch = products.slice(i, i + batchSize);
      const batchPromises = batch.map(async (product) => {
        try {
          const embedding = await this.generateEmbedding(product);
          return { product, embedding, success: true };
        } catch (error) {
          console.error(`Failed to generate embedding for product ${product.id}:`, error);
          return { product, embedding: null, success: false, error: error.message };
        }
      });

      const batchResults = await Promise.all(batchPromises);
      results.push(...batchResults);
      
      // Rate limiting - wait between batches
      if (i + batchSize < products.length) {
        await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second delay
      }
    }

    return results;
  }

  // Calculate cosine similarity between two embeddings
  calculateCosineSimilarity(embedding1, embedding2) {
    try {
      const vec1 = typeof embedding1 === 'string' ? JSON.parse(embedding1) : embedding1;
      const vec2 = typeof embedding2 === 'string' ? JSON.parse(embedding2) : embedding2;

      if (!Array.isArray(vec1) || !Array.isArray(vec2)) {
        return 0;
      }

      if (vec1.length !== vec2.length) {
        return 0;
      }

      let dotProduct = 0;
      let norm1 = 0;
      let norm2 = 0;

      for (let i = 0; i < vec1.length; i++) {
        dotProduct += vec1[i] * vec2[i];
        norm1 += vec1[i] * vec1[i];
        norm2 += vec2[i] * vec2[i];
      }

      const magnitude1 = Math.sqrt(norm1);
      const magnitude2 = Math.sqrt(norm2);

      if (magnitude1 === 0 || magnitude2 === 0) {
        return 0;
      }

      return dotProduct / (magnitude1 * magnitude2);
    } catch (error) {
      console.error('Error calculating cosine similarity:', error);
      return 0;
    }
  }

  // Find similar products using embeddings
  async findSimilarProducts(targetEmbedding, candidateProducts, threshold = 0.7) {
    if (!targetEmbedding) return [];

    const similarities = candidateProducts
      .filter(product => product.embedding)
      .map(product => ({
        product,
        similarity: this.calculateCosineSimilarity(targetEmbedding, product.embedding)
      }))
      .filter(result => result.similarity >= threshold)
      .sort((a, b) => b.similarity - a.similarity);

    return similarities;
  }

  // Get embedding statistics
  getEmbeddingStats(embedding) {
    try {
      const vec = typeof embedding === 'string' ? JSON.parse(embedding) : embedding;
      
      if (!Array.isArray(vec)) return null;

      const sum = vec.reduce((acc, val) => acc + val, 0);
      const mean = sum / vec.length;
      const variance = vec.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / vec.length;
      
      return {
        dimensions: vec.length,
        mean: mean,
        variance: variance,
        std_dev: Math.sqrt(variance),
        min: Math.min(...vec),
        max: Math.max(...vec)
      };
    } catch (error) {
      console.error('Error calculating embedding stats:', error);
      return null;
    }
  }
}

export default new EmbeddingsService();