import { toolResultCache } from './server/memory/tool-result-cache.js';

async function testCacheSearch() {
    const conversationId = '310.0';
    
    // Test different search queries
    const queries = [
        'OB-2505-YYC-138CG-BRE-BCG820XL-RVC',
        'product data for OB-2505-YYC-138CG-BRE-BCG820XL-RVC',
        'get_product OB-2505-YYC-138CG-BRE-BCG820XL-RVC',
        'BCG820XL',
        'open box BCG820XL'
    ];
    
    console.log(`Testing cache search for conversation ${conversationId}\n`);
    
    for (const query of queries) {
        console.log(`\nSearching for: "${query}"`);
        const results = await toolResultCache.search(conversationId, query, {
            toolName: 'get_product',
            limit: 3,
            similarityThreshold: 0.75
        });
        
        console.log(`Found ${results.length} results`);
        if (results.length > 0) {
            console.log(`Top result similarity: ${results[0].similarity}`);
            console.log(`Input params: ${JSON.stringify(results[0].input).substring(0, 100)}`);
        }
    }
    
    // Also check without toolName filter
    console.log('\n\nSearching without tool filter:');
    const allResults = await toolResultCache.search(conversationId, 'OB-2505-YYC-138CG-BRE-BCG820XL-RVC', {
        limit: 5,
        similarityThreshold: 0.75
    });
    
    console.log(`Found ${allResults.length} results total`);
    allResults.forEach((result, i) => {
        console.log(`${i+1}. Tool: ${result.tool}, Similarity: ${result.similarity}`);
    });
}

testCacheSearch().catch(console.error);