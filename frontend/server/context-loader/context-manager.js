/**
 * Smart Context Loading Manager for EspressoBot Shell Agency
 * 
 * This module analyzes user requests and agent tasks to intelligently
 * load only relevant context, preventing prompt bloat while ensuring
 * agents have all necessary information.
 */

import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Context categories and their trigger patterns
const CONTEXT_PATTERNS = {
  PRODUCT_CREATION: {
    patterns: [
      /create.*product/i,
      /new.*product/i,
      /add.*product/i,
      /create.*combo/i,
      /create.*open.?box/i,
      /duplicate.*product/i
    ],
    contexts: [
      'product-creation-rules',
      'naming-conventions',
      'metafields-guide',
      'features-workflow'
    ]
  },
  
  PRICING_UPDATES: {
    patterns: [
      /update.*pric/i,
      /change.*pric/i,
      /bulk.*pric/i,
      /discount/i,
      /sale.*price/i,
      /cost.*update/i
    ],
    contexts: [
      'pricing-rules',
      'currency-handling',
      'bulk-operations'
    ]
  },
  
  PREORDER_MANAGEMENT: {
    patterns: [
      /preorder/i,
      /pre-order/i,
      /oversell/i,
      /shipping.*nis/i,
      /inventory.*policy/i
    ],
    contexts: [
      'preorder-rules',
      'inventory-management',
      'tag-management'
    ]
  },
  
  TAG_OPERATIONS: {
    patterns: [
      /add.*tag/i,
      /remove.*tag/i,
      /manage.*tag/i,
      /tag.*product/i
    ],
    contexts: [
      'tag-conventions',
      'tag-operations'
    ]
  },
  
  FEATURES_MANAGEMENT: {
    patterns: [
      /add.*feature/i,
      /product.*feature/i,
      /manage.*feature/i,
      /metaobject/i
    ],
    contexts: [
      'features-workflow',
      'metaobjects-guide'
    ]
  },
  
  VENDOR_SPECIFIC: {
    patterns: [
      /cd2025/i,
      /mahlkonig/i,
      /anfim/i,
      /heycafe/i,
      /vendor.*discount/i
    ],
    contexts: [
      'vendor-rules',
      'cd2025-scripts'
    ]
  },
  
  SEARCH_OPERATIONS: {
    patterns: [
      /search.*product/i,
      /find.*product/i,
      /get.*product/i,
      /list.*product/i
    ],
    contexts: [
      'search-syntax',
      'identifier-formats'
    ]
  },
  
  BULK_OPERATIONS: {
    patterns: [
      /bulk/i,
      /multiple.*product/i,
      /csv/i,
      /batch/i
    ],
    contexts: [
      'bulk-operations',
      'csv-formats'
    ]
  }
};

// Context file mappings
const CONTEXT_FILES = {
  // Business Rules
  'preorder-rules': {
    file: '../prompts/idc-business-rules.md',
    section: '## Preorder Management'
  },
  'pricing-rules': {
    file: '../prompts/idc-business-rules.md',
    section: '## Pricing Rules'
  },
  'tag-conventions': {
    file: '../prompts/idc-business-rules.md',
    section: '## Tag Conventions'
  },
  'naming-conventions': {
    file: '../prompts/idc-business-rules.md',
    section: '## Product Conventions'
  },
  'vendor-rules': {
    file: '../prompts/idc-business-rules.md',
    section: '## Vendor-Specific Notes'
  },
  
  // Tool Documentation
  'product-creation-rules': {
    file: '../tool-docs/TOOL_USAGE_GUIDE.md',
    section: '### 📦 Product Creation Tools'
  },
  'search-syntax': {
    file: '../tool-docs/TOOL_USAGE_GUIDE.md',
    section: '### 🔍 Search & Information Tools'
  },
  'bulk-operations': {
    file: '../tool-docs/TOOL_USAGE_GUIDE.md',
    section: '## Common Workflows'
  },
  'features-workflow': {
    file: '../tool-docs/TOOL_USAGE_GUIDE.md',
    section: '#### manage_features_metaobjects.py'
  },
  'tag-operations': {
    file: '../tool-docs/TOOL_USAGE_GUIDE.md',
    section: '#### manage_tags.py'
  },
  
  // Workflow Examples (to be created)
  'csv-formats': {
    file: '../tool-docs/WORKFLOW_EXAMPLES.md',
    section: '## CSV Formats'
  },
  'identifier-formats': {
    file: '../tool-docs/WORKFLOW_EXAMPLES.md',
    section: '## Identifier Formats'
  }
};

