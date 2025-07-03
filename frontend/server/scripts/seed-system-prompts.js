#!/usr/bin/env node

import { memoryOperations } from '../memory/memory-operations-local.js';
import fs from 'fs/promises';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const systemPromptFragments = [
  // Tool Usage Patterns
  {
    fragment: "When searching for files or code patterns, use concurrent tool calls to maximize efficiency. For example, use multiple Glob and Grep calls in a single message when searching for related items.",
    metadata: {
      category: 'tools',
      priority: 'high',
      tags: ['search', 'performance', 'tools'],
      agent_type: 'all'
    }
  },
  {
    fragment: "For file operations, always verify the parent directory exists using LS before creating new files or directories. This prevents errors and ensures correct placement.",
    metadata: {
      category: 'tools',
      priority: 'high',
      tags: ['file-operations', 'safety'],
      agent_type: 'bash'
    }
  },
  {
    fragment: "When using bash commands with file paths containing spaces, always wrap the paths in double quotes. Example: cd \"/path with spaces/directory\"",
    metadata: {
      category: 'tools',
      priority: 'high',
      tags: ['bash', 'file-paths'],
      agent_type: 'bash'
    }
  },

  // Workflow Patterns
  {
    fragment: "Before implementing new features, search for existing similar implementations in the codebase. Look for patterns in neighboring files and follow established conventions.",
    metadata: {
      category: 'workflows',
      priority: 'high',
      tags: ['implementation', 'conventions'],
      agent_type: 'swe'
    }
  },
  {
    fragment: "When fixing bugs, first understand the root cause by reading relevant code and tests. Create a TodoWrite plan if the fix involves multiple steps or files.",
    metadata: {
      category: 'workflows',
      priority: 'medium',
      tags: ['debugging', 'planning'],
      agent_type: 'swe'
    }
  },
  {
    fragment: "After making code changes, always run lint and typecheck commands if available (npm run lint, npm run typecheck, etc). Ask for these commands if not found in package.json.",
    metadata: {
      category: 'workflows',
      priority: 'high',
      tags: ['quality', 'validation'],
      agent_type: 'swe'
    }
  },

  // Domain Knowledge - Shopify
  {
    fragment: "For Shopify development, use MCP tools for API introspection: introspect_admin_schema for GraphQL schema, search_dev_docs for documentation, and get_started for API overviews.",
    metadata: {
      category: 'domain',
      priority: 'high',
      tags: ['shopify', 'mcp', 'api'],
      agent_type: 'swe'
    }
  },
  {
    fragment: "When working with Shopify GraphQL mutations, always check for userErrors in the response. Handle these errors gracefully and provide meaningful feedback.",
    metadata: {
      category: 'domain',
      priority: 'medium',
      tags: ['shopify', 'graphql', 'error-handling'],
      agent_type: 'swe'
    }
  },

  // Error Handling
  {
    fragment: "If a git commit fails due to pre-commit hooks, retry once to include the hook's changes. If it fails again, investigate the specific hook requirements.",
    metadata: {
      category: 'errors',
      priority: 'medium',
      tags: ['git', 'pre-commit'],
      agent_type: 'bash'
    }
  },
  {
    fragment: "When encountering module import errors, check if the file extension is included for ES modules. Use .js extension for local imports in Node.js ES module projects.",
    metadata: {
      category: 'errors',
      priority: 'high',
      tags: ['javascript', 'modules', 'imports'],
      agent_type: 'swe'
    }
  },

  // Best Practices
  {
    fragment: "Prefer editing existing files over creating new ones. Only create new files when explicitly required by the task or when implementing genuinely new functionality.",
    metadata: {
      category: 'patterns',
      priority: 'high',
      tags: ['file-management', 'best-practices'],
      agent_type: 'all'
    }
  },
  {
    fragment: "Never expose or log sensitive information like API keys, tokens, or passwords. Always use environment variables for configuration and validate that secrets aren't committed.",
    metadata: {
      category: 'constraints',
      priority: 'high',
      tags: ['security', 'secrets'],
      agent_type: 'all'
    }
  },
  {
    fragment: "When implementing React components, check existing components for patterns. Follow the project's state management approach (Redux, Context, Zustand, etc) and styling conventions.",
    metadata: {
      category: 'patterns',
      priority: 'medium',
      tags: ['react', 'frontend', 'conventions'],
      agent_type: 'swe'
    }
  },

  // Architecture Knowledge
  {
    fragment: "EspressoBot uses a Shell Agency architecture where agents have direct bash access. Agents can spawn sub-agents dynamically for focused tasks.",
    metadata: {
      category: 'domain',
      priority: 'medium',
      tags: ['architecture', 'espressobot'],
      agent_type: 'all'
    }
  },
  {
    fragment: "The memory system uses SQLite with OpenAI embeddings for semantic search. Deduplication threshold is 85% similarity. Memory operations are available via Python CLI for bash agents.",
    metadata: {
      category: 'domain',
      priority: 'medium',
      tags: ['memory', 'architecture', 'espressobot'],
      agent_type: 'all'
    }
  },

  // Task Management
  {
    fragment: "Use TodoWrite proactively for complex tasks (3+ steps). Mark tasks as in_progress before starting and completed immediately after finishing. Only have one in_progress task at a time.",
    metadata: {
      category: 'tools',
      priority: 'high',
      tags: ['todo', 'planning', 'task-management'],
      agent_type: 'all'
    }
  },
  {
    fragment: "When blocked on a task, keep it as in_progress and create a new todo describing what needs to be resolved. Never mark incomplete tasks as completed.",
    metadata: {
      category: 'workflows',
      priority: 'medium',
      tags: ['todo', 'blocked', 'task-management'],
      agent_type: 'all'
    }
  }
];

async function seedSystemPrompts() {
  console.log('Starting system prompt seeding...\n');
  
  let successCount = 0;
  let errorCount = 0;

  for (const item of systemPromptFragments) {
    try {
      await memoryOperations.addSystemPromptFragment(
        item.fragment,
        item.metadata
      );
      console.log(`✓ Added: ${item.fragment.slice(0, 60)}...`);
      successCount++;
    } catch (error) {
      console.error(`✗ Failed to add fragment: ${error.message}`);
      errorCount++;
    }
  }

  console.log(`\nSeeding complete!`);
  console.log(`Successfully added: ${successCount} fragments`);
  console.log(`Errors: ${errorCount}`);

  // Verify by searching
  console.log('\nVerifying system prompts...');
  const searchTests = ['tools', 'shopify', 'error', 'workflow'];
  
  for (const query of searchTests) {
    const results = await memoryOperations.searchSystemPromptFragments(query, 3);
    console.log(`\nSearch "${query}" found ${results.length} results:`);
    results.forEach(r => {
      console.log(`  - [${r.score.toFixed(2)}] ${r.memory.slice(0, 60)}...`);
    });
  }

  process.exit(0);
}

// Run the seeding
seedSystemPrompts().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});