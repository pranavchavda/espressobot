#!/usr/bin/env node

import prisma from '../server/lib/prisma.js';

async function analyzeProfiletecMatching() {
    try {        
        console.log('🔍 Analyzing Profitec Matching Issues\n');
        console.log('=' .repeat(50));
        
        // Get all IDC Profitec products
        const idcProducts = await prisma.idc_products.findMany({
            where: {
                vendor: {
                    contains: 'Profitec',
                    mode: 'insensitive'
                }
            },
            orderBy: { price: 'desc' }
        });
        
        // Get all competitor Profitec products
        const competitorProducts = await prisma.competitor_products.findMany({
            where: {
                vendor: {
                    contains: 'Profitec',
                    mode: 'insensitive'
                }
            },
            include: {
                competitor: true
            },
            orderBy: { price: 'desc' }
        });
                
        console.log(`📊 IDC Profitec Products: ${idcProducts.length}`);
        console.log(`🏪 Competitor Profitec Products: ${competitorProducts.length}\n`);
        
        // Analyze title patterns
        console.log('🎯 IDC Product Title Patterns:');
        console.log('=' .repeat(30));
        const idcTitlePatterns = {};
        idcProducts.forEach(product => {
            const key = product.title.replace(/\s+(w\/|with|&|\+).*$/i, '').trim();
            if (!idcTitlePatterns[key]) idcTitlePatterns[key] = 0;
            idcTitlePatterns[key]++;
        });
        
        Object.entries(idcTitlePatterns)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .forEach(([pattern, count]) => {
                console.log(`  ${pattern} (${count})`);
            });
        
        console.log('\n🏪 Competitor Product Title Patterns:');
        console.log('=' .repeat(35));
        const compTitlePatterns = {};
        competitorProducts.forEach(product => {
            const key = product.title.replace(/\s+\([^)]+\).*$/i, '').trim();
            if (!compTitlePatterns[key]) compTitlePatterns[key] = 0;
            compTitlePatterns[key]++;
        });
        
        Object.entries(compTitlePatterns)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10)
            .forEach(([pattern, count]) => {
                console.log(`  ${pattern} (${count})`);
            });
                
        // Find potential matches by model number
        console.log('\n🔍 Potential Matches by Model:');
        console.log('=' .repeat(30));
        
        const potentialMatches = [];
        
        idcProducts.forEach(idcProduct => {
            // Extract model numbers (Pro 500, Pro 400, etc.)
            const idcModel = idcProduct.title.match(/Pro\s+\d+|Go\s*(?:Single)?|Drive|T\d+/i);
            if (!idcModel) return;
            
            competitorProducts.forEach(compProduct => {
                const compModel = compProduct.title.match(/Pro\s+\d+|Go\s*(?:Single)?|Drive|T\d+/i);
                if (!compModel) return;
                
                if (idcModel[0].toLowerCase().replace(/\s+/g, '') === 
                    compModel[0].toLowerCase().replace(/\s+/g, '')) {
                    
                    const idcPrice = parseFloat(idcProduct.price) || 0;
                    const compPrice = parseFloat(compProduct.price) || 0;
                    const priceDiff = Math.abs(idcPrice - compPrice);
                    const priceDiffPct = (priceDiff / Math.max(idcPrice, compPrice)) * 100;
                    
                    potentialMatches.push({
                        idcTitle: idcProduct.title,
                        compTitle: compProduct.title,  
                        idcPrice: idcPrice,
                        compPrice: compPrice,
                        priceDiff: priceDiff,
                        priceDiffPct: priceDiffPct.toFixed(1),
                        model: idcModel[0],
                        source: compProduct.competitor?.domain || 'Unknown'
                    });
                }
            });
        });
        
        // Sort by price difference
        potentialMatches.sort((a, b) => a.priceDiff - b.priceDiff);
        
        console.log(`Found ${potentialMatches.length} potential matches:\n`);
        
        potentialMatches.slice(0, 10).forEach((match, i) => {
            console.log(`${i + 1}. ${match.model} Match:`);
            console.log(`   IDC: ${match.idcTitle} ($${match.idcPrice})`);
            console.log(`   Comp: ${match.compTitle} ($${match.compPrice})`);
            console.log(`   Price Diff: $${match.priceDiff} (${match.priceDiffPct}%)`);
            console.log(`   Source: ${match.source}\n`);
        });
        
        // Check existing matches
        const existingMatches = await prisma.product_matches.count({
            where: {
                idc_product: {
                    vendor: {
                        contains: 'Profitec',
                        mode: 'insensitive'
                    }
                }
            }
        });
        
        console.log(`\n📈 Current Profitec Matches: ${existingMatches}`);
        
        // Recommendations
        console.log('\n💡 Recommendations:');
        console.log('=' .repeat(20));
        console.log('1. Title normalization needed - IDC uses "w/" while competitors use "(Color)"');
        console.log('2. Model-based matching could work well for Profitec');
        console.log('3. Price differences are reasonable for most matches');
        console.log('4. Consider lowering similarity threshold for Profitec specifically');
        
        if (potentialMatches.length > 0) {
            console.log(`\n🎯 Best Match Candidate:`);
            const best = potentialMatches[0];
            console.log(`   Model: ${best.model}`);
            console.log(`   Price Similarity: ${(100 - parseFloat(best.priceDiffPct)).toFixed(1)}%`);
            console.log(`   Should be matched with similarity threshold ~0.6-0.7`);
        }
        
    } catch (error) {
        console.error('Error analyzing Profitec matching:', error);
    } finally {
        await prisma.$disconnect();
    }
}

// Run the analysis
analyzeProfiletecMatching().catch(console.error);