
// Test to verify that spawning a bash agent no longer throws
// ReferenceError: taskContext is not defined.

import { createBashAgent } from '../server/tools/bash-tool.js';

process.env.OPENAI_API_KEY = process.env.OPENAI_API_KEY || 'test-key';

async function main () {
  const richContext = {
    specificEntities: [],
    businessLogic: { patterns: [] },
    relevantMemories: [],
    conversationHistory: '',
    currentTasks: [{ title: 'Dummy task', status: 'pending' }],
    relevantRules: [],
    relevantTools: []
  };

  try {
    await createBashAgent('SpawnTestAgent', 'echo "hello"', 'conv-test', 'high', richContext);
    console.log('✅ spawn_bash_agent fix validated — no ReferenceError thrown');
    process.exit(0);
  } catch (error) {
    console.error('❌ spawn_bash_agent fix FAILED:', error);
    process.exit(1);
  }
}

main();
