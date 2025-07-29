const { PrismaClient } = require('@prisma/client');
const prisma = new PrismaClient();

// Copy the ProductMatcher class
class ProductMatcher {
  constructor() {
    this.weights = {
      embedding: 0.4,    
      title: 0.18,       
      vendor: 0.24,      
      price: 0.06,       
      sku: 0,            
      type: 0.12         
    };
    
    this.thresholds = {
      high_confidence: 0.80,    
      medium_confidence: 0.70,  
      low_confidence: 0.60      
    };
  }

  calculateStringSimilarity(str1, str2) {
    if (!str1 || !str2) return 0;
    
    str1 = str1.toLowerCase().trim();
    str2 = str2.toLowerCase().trim();
    
    if (str1 === str2) return 1;
    
    const matrix = [];
    const len1 = str1.length;
    const len2 = str2.length;

    for (let i = 0; i <= len2; i++) {
      matrix[i] = [i];
    }

    for (let j = 0; j <= len1; j++) {
      matrix[0][j] = j;
    }

    for (let i = 1; i <= len2; i++) {
      for (let j = 1; j <= len1; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }

    const maxLen = Math.max(len1, len2);
    return (maxLen - matrix[len2][len1]) / maxLen;
  }

  calculateTitleSimilarity(title1, title2) {
    if (!title1 || !title2) return 0;

    const basicSimilarity = this.calculateStringSimilarity(title1, title2);
    
    const stopWords = ['the', 'and', 'or', 'with', 'for', 'espresso', 'coffee', 'machine', 'grinder'];
    const extractKeyTerms = (title) => {
      return title.toLowerCase()
        .replace(/[^\w\s]/g, ' ')
        .split(/\s+/)
        .filter(word => word.length > 2 && !stopWords.includes(word))
        .sort();
    };

    const terms1 = extractKeyTerms(title1);
    const terms2 = extractKeyTerms(title2);
    
    const commonTerms = terms1.filter(term => terms2.includes(term));
    const termSimilarity = commonTerms.length / Math.max(terms1.length, terms2.length, 1);
    
    return (basicSimilarity * 0.6) + (termSimilarity * 0.4);
  }

  calculateVendorSimilarity(vendor1, vendor2) {
    if (!vendor1 || !vendor2) return 0;
    
    const v1 = vendor1.toLowerCase().trim();
    const v2 = vendor2.toLowerCase().trim();
    
    if (v1 === v2) return 1;
    
    if (v1.includes(v2) || v2.includes(v1)) return 0.8;
    
    return this.calculateStringSimilarity(v1, v2);
  }

  calculatePriceSimilarity(price1, price2) {
    if (!price1 || !price2 || price1 <= 0 || price2 <= 0) return 0;
    
    const priceDiff = Math.abs(price1 - price2);
    const avgPrice = (price1 + price2) / 2;
    const relativeError = priceDiff / avgPrice;
    
    if (relativeError <= 0.05) return 1;      
    if (relativeError <= 0.15) return 0.8;    
    if (relativeError <= 0.30) return 0.6;    
    if (relativeError <= 0.50) return 0.4;    
    
    return Math.max(0, 1 - relativeError);
  }

  calculateTypeSimilarity(type1, type2) {
    if (!type1 || !type2) return 0;
    
    const t1 = type1.toLowerCase().trim();
    const t2 = type2.toLowerCase().trim();
    
    if (t1 === t2) return 1;
    
    const categories = {
      'espresso': ['espresso-machines', 'coffee-machines', 'automatic', 'semi-automatic'],
      'grinder': ['grinders', 'burr-grinder', 'coffee-grinder'],
      'accessory': ['accessories', 'parts', 'cleaning']
    };
    
    for (const [category, terms] of Object.entries(categories)) {
      if (terms.some(term => t1.includes(term)) && terms.some(term => t2.includes(term))) {
        return 0.8;
      }
    }
    
    return this.calculateStringSimilarity(t1, t2);
  }

  calculateCosineSimilarity(embedding1, embedding2) {
    if (!embedding1 || !embedding2) return 0;
    
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
      console.error('Error calculating embedding similarity:', error);
      return 0;
    }
  }

