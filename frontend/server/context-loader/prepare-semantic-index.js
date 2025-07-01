#!/usr/bin/env node

/**
 * Prepare documentation for future semantic indexing
 * 
 * This script extracts all documentation sections and prepares them
 * in a format that can be easily vectorized when we move to semantic search.
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { CONTEXT_FILES } from './context-manager.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Extract all sections from documentation
 */
async function extractAllSections() {
  const sections = [];
  const processedFiles = new Set();
  
  for (const [contextKey, config] of Object.entries(CONTEXT_FILES)) {
    const filePath = path.join(__dirname, config.file);
    
    // Extract section if specified, otherwise use whole file
    try {
      let content;
      let fileContent;
      
      // Only read each file once
      if (!processedFiles.has(filePath)) {
        fileContent = await fs.readFile(filePath, 'utf-8');
        processedFiles.add(filePath);
      }
      
      if (config.section) {
        // Extract specific section
        content = await extractSection(fileContent || await fs.readFile(filePath, 'utf-8'), config.section);
      } else {
        content = fileContent || await fs.readFile(filePath, 'utf-8');
      }
      
      sections.push({
        id: contextKey,
        file: config.file,
        section: config.section || 'full_document',
        content: content,
        contentLength: content.length,
        metadata: {
          category: determineCategory(config.file),
          keywords: extractKeywords(content),
          lastModified: new Date().toISOString()
        }
      });
      
    } catch (error) {
      console.error(`Error processing ${contextKey}:`, error.message);
    }
  }
  
  return sections;
}

/**
 * Extract section from content
 */
async function extractSection(content, sectionHeader) {
  const lines = content.split('\n');
  let inSection = false;
  let sectionContent = [];
  let sectionLevel = 0;
  
  for (const line of lines) {
    if (line.trim() === sectionHeader) {
      inSection = true;
      sectionLevel = line.match(/^#+/)?.[0].length || 0;
      sectionContent.push(line);
      continue;
    }
    
    if (inSection) {
      const currentLevel = line.match(/^#+/)?.[0].length || 0;
      if (currentLevel > 0 && currentLevel <= sectionLevel && line !== sectionHeader) {
        break;
      }
      sectionContent.push(line);
    }
  }
  
  return sectionContent.join('\n').trim();
}

/**
 * Determine category from file path
 */
function determineCategory(filePath) {
  if (filePath.includes('business-rules')) return 'business_rules';
  if (filePath.includes('TOOL_USAGE')) return 'tool_documentation';
  if (filePath.includes('WORKFLOW')) return 'workflows';
  if (filePath.includes('prompts')) return 'prompts';
  return 'other';
}

/**
 * Extract keywords from content (simple implementation)
 */
function extractKeywords(content) {
  // Extract tool names
  const toolMatches = content.match(/\b(manage_\w+|create_\w+|update_\w+|bulk_\w+)\.py/g) || [];
  
  // Extract key business terms
  const businessTerms = [];
  const terms = ['preorder', 'pricing', 'inventory', 'tags', 'features', 'combo', 'open-box', 'bulk', 'GraphQL'];
  for (const term of terms) {
    if (content.toLowerCase().includes(term.toLowerCase())) {
      businessTerms.push(term);
    }
  }
  
  return [...new Set([...toolMatches.map(t => t.replace('.py', '')), ...businessTerms])];
}

/**
 * Prepare chunk strategy for large documents
 */
function prepareChunks(sections, maxChunkSize = 2000) {
  const chunks = [];
  
  for (const section of sections) {
    if (section.content.length <= maxChunkSize) {
      chunks.push(section);
    } else {
      // Split large sections into semantic chunks
      const paragraphs = section.content.split('\n\n');
      let currentChunk = '';
      let chunkIndex = 0;
      
      for (const paragraph of paragraphs) {
        if (currentChunk.length + paragraph.length > maxChunkSize && currentChunk) {
          chunks.push({
            ...section,
            id: `${section.id}_chunk_${chunkIndex}`,
            content: currentChunk,
            contentLength: currentChunk.length,
            metadata: {
              ...section.metadata,
              chunkIndex: chunkIndex,
              totalChunks: Math.ceil(section.content.length / maxChunkSize)
            }
          });
          currentChunk = paragraph;
          chunkIndex++;
        } else {
          currentChunk += (currentChunk ? '\n\n' : '') + paragraph;
        }
      }
      
      // Add final chunk
      if (currentChunk) {
        chunks.push({
          ...section,
          id: `${section.id}_chunk_${chunkIndex}`,
          content: currentChunk,
          contentLength: currentChunk.length,
          metadata: {
            ...section.metadata,
            chunkIndex: chunkIndex,
            totalChunks: Math.ceil(section.content.length / maxChunkSize)
          }
        });
      }
    }
  }
  
  return chunks;
}

/**
 * Main function
 */
async function main() {
  console.log('🔍 Extracting documentation sections...\n');
  
  // Extract all sections
  const sections = await extractAllSections();
  console.log(`✅ Extracted ${sections.length} sections\n`);
  
  // Prepare chunks
  const chunks = prepareChunks(sections);
  console.log(`📦 Prepared ${chunks.length} chunks for indexing\n`);
  
  // Save to JSON for future processing
  const outputPath = path.join(__dirname, 'semantic-index-data.json');
  await fs.writeFile(
    outputPath,
    JSON.stringify({
      metadata: {
        created: new Date().toISOString(),
        totalSections: sections.length,
        totalChunks: chunks.length,
        categories: [...new Set(chunks.map(c => c.metadata.category))]
      },
      chunks: chunks
    }, null, 2)
  );
  
  console.log(`💾 Saved to ${outputPath}\n`);
  
  // Show statistics
  console.log('📊 Statistics:');
  console.log('=============');
  
  const stats = {
    byCategory: {},
    byFile: {},
    totalSize: 0
  };
  
  for (const chunk of chunks) {
    const category = chunk.metadata.category;
    const file = chunk.file;
    
    stats.byCategory[category] = (stats.byCategory[category] || 0) + 1;
    stats.byFile[file] = (stats.byFile[file] || 0) + 1;
    stats.totalSize += chunk.contentLength;
  }
  
  console.log('\nBy Category:');
  for (const [cat, count] of Object.entries(stats.byCategory)) {
    console.log(`  ${cat}: ${count} chunks`);
  }
  
  console.log('\nBy File:');
  for (const [file, count] of Object.entries(stats.byFile)) {
    console.log(`  ${file}: ${count} chunks`);
  }
  
  console.log(`\nTotal size: ${(stats.totalSize / 1024).toFixed(2)} KB`);
  console.log('\n✨ Ready for semantic indexing when needed!');
  
  // Show sample for verification
  console.log('\n📝 Sample chunk:');
  console.log('================');
  const sample = chunks[Math.floor(chunks.length / 2)];
  console.log(`ID: ${sample.id}`);
  console.log(`Keywords: ${sample.metadata.keywords.join(', ')}`);
  console.log(`Content preview: ${sample.content.substring(0, 200)}...`);
}

// Run if executed directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

export { extractAllSections, prepareChunks };