#!/usr/bin/env node
/**
 * Example: Using Generated Product Prompts with AI Agents
 * 
 * This shows how to integrate the converted product guidelines
 * into your AI agent system prompts.
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Load a generated prompt
 */
async function loadPrompt(promptType) {
  const promptPath = path.join(__dirname, '../prompts', `${promptType}-system-prompt.txt`);
  return await fs.readFile(promptPath, 'utf-8');
}

/**
 * Load structured data
 */
async function loadStructuredData() {
  const dataPath = path.join(__dirname, '../prompts', 'product-guidelines-structured.json');
  const content = await fs.readFile(dataPath, 'utf-8');
  return JSON.parse(content);
}

/**
 * Example: Enhance SWE Agent prompt with product guidelines
 */
async function enhanceSWEAgentPrompt(basePrompt, context) {
  // Load appropriate product prompt based on context
  let productPrompt = '';
  
  if (context.includes('coffee') || context.includes('escarpment')) {
    productPrompt = await loadPrompt('coffeeProducts');
  } else if (context.includes('technical') || context.includes('graphql')) {
    productPrompt = await loadPrompt('technical');
  } else {
    productPrompt = await loadPrompt('productCreation');
  }
  
  // Combine prompts
  return `${basePrompt}

# Product Creation Guidelines

${productPrompt}

Remember to follow all product creation guidelines when helping with Shopify product management tasks.`;
}

/**
 * Example: Create context-aware prompt
 */
async function createContextAwarePrompt(taskDescription) {
  const structuredData = await loadStructuredData();
  
  let prompt = `You are an AI assistant helping with: ${taskDescription}\n\n`;
  
  // Add relevant sections based on task
  if (taskDescription.toLowerCase().includes('metafield')) {
    prompt += '# Relevant Metafields\n\n';
    structuredData.metafields.slice(0, 5).forEach(field => {
      prompt += `- ${field.name}: \`${field.namespace}.${field.key}\`\n`;
    });
    prompt += '\n';
  }
  
  if (taskDescription.toLowerCase().includes('tag')) {
    prompt += '# Relevant Tags\n\n';
    structuredData.tags.slice(0, 3).forEach(category => {
      prompt += `## ${category.category}\n`;
      category.tags.slice(0, 5).forEach(tag => {
        prompt += `- \`${tag}\`\n`;
      });
      prompt += '\n';
    });
  }
  
  // Always add principles
  prompt += '# Key Principles\n\n';
  structuredData.principles.forEach(principle => {
    prompt += `- ${principle}\n`;
  });
  
  return prompt;
}

/**
 * Example: Dynamic prompt selection
 */
function selectPromptForTask(task) {
  const taskLower = task.toLowerCase();
  
  if (taskLower.includes('coffee') || taskLower.includes('roast')) {
    return 'coffeeProducts';
  } else if (taskLower.includes('api') || taskLower.includes('graphql') || taskLower.includes('mutation')) {
    return 'technical';
  } else {
    return 'productCreation';
  }
}

/**
 * Example: Integration with RAG system
 */
async function integrateWithRAG() {
  // This shows how you might integrate with your existing RAG system
  const structuredData = await loadStructuredData();
  
  // Create searchable fragments
  const fragments = [];
  
  // Add metafields as fragments
  structuredData.metafields.forEach(field => {
    fragments.push({
      content: `Metafield ${field.name}: namespace=${field.namespace}, key=${field.key}`,
      metadata: { type: 'metafield', category: 'product_data' }
    });
  });
  
  // Add tag categories
  structuredData.tags.forEach(category => {
    fragments.push({
      content: `Tags for ${category.category}: ${category.tags.join(', ')}`,
      metadata: { type: 'tags', category: category.category }
    });
  });
  
  // Add principles
  fragments.push({
    content: `Key principles: ${structuredData.principles.join('; ')}`,
    metadata: { type: 'principles', category: 'guidelines' }
    });
  
  return fragments;
}

// Example usage
async function main() {
  console.log('📚 Product Prompt Integration Examples\n');
  
  // Example 1: Load a specific prompt
  console.log('1️⃣ Loading coffee products prompt...');
  const coffeePrompt = await loadPrompt('coffeeProducts');
  console.log(`   Loaded ${coffeePrompt.length} characters\n`);
  
  // Example 2: Create context-aware prompt
  console.log('2️⃣ Creating context-aware prompt for "Add metafields to a coffee product"...');
  const contextPrompt = await createContextAwarePrompt('Add metafields to a coffee product');
  console.log(contextPrompt.substring(0, 500) + '...\n');
  
  // Example 3: Select appropriate prompt
  console.log('3️⃣ Selecting prompts for different tasks:');
  const tasks = [
    'Create a new espresso machine listing',
    'Add Colombia coffee to the catalog',
    'Write a GraphQL mutation for product creation',
    'Update product tags'
  ];
  
  tasks.forEach(task => {
    const promptType = selectPromptForTask(task);
    console.log(`   Task: "${task}" → ${promptType}`);
  });
  
  // Example 4: Show how to integrate with SWE agent
  console.log('\n4️⃣ Example SWE Agent integration:');
  const sampleBasePrompt = 'You are a Software Engineering Agent...';
  const enhancedPrompt = await enhanceSWEAgentPrompt(sampleBasePrompt, 'create coffee product');
  console.log(`   Enhanced prompt length: ${enhancedPrompt.length} characters`);
  
  // Example 5: RAG integration
  console.log('\n5️⃣ RAG system integration:');
  const fragments = await integrateWithRAG();
  console.log(`   Generated ${fragments.length} searchable fragments`);
  console.log(`   Sample fragment: ${JSON.stringify(fragments[0], null, 2)}`);
}

// Run examples if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}

// Export functions for use in other modules
export {
  loadPrompt,
  loadStructuredData,
  enhanceSWEAgentPrompt,
  createContextAwarePrompt,
  selectPromptForTask,
  integrateWithRAG
};