/**
 * Analyzes a message/task to determine which contexts are relevant
 */
export function analyzeContextNeeds(message) {
  const neededContexts = new Set();
  
  // Always include base context
  neededContexts.add('base-rules');
  
  // Check each pattern category
  for (const [category, config] of Object.entries(CONTEXT_PATTERNS)) {
    const matches = config.patterns.some(pattern => pattern.test(message));
    if (matches) {
      config.contexts.forEach(context => neededContexts.add(context));
    }
  }
  
  return Array.from(neededContexts);
}

/**
 * Extracts a specific section from a markdown file
 */
async function extractSection(filePath, sectionHeader) {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    const lines = content.split('\n');
    
    let inSection = false;
    let sectionContent = [];
    let sectionLevel = 0;
    
    for (const line of lines) {
      // Check if we've found our section
      if (line.trim() === sectionHeader) {
        inSection = true;
        sectionLevel = line.match(/^#+/)?.[0].length || 0;
        sectionContent.push(line);
        continue;
      }
      
      // If in section, check if we've hit the next section at same or higher level
      if (inSection) {
        const currentLevel = line.match(/^#+/)?.[0].length || 0;
        if (currentLevel > 0 && currentLevel <= sectionLevel && line !== sectionHeader) {
          break;
        }
        sectionContent.push(line);
      }
    }
    
    return sectionContent.join('\n').trim();
  } catch (error) {
    console.error(`Error extracting section from ${filePath}:`, error);
    return '';
  }
}

/**
 * Loads the relevant context based on the analyzed needs
 */
export async function loadContext(contextNeeds) {
  const loadedContext = {
    rules: [],
    tools: [],
    workflows: []
  };
  
  for (const contextKey of contextNeeds) {
    const contextConfig = CONTEXT_FILES[contextKey];
    if (!contextConfig) continue;
    
    const filePath = path.join(__dirname, contextConfig.file);
    
    try {
      let content;
      if (contextConfig.section) {
        content = await extractSection(filePath, contextConfig.section);
      } else {
        content = await fs.readFile(filePath, 'utf-8');
      }
      
      // Categorize content
      if (contextConfig.file.includes('business-rules')) {
        loadedContext.rules.push(content);
      } else if (contextConfig.file.includes('TOOL_USAGE_GUIDE')) {
        loadedContext.tools.push(content);
      } else if (contextConfig.file.includes('WORKFLOW')) {
        loadedContext.workflows.push(content);
      }
    } catch (error) {
      console.error(`Error loading context ${contextKey}:`, error);
    }
  }
  
  return loadedContext;
}

/**
 * Formats the loaded context into a prompt-friendly format
 */
export function formatContext(loadedContext, taskDescription = '') {
  let formattedContext = '';
  
  if (taskDescription) {
    formattedContext += `## Task Context\nYour specific task: ${taskDescription}\n\n`;
  }
  
  if (loadedContext.rules.length > 0) {
    formattedContext += `## Relevant Business Rules\n${loadedContext.rules.join('\n\n')}\n\n`;
  }
  
  if (loadedContext.tools.length > 0) {
    formattedContext += `## Relevant Tools\n${loadedContext.tools.join('\n\n')}\n\n`;
  }
  
  if (loadedContext.workflows.length > 0) {
    formattedContext += `## Relevant Workflows\n${loadedContext.workflows.join('\n\n')}\n\n`;
  }
  
  return formattedContext;
}

/**
 * Main function to get smart context for a given message/task
 */
export async function getSmartContext(message, options = {}) {
  const { includeMemory = true, taskDescription = '', useContextStore = true, userId = null, conversationId = null } = options;
  
  let contextNeeds;
  
  // Use context store abstraction if enabled (allows easy migration to semantic search)
  if (useContextStore) {
    try {
      const { getContextStore } = await import('./context-store.js');
      const store = getContextStore({ enableMetrics: true });
      contextNeeds = await store.getContexts(message, options);
      console.log(`[Context Manager] Context store identified needs:`, contextNeeds);
    } catch (error) {
      // Fallback to direct pattern matching
      console.log('[Context Manager] Context store error, using direct patterns:', error.message);
      contextNeeds = analyzeContextNeeds(message);
    }
  } else {
    // Direct pattern matching
    contextNeeds = analyzeContextNeeds(message);
    console.log(`[Context Manager] Identified context needs:`, contextNeeds);
  }
  
  // Load the relevant contexts
  const loadedContext = await loadContext(contextNeeds);
  
  // Format for prompt injection
  let formattedContext = formatContext(loadedContext, taskDescription);
  
  // If conversationId is provided, fetch and inject topic information
  if (conversationId) {
    try {
      const pkg = await import('@prisma/client');
      const { PrismaClient } = pkg;
      const prisma = new PrismaClient();
      
      const conversation = await prisma.conversations.findUnique({
        where: { id: parseInt(conversationId) }
      });
      
      if (conversation && (conversation.topic_title || conversation.topic_details)) {
        let topicContext = '\n## Conversation Topic\n';
        if (conversation.topic_title) {
          topicContext += `**Topic:** ${conversation.topic_title}\n`;
        }
        if (conversation.topic_details) {
          topicContext += `**Details:** ${conversation.topic_details}\n`;
        }
        formattedContext = topicContext + '\n' + formattedContext;
      }
    } catch (error) {
      console.log('[Context Manager] Could not fetch conversation topic:', error.message);
    }
  }
  
  // If memory integration is enabled, fetch relevant memories
  if (includeMemory) {
    try {
      const { memoryOperations } = await import('../memory/memory-operations-local.js');
      
      // Extract just the relevant part for memory search
      // If message is very long (likely full conversation), extract the last user message
      let searchQuery = message;
      if (message.length > 1000) {
        // Try to extract just the last user message
        const lastUserMatch = message.match(/(?:^|\n)User:\s*(.+?)(?:\n|$)/g);
        if (lastUserMatch && lastUserMatch.length > 0) {
          const lastUserMessage = lastUserMatch[lastUserMatch.length - 1];
          searchQuery = lastUserMessage.replace(/^User:\s*/, '').trim();
          console.log(`[Context Manager] Extracted search query from conversation: "${searchQuery.substring(0, 100)}..."`);
        } else {
          // Fallback: use last 1000 chars
          searchQuery = message.substring(message.length - 1000);
        }
      }
      
      // Use the provided userId or fall back to 'global' for backward compatibility
      const memoryUserId = userId || 'global';
      const memories = await memoryOperations.search(searchQuery, memoryUserId);
      
      if (memories && memories.length > 0) {
        const memoryContext = memories
          .map(m => `- ${m.memory}`)
          .join('\n');
        
        return formattedContext + `\n## Relevant Memories\n${memoryContext}\n`;
      }
    } catch (error) {
      console.log('[Context Manager] Memory fetch error:', error.message);
    }
  }
  
  return formattedContext;
}

/**
 * Utility to test context loading
 */
export async function testContextLoading(testMessage) {
  console.log(`\nTesting context loading for: "${testMessage}"`);
  console.log('=' * 50);
  
  const context = await getSmartContext(testMessage);
  console.log('Loaded context preview:');
  console.log(context.substring(0, 500) + '...\n');
  
  return context;
}

// Export patterns for external use
export { CONTEXT_PATTERNS };