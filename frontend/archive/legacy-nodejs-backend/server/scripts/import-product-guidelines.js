#!/usr/bin/env node
/**
 * Import Product Guidelines into Prompt Library
 * 
 * This script takes the generated product guidelines and imports them
 * as individual fragments into the prompt library for RAG retrieval.
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';
import { memoryOperations as memoryOps } from '../memory/memory-operations-local.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function importProductGuidelines() {
  console.log('📚 Importing product guidelines into prompt library...\n');
  
  try {
    // Read the structured data
    const dataPath = path.join(__dirname, '../prompts/product-guidelines-structured.json');
    const data = JSON.parse(await fs.readFile(dataPath, 'utf8'));
    
    let imported = 0;
    
    // Import Key Principles
    if (data.principles && data.principles.length > 0) {
      const principlesFragment = `# Key Business Principles for ${data.brand}

${data.principles.map(p => `- ${p}`).join('\n')}

These principles guide all product creation and content decisions.`;
      
      await memoryOps.addSystemPromptFragment(principlesFragment, {
        category: 'domain',
        priority: 'high',
        agent_type: 'all',
        tags: ['principles', 'guidelines', 'business-rules']
      });
      imported++;
      console.log('✅ Imported key principles');
    }
    
    // Import Core Requirements
    if (data.requirements && data.requirements.length > 0) {
      const requirementsFragment = `# Core Product Requirements

Every product in Shopify must include:
${data.requirements.map(r => `- ${r}`).join('\n')}

These are mandatory fields that must be filled for all products.`;
      
      await memoryOps.addSystemPromptFragment(requirementsFragment, {
        category: 'constraints',
        priority: 'high',
        agent_type: 'all',
        tags: ['requirements', 'product-creation', 'mandatory']
      });
      imported++;
      console.log('✅ Imported core requirements');
    }
    
    // Import Metafields (in chunks for better retrieval)
    if (data.metafields && data.metafields.length > 0) {
      // Core metafields (first 5)
      const coreMetafields = data.metafields.slice(0, 5);
      const coreMetafieldsFragment = `# Core Product Metafields

Essential metafields for product data:
${coreMetafields.map(m => `- **${m.name}**: \`${m.namespace}.${m.key}\``).join('\n')}

These metafields store primary product information and content.`;
      
      await memoryOps.addSystemPromptFragment(coreMetafieldsFragment, {
        category: 'tools',
        priority: 'high',
        agent_type: 'swe',
        tags: ['metafields', 'core-fields', 'product-data']
      });
      imported++;
      
      // Additional metafields
      const additionalMetafields = data.metafields.slice(5);
      const additionalMetafieldsFragment = `# Additional Product Metafields

Extended metafields for specialized data:
${additionalMetafields.map(m => `- **${m.name}**: \`${m.namespace}.${m.key}\``).join('\n')}

These fields handle reviews, variants, promotions, and other extended features.`;
      
      await memoryOps.addSystemPromptFragment(additionalMetafieldsFragment, {
        category: 'tools',
        priority: 'medium',
        agent_type: 'swe',
        tags: ['metafields', 'extended-fields', 'product-data']
      });
      imported++;
      console.log('✅ Imported metafields reference');
    }
    
    // Import Tag Categories
    if (data.tags && data.tags.length > 0) {
      for (const tagCategory of data.tags) {
        const tagFragment = `# Product Tags: ${tagCategory.category}

Tags for ${tagCategory.category}:
${tagCategory.tags.map(t => `- \`${t}\``).join('\n')}

${tagCategory.category.includes('icon') ? 'These icon tags trigger visual badges on product pages.' : ''}
${tagCategory.category.includes('NC_') ? 'Collection tags (NC_*) are used for automatic collection building.' : ''}
${tagCategory.category.includes('Prefixes') ? 'Use these prefixes to create structured tags (e.g., ROAST-Medium, REGION-Colombia).' : ''}`;
        
        await memoryOps.addSystemPromptFragment(tagFragment, {
          category: 'domain',
          priority: tagCategory.category.includes('Important') ? 'high' : 'medium',
          agent_type: 'all',
          tags: ['tags', 'product-tags', tagCategory.category.toLowerCase().replace(/\s+/g, '-')]
        });
        imported++;
      }
      console.log(`✅ Imported ${data.tags.length} tag categories`);
    }
    
    // Import Coffee-Specific Guidelines
    if (data.coffeeSpecific && data.coffeeSpecific.length > 0) {
      const coffeeFragment = `# Coffee Product Tag Structure

For coffee products, use these specific tag formats:
${data.coffeeSpecific.map(c => `- ${c}`).join('\n')}

Important Notes:
- For NOTES tags, use # to separate multiple values (e.g., NOTES-Chocolate#Caramel#Citrus)
- All coffee products should have origin tags (origin-{country})
- Roast levels: Light, Medium, Medium-Dark, Dark
- Processing methods: Washed, Natural, Honey, Anaerobic`;
      
      await memoryOps.addSystemPromptFragment(coffeeFragment, {
        category: 'domain',
        priority: 'high',
        agent_type: 'all',
        tags: ['coffee', 'coffee-tags', 'product-guidelines']
      });
      imported++;
      console.log('✅ Imported coffee-specific guidelines');
    }
    
    // Import Workflow Steps
    if (data.workflow && data.workflow.length > 0) {
      const workflowFragment = `# Product Creation Workflow

Step-by-step process for creating products:

${data.workflow.join('\n\n')}

Always follow this workflow to ensure consistent product creation.`;
      
      await memoryOps.addSystemPromptFragment(workflowFragment, {
        category: 'workflows',
        priority: 'high',
        agent_type: 'all',
        tags: ['workflow', 'product-creation', 'process']
      });
      imported++;
      console.log('✅ Imported workflow steps');
    }
    
    // Import specific instructions from each prompt type
    const promptTypes = ['productCreation', 'coffeeProducts', 'technical'];
    
    for (const promptType of promptTypes) {
      if (data.prompts && data.prompts[promptType]) {
        // Extract the "Specific Instructions" section
        const prompt = data.prompts[promptType];
        const instructionsMatch = prompt.match(/# Specific Instructions\n\n([\s\S]+?)(?=\n#|$)/);
        
        if (instructionsMatch) {
          const instructions = instructionsMatch[1];
          const fragmentTitle = promptType === 'productCreation' ? 'General Product Creation' :
                               promptType === 'coffeeProducts' ? 'Coffee Product Creation' :
                               'Technical API Guidelines';
          
          const instructionsFragment = `# ${fragmentTitle} Instructions

${instructions}`;
          
          await memoryOps.addSystemPromptFragment(instructionsFragment, {
            category: promptType === 'technical' ? 'tools' : 'workflows',
            priority: 'high',
            agent_type: promptType === 'technical' ? 'swe' : 'all',
            tags: [promptType, 'instructions', 'specific-guidelines']
          });
          imported++;
        }
      }
    }
    console.log('✅ Imported specific instructions');
    
    // Create a comprehensive product creation checklist
    const checklistFragment = `# Product Creation Checklist

Before marking a product as complete, verify:

☐ Product has a proper title following format: {Brand} {Product Name} {Descriptors}
☐ Vendor field is filled with the correct brand name
☐ Product Type is set appropriately
☐ Body HTML contains detailed, engaging overview
☐ At least one variant exists with:
  - Price set
  - SKU assigned
  - Cost (COGS) entered
  - Inventory tracking enabled
☐ All relevant tags applied:
  - Product type tags
  - Feature tags
  - Collection tags (NC_*)
  - Special tags (preorder, shipping, etc.)
☐ Required metafields populated:
  - Buy Box content (if applicable)
  - FAQs (if applicable)
  - Tech specs (if applicable)
☐ Product status is DRAFT (for initial creation)
☐ For coffee products:
  - Vendor is "Escarpment Coffee Roasters"
  - Product Type is "Fresh Coffee"
  - Coffee-specific tags applied
  - Seasonality metafield set

This checklist ensures all products meet quality standards.`;
    
    await memoryOps.addSystemPromptFragment(checklistFragment, {
      category: 'patterns',
      priority: 'high',
      agent_type: 'all',
      tags: ['checklist', 'product-creation', 'quality-assurance']
    });
    imported++;
    console.log('✅ Created product creation checklist');
    
    console.log(`\n🎉 Successfully imported ${imported} prompt fragments!`);
    
  } catch (error) {
    console.error('❌ Error importing guidelines:', error);
  }
}

// Run if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  importProductGuidelines();
}

export default importProductGuidelines;