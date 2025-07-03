#!/usr/bin/env node

/**
 * Script to search and display tool documentation
 */

import { memoryOperations } from '../server/memory/memory-operations-local.js';

async function searchToolDocs(query = '', category = 'tools') {
  try {
    console.log(`🔍 Searching tool documentation for: "${query}"\n`);
    
    let results;
    if (query) {
      // Search for specific tools
      results = await memoryOperations.searchSystemPromptFragments(query, 50);
    } else {
      // Get all tool documentation
      results = await memoryOperations.getAllSystemPromptFragments();
    }
    
    // Filter for tools only
    const toolDocs = results.filter(doc => 
      doc.metadata?.category === category && 
      doc.metadata?.tool_name
    );
    
    if (toolDocs.length === 0) {
      console.log('No tool documentation found matching your criteria.');
      return;
    }
    
    // Group by tool type
    const groupedTools = {};
    toolDocs.forEach(doc => {
      const toolType = doc.metadata?.tool_type || 'unknown';
      if (!groupedTools[toolType]) {
        groupedTools[toolType] = [];
      }
      groupedTools[toolType].push(doc);
    });
    
    // Display results
    console.log(`📚 Found ${toolDocs.length} tool documentation entries:\n`);
    
    Object.keys(groupedTools).sort().forEach(toolType => {
      console.log(`\n📁 ${toolType.toUpperCase()} TOOLS:`);
      console.log('='.repeat(50));
      
      groupedTools[toolType]
        .sort((a, b) => a.metadata.tool_name.localeCompare(b.metadata.tool_name))
        .forEach(doc => {
          const priority = doc.metadata?.priority || 'medium';
          const priorityIcon = priority === 'high' ? '🔴' : priority === 'medium' ? '🟡' : '🟢';
          const tags = doc.metadata?.tags || [];
          
          console.log(`\n${priorityIcon} ${doc.metadata.tool_name}`);
          console.log(`   Tags: ${tags.join(', ')}`);
          
          // Show first few lines of documentation
          const lines = doc.memory.split('\n');
          const purposeLine = lines.find(line => line.includes('**Purpose**'));
          if (purposeLine) {
            console.log(`   ${purposeLine.replace(/\*\*/g, '')}`);
          }
          
          const pathLine = lines.find(line => line.includes('**Python Path**') || line.includes('**Access**'));
          if (pathLine) {
            console.log(`   ${pathLine.replace(/\*\*/g, '')}`);
          }
        });
    });
    
    console.log(`\n\n💡 Use --show-full to see complete documentation for any tool`);
    console.log(`   Example: node scripts/search-tool-docs.js search_products --show-full`);
    
  } catch (error) {
    console.error('Error searching tool documentation:', error);
    process.exit(1);
  }
}

async function showFullDoc(toolName) {
  try {
    console.log(`📖 Full documentation for: ${toolName}\n`);
    
    const results = await memoryOperations.searchSystemPromptFragments(toolName, 10);
    const toolDoc = results.find(doc => 
      doc.metadata?.tool_name === toolName && 
      doc.metadata?.category === 'tools'
    );
    
    if (!toolDoc) {
      console.log(`❌ No documentation found for tool: ${toolName}`);
      console.log(`\nAvailable tools:`);
      
      const allTools = await memoryOperations.getAllSystemPromptFragments();
      const toolNames = allTools
        .filter(doc => doc.metadata?.category === 'tools' && doc.metadata?.tool_name)
        .map(doc => doc.metadata.tool_name)
        .sort();
        
      toolNames.forEach(name => console.log(`   - ${name}`));
      return;
    }
    
    console.log(toolDoc.memory);
    console.log(`\n📊 Metadata:`);
    console.log(`   Priority: ${toolDoc.metadata?.priority || 'medium'}`);
    console.log(`   Type: ${toolDoc.metadata?.tool_type || 'unknown'}`);
    console.log(`   Tags: ${(toolDoc.metadata?.tags || []).join(', ')}`);
    console.log(`   Created: ${toolDoc.createdAt || 'unknown'}`);
    
  } catch (error) {
    console.error('Error showing full documentation:', error);
    process.exit(1);
  }
}

// Command line interface
async function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0) {
    // Show all tools
    await searchToolDocs();
  } else if (args.includes('--show-full')) {
    // Show full documentation for specific tool
    const toolName = args.find(arg => !arg.startsWith('--'));
    if (!toolName) {
      console.log('❌ Please specify a tool name with --show-full');
      console.log('   Example: node scripts/search-tool-docs.js search_products --show-full');
      process.exit(1);
    }
    await showFullDoc(toolName);
  } else if (args.includes('--list-categories')) {
    // List all categories
    const allDocs = await memoryOperations.getAllSystemPromptFragments();
    const categories = [...new Set(allDocs.map(doc => doc.metadata?.category).filter(Boolean))];
    console.log('📂 Available categories:');
    categories.sort().forEach(cat => console.log(`   - ${cat}`));
  } else {
    // Search for specific query
    const query = args.join(' ');
    await searchToolDocs(query);
  }
}

// Help text
if (process.argv.includes('--help') || process.argv.includes('-h')) {
  console.log(`
🛠️  Tool Documentation Search

Usage:
  node scripts/search-tool-docs.js [query] [options]

Examples:
  node scripts/search-tool-docs.js                     # Show all tools
  node scripts/search-tool-docs.js shopify             # Search for shopify tools
  node scripts/search-tool-docs.js python              # Show python tools
  node scripts/search-tool-docs.js search_products --show-full  # Full docs for search_products
  node scripts/search-tool-docs.js --list-categories   # List all categories

Options:
  --show-full     Show complete documentation for a tool
  --list-categories  List all available categories
  --help, -h      Show this help message
`);
  process.exit(0);
}

main().catch(console.error);