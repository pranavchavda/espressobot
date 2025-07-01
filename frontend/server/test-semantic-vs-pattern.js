#!/usr/bin/env node

/**
 * Compare Pattern Matching vs Semantic Search
 * 
 * This script demonstrates the difference between our two context loading approaches.
 */

import { analyzeContextNeeds } from './context-loader/context-manager.js';
import { createBashAgent } from './tools/bash-tool.js';
import { createSemanticBashAgent } from './agents/semantic-bash-agent.js';
import { run } from '@openai/agents';

const testQueries = [
  {
    name: "Direct Pattern Match",
    query: "Update pricing for products",
    expectedPattern: true
  },
  {
    name: "Ambiguous Business Query",
    query: "Make this product available next month",
    expectedPattern: false  // Pattern won't understand this means preorder
  },
  {
    name: "Complex Workflow",
    query: "Set up a machine and grinder bundle with discount",
    expectedPattern: false  // Pattern might miss combo product connection
  },
  {
    name: "Natural Language",
    query: "How do I handle overselling for items on backorder?",
    expectedPattern: false  // Pattern won't connect overselling to inventory policy
  },
  {
    name: "Specific Tool Query",
    query: "What parameters does manage_features_metaobjects.py accept?",
    expectedPattern: true
  }
];

async function runComparison() {
  console.log('🔍 Pattern Matching vs Semantic Search Comparison\n');
  console.log('=' * 60 + '\n');
  
  for (const test of testQueries) {
    console.log(`### Test: ${test.name}`);
    console.log(`Query: "${test.query}"`);
    console.log('-'.repeat(60));
    
    // Test 1: Pattern Matching
    console.log('\n📊 Pattern Matching Results:');
    const patternContexts = analyzeContextNeeds(test.query);
    console.log(`Contexts found: ${patternContexts.length}`);
    console.log(`Contexts: ${patternContexts.join(', ') || 'None'}`);
    
    // Test 2: Semantic Search (if available)
    console.log('\n🧠 Semantic Search Results:');
    try {
      // Create a test task that uses semantic search
      const semanticTask = `Use ONLY the search_documentation tool to find information about: "${test.query}"
      
      Do NOT execute any bash commands. Just search and summarize what you find.
      Return a list of the most relevant information found.`;
      
      const agent = await createSemanticBashAgent('Test_Semantic_Agent', semanticTask);
      const result = await run(agent, semanticTask);
      
      // Extract key points from result
      if (result && typeof result === 'string') {
        console.log('Found relevant information via semantic search');
        console.log('Preview:', result.substring(0, 200) + '...');
      }
    } catch (error) {
      console.log('Semantic search not available:', error.message);
    }
    
    // Analysis
    console.log('\n📈 Analysis:');
    if (test.expectedPattern && patternContexts.length > 0) {
      console.log('✅ Pattern matching worked as expected');
    } else if (!test.expectedPattern && patternContexts.length === 0) {
      console.log('⚠️  Pattern matching missed context (as expected)');
      console.log('💡 Semantic search would be better for this query');
    } else {
      console.log('🤔 Unexpected result');
    }
    
    console.log('\n' + '='.repeat(60) + '\n');
  }
  
  // Summary
  console.log('📝 Summary:');
  console.log('- Pattern matching is fast and works well for direct queries');
  console.log('- Semantic search understands intent and ambiguous queries');
  console.log('- Best practice: Use semantic search for complex/ambiguous tasks');
  console.log('- Fallback: Pattern matching when semantic unavailable');
}

// Run if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  runComparison().catch(console.error);
}