#!/usr/bin/env node
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import memoryOps from '../memory/memory-operations-local.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function importDocumentPrompts(docPath, options = {}) {
  const {
    category = 'domain',
    agentType = 'all',
    priority = 'high',
    tagPrefix = 'doc'
  } = options;

  try {
    // Read the document
    const content = await fs.readFile(docPath, 'utf8');
    const fileName = path.basename(docPath, path.extname(docPath));
    
    // Split into sections by headers
    const sections = content.split(/^#{1,3}\s+/m).filter(s => s.trim());
    
    let imported = 0;
    
    for (const section of sections) {
      const lines = section.trim().split('\n');
      const title = lines[0].trim();
      const body = lines.slice(1).join('\n').trim();
      
      if (body.length < 50) continue; // Skip very short sections
      
      // Create a concise fragment
      const fragment = `${title}:\n${body.substring(0, 500)}${body.length > 500 ? '...' : ''}`;
      
      await memoryOps.addSystemPromptFragment({
        fragment,
        category,
        priority,
        agentType,
        tags: [`${tagPrefix}-${fileName}`, title.toLowerCase().replace(/\s+/g, '-')]
      });
      
      imported++;
    }
    
    console.log(`✅ Imported ${imported} fragments from ${fileName}`);
    return imported;
    
  } catch (error) {
    console.error(`❌ Error importing ${docPath}:`, error);
    return 0;
  }
}

// Import multiple document types
async function importAllDocs() {
  const docsToImport = [
    {
      pattern: '../docs/product-guidelines/*.md',
      options: { category: 'domain', tagPrefix: 'product' }
    },
    {
      pattern: '../docs/workflows/*.md', 
      options: { category: 'workflows', tagPrefix: 'workflow' }
    },
    {
      pattern: '../docs/api-guides/*.md',
      options: { category: 'tools', tagPrefix: 'api' }
    }
  ];
  
  let totalImported = 0;
  
  for (const { pattern, options } of docsToImport) {
    const basePath = path.join(__dirname, pattern);
    const dir = path.dirname(basePath);
    const filePattern = path.basename(basePath);
    
    try {
      const files = await fs.readdir(dir);
      const mdFiles = files.filter(f => f.match(filePattern.replace('*', '.*')));
      
      for (const file of mdFiles) {
        const filePath = path.join(dir, file);
        totalImported += await importDocumentPrompts(filePath, options);
      }
    } catch (error) {
      console.log(`Skipping ${pattern}: ${error.message}`);
    }
  }
  
  console.log(`\n🎉 Total fragments imported: ${totalImported}`);
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  importAllDocs();
}

export { importDocumentPrompts, importAllDocs };