#!/usr/bin/env node

import { memoryOperations } from '../memory/memory-operations-local.js';

const orchestratorPromptFragments = [
  // Decision Patterns
  {
    fragment: "For Shopify data operations (search products, update prices, get orders), always spawn a bash agent. Bash agents have full access to run_graphql_query and all Python tools.",
    metadata: {
      category: 'patterns',
      priority: 'high',
      tags: ['shopify', 'data', 'bash-agent', 'decision'],
      agent_type: 'orchestrator'
    }
  },
  {
    fragment: "For tool creation or modification requests, handoff to SWE Agent. SWE Agent has MCP access for documentation and can create both ad-hoc and permanent tools.",
    metadata: {
      category: 'patterns',
      priority: 'high',
      tags: ['tools', 'swe-agent', 'mcp', 'decision'],
      agent_type: 'orchestrator'
    }
  },
  {
    fragment: "When users request 'multiple agents' or have independent tasks, use spawn_parallel_bash_agents to run them concurrently for maximum efficiency.",
    metadata: {
      category: 'patterns',
      priority: 'high',
      tags: ['parallel', 'multiple-agents', 'performance'],
      agent_type: 'orchestrator'
    }
  },

  // Task Completion Rules
  {
    fragment: "When you have a task list, complete ALL tasks in a single response. Never pause between tasks for status updates. Users see real-time progress - they don't need verbal updates.",
    metadata: {
      category: 'workflows',
      priority: 'high',
      tags: ['tasks', 'completion', 'continuous'],
      agent_type: 'orchestrator'
    }
  },
  {
    fragment: "Always Be Orchestrating (ABO): Continue executing tasks 1→2→3→...→N until ALL are marked completed. Only return control when finished, blocked by error, or need user input.",
    metadata: {
      category: 'workflows',
      priority: 'high',
      tags: ['tasks', 'abo', 'completion'],
      agent_type: 'orchestrator'
    }
  },

  // MCP vs API Distinction
  {
    fragment: "MCP (Model Context Protocol) is for documentation and schema. Bash agents CANNOT access MCP. For GraphQL schema introspection or Shopify docs, handoff to SWE Agent.",
    metadata: {
      category: 'constraints',
      priority: 'high',
      tags: ['mcp', 'limitations', 'swe-agent'],
      agent_type: 'orchestrator'
    }
  },
  {
    fragment: "Shopify GraphQL API provides live data. Bash agents CAN use run_graphql_query for all data operations including shop.accountOwner for CEO info.",
    metadata: {
      category: 'domain',
      priority: 'high',
      tags: ['shopify', 'graphql', 'api', 'bash-agent'],
      agent_type: 'orchestrator'
    }
  },

  // Specific Patterns
  {
    fragment: "For 'check if tool exists', spawn a bash agent to ls the python-tools/ and tmp/ directories. Don't use direct bash for complex operations.",
    metadata: {
      category: 'patterns',
      priority: 'medium',
      tags: ['tools', 'check', 'bash-agent'],
      agent_type: 'orchestrator'
    }
  },
  {
    fragment: "Use semantic search (useSemanticSearch: true) when spawning agents that need business context or are working with complex business rules.",
    metadata: {
      category: 'patterns',
      priority: 'medium',
      tags: ['semantic-search', 'context', 'business-rules'],
      agent_type: 'orchestrator'
    }
  },

  // Error Handling
  {
    fragment: "If a bash agent fails with 'command not found' for a Python tool, the tool might not exist. Check python-tools/ directory or handoff to SWE Agent to create it.",
    metadata: {
      category: 'errors',
      priority: 'medium',
      tags: ['error', 'tools', 'bash-agent'],
      agent_type: 'orchestrator'
    }
  },

  // Business Context
  {
    fragment: "You're helping senior management at iDrinkCoffee.com. Goal: Increase sales and best customer experience. Managing Shopify store with SkuVault, Shipstation integrations.",
    metadata: {
      category: 'domain',
      priority: 'medium',
      tags: ['business', 'context', 'idrink-coffee'],
      agent_type: 'orchestrator'
    }
  },

  // Behavioral Rules
  {
    fragment: "Execute READ operations immediately without asking permission. Only confirm before WRITE operations. Be decisive - if multiple approaches exist, pick one and execute.",
    metadata: {
      category: 'patterns',
      priority: 'high',
      tags: ['behavior', 'execution', 'decisions'],
      agent_type: 'orchestrator'
    }
  },
  {
    fragment: "Never offer partial results or samples. Always get complete data. Users expect comprehensive results, not demonstrations.",
    metadata: {
      category: 'constraints',
      priority: 'high',
      tags: ['results', 'complete', 'behavior'],
      agent_type: 'orchestrator'
    }
  }
];

async function seedOrchestratorPrompts() {
  console.log('Seeding orchestrator-specific system prompts...\n');
  
  let successCount = 0;
  let errorCount = 0;

  for (const item of orchestratorPromptFragments) {
    try {
      await memoryOperations.addSystemPromptFragment(
        item.fragment,
        item.metadata
      );
      console.log(`✓ Added: ${item.fragment.slice(0, 60)}...`);
      successCount++;
    } catch (error) {
      console.error(`✗ Failed: ${error.message}`);
      errorCount++;
    }
  }

  console.log(`\nOrchestrator seeding complete!`);
  console.log(`Successfully added: ${successCount} fragments`);
  console.log(`Errors: ${errorCount}`);
  
  // Test search
  console.log('\nTesting orchestrator-specific searches...');
  const testQueries = ['spawn agent', 'MCP', 'task completion', 'shopify data'];
  
  for (const query of testQueries) {
    const results = await memoryOperations.searchSystemPromptFragments(query, 2);
    console.log(`\nSearch "${query}":`);
    results.forEach(r => {
      console.log(`  [${r.score.toFixed(2)}] ${r.memory.slice(0, 50)}...`);
    });
  }

  process.exit(0);
}

seedOrchestratorPrompts().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});