  calculateSimilarity(idcProduct, competitorProduct) {
    const titleScore = this.calculateTitleSimilarity(idcProduct.title, competitorProduct.title);
    const vendorScore = this.calculateVendorSimilarity(idcProduct.vendor, competitorProduct.vendor);
    const priceScore = this.calculatePriceSimilarity(parseFloat(idcProduct.price), parseFloat(competitorProduct.price));
    const typeScore = this.calculateTypeSimilarity(idcProduct.product_type, competitorProduct.product_type);
    const embeddingScore = this.calculateCosineSimilarity(idcProduct.embedding, competitorProduct.embedding);

    console.log('Raw scores before clamping:');
    console.log(`  Title: ${titleScore}`);
    console.log(`  Vendor: ${vendorScore}`);
    console.log(`  Price: ${priceScore}`);
    console.log(`  Type: ${typeScore}`);

    const clampedScores = {
      titleScore: Math.max(0, Math.min(1, titleScore)),
      vendorScore: Math.max(0, Math.min(1, vendorScore)),
      priceScore: Math.max(0, Math.min(1, priceScore)),
      typeScore: Math.max(0, Math.min(1, typeScore)),
      embeddingScore: Math.max(0, Math.min(1, embeddingScore))
    };

    console.log('Weighted contributions:');
    console.log(`  Title: ${clampedScores.titleScore} * ${this.weights.title} = ${clampedScores.titleScore * this.weights.title}`);
    console.log(`  Vendor: ${clampedScores.vendorScore} * ${this.weights.vendor} = ${clampedScores.vendorScore * this.weights.vendor}`);
    console.log(`  Price: ${clampedScores.priceScore} * ${this.weights.price} = ${clampedScores.priceScore * this.weights.price}`);
    console.log(`  Type: ${clampedScores.typeScore} * ${this.weights.type} = ${clampedScores.typeScore * this.weights.type}`);
    console.log(`  Embedding: ${clampedScores.embeddingScore} * ${this.weights.embedding} = ${clampedScores.embeddingScore * this.weights.embedding}`);

    const overallScore = 
      (clampedScores.embeddingScore * this.weights.embedding) +
      (clampedScores.titleScore * this.weights.title) +
      (clampedScores.vendorScore * this.weights.vendor) +
      (clampedScores.priceScore * this.weights.price) +
      (clampedScores.typeScore * this.weights.type);

    return {
      overall_score: Math.max(0, Math.min(1, overallScore)),
      embedding_similarity: clampedScores.embeddingScore,
      title_similarity: clampedScores.titleScore,
      brand_similarity: clampedScores.vendorScore,
      price_similarity: clampedScores.priceScore,
      type_similarity: clampedScores.typeScore
    };
  }
}

async function testSpecificMatch() {
  const matcher = new ProductMatcher();

  // Get the specific ECM products
  const kitchenBarista = await prisma.competitors.findFirst({
    where: { name: 'The Kitchen Barista' }
  });

  const kbProduct = await prisma.competitor_products.findFirst({
    where: { 
      competitor_id: kitchenBarista.id,
      title: { contains: 'ECM Mechanika Max' }
    }
  });

  const idcProduct = await prisma.idc_products.findFirst({
    where: { 
      vendor: 'ECM',
      title: { contains: 'Mechanika Max' }
    }
  });

  if (!kbProduct || !idcProduct) {
    console.log('Could not find both products');
    console.log('KB Product found:', !!kbProduct);
    console.log('IDC Product found:', !!idcProduct);
    return;
  }

  console.log('=== MANUAL MATCHING TEST ===');
  console.log('Kitchen Barista Product:');
  console.log(`  Title: ${kbProduct.title}`);
  console.log(`  Vendor: ${kbProduct.vendor}`);
  console.log(`  Price: ${kbProduct.price}`);
  console.log(`  Type: ${kbProduct.product_type}`);
  
  console.log('\niDC Product:');
  console.log(`  Title: ${idcProduct.title}`);
  console.log(`  Vendor: ${idcProduct.vendor}`);
  console.log(`  Price: ${idcProduct.price}`);
  console.log(`  Type: ${idcProduct.product_type}`);

  console.log('\n=== DETAILED MATCHING CALCULATION ===');
  const similarity = matcher.calculateSimilarity(idcProduct, kbProduct);
  
  console.log('\n=== FINAL SIMILARITY SCORES ===');
  console.log(`Overall Score: ${(similarity.overall_score * 100).toFixed(1)}%`);
  console.log(`Title Similarity: ${(similarity.title_similarity * 100).toFixed(1)}%`);
  console.log(`Vendor Similarity: ${(similarity.brand_similarity * 100).toFixed(1)}%`);  
  console.log(`Price Similarity: ${(similarity.price_similarity * 100).toFixed(1)}%`);
  console.log(`Type Similarity: ${(similarity.type_similarity * 100).toFixed(1)}%`);
  console.log(`Embedding Similarity: ${(similarity.embedding_similarity * 100).toFixed(1)}%`);

  // Check if this meets the threshold
  console.log(`\nWould this match? ${similarity.overall_score >= 0.60 ? 'YES' : 'NO'}`);
  console.log(`Confidence level: ${similarity.overall_score >= 0.8 ? 'high' : similarity.overall_score >= 0.7 ? 'medium' : similarity.overall_score >= 0.6 ? 'low' : 'very_low'}`);

  await prisma.$disconnect();
}

testSpecificMatch().catch(console.error);