#!/usr/bin/env node

/**
 * Test script to verify user profile injection in system prompts
 */

import { buildUnifiedOrchestratorPrompt } from '../server/prompts/unified-orchestrator-prompt.js';
import { buildPromptFromRichContext } from '../server/tools/bash-tool.js';

console.log('Testing User Profile Injection in System Prompts\n');
console.log('='.repeat(60));

// Test 1: Test orchestrator system prompt with no user
console.log('\n1. Orchestrator prompt with no user profile:');
const promptNoUser = buildUnifiedOrchestratorPrompt('test message', {});
console.log(promptNoUser.substring(0, 500) + '...');

// Test 2: Test orchestrator prompt with regular user
console.log('\n\n2. Orchestrator prompt with regular user:');
const regularUser = {
  id: 123,
  name: 'John Doe',
  email: 'john@example.com',
  bio: 'Regular user of the system',
  is_admin: false,
  created_at: new Date('2024-01-15')
};
const promptRegularUser = buildUnifiedOrchestratorPrompt('test message', {}, regularUser);
const userSection = promptRegularUser.match(/## User Profile[\s\S]*?(?=##|$)/);
console.log('User section:', userSection ? userSection[0] : 'NOT FOUND');

// Test 3: Test orchestrator prompt with Pranav (VIP)
console.log('\n\n3. Orchestrator prompt with Pranav (VIP):');
const pranavUser = {
  id: 1,
  name: 'Pranav',
  email: 'pranav@idrinkcoffee.com',
  bio: 'Developer and Digital Operations Manager',
  is_admin: true,
  created_at: new Date('2023-06-01')
};
const promptPranav = buildUnifiedOrchestratorPrompt('test message', {}, pranavUser);
const pranavSection = promptPranav.match(/## User Profile[\s\S]*?(?=##|$)/);
console.log('Pranav section:', pranavSection ? pranavSection[0] : 'NOT FOUND');

// Test 4: Test unified prompt with complex task
console.log('\n\n4. Unified orchestrator prompt with complex task:');
const complexPrompt = buildUnifiedOrchestratorPrompt(
  'Bulk update product prices for all products',
  { businessLogic: { patterns: [{ type: 'bulk_operation' }] } },
  pranavUser
);
console.log('Includes user profile:', complexPrompt.includes('Pranav') ? 'YES' : 'NO');
console.log('Includes VIP instructions:', complexPrompt.includes('VIP') ? 'YES' : 'NO');
console.log('Includes bulk handling:', complexPrompt.includes('Bulk Operations') ? 'YES' : 'NO');

// Test 5: Test bash agent prompt with user profile
console.log('\n\n5. Bash agent prompt with user profile:');
const bashContext = {
  task: 'Update git repository',
  userProfile: pranavUser,
  relevantMemories: [],
  businessLogic: { patterns: [] }
};
const bashPrompt = buildPromptFromRichContext(bashContext);
const bashUserSection = bashPrompt.match(/## Current User Profile:[\s\S]*?(?=##|$)/);
console.log('Bash user section:', bashUserSection ? bashUserSection[0] : 'NOT FOUND');

// Test 6: Test admin user (not Pranav)
console.log('\n\n6. Admin user (not Pranav):');
const adminUser = {
  id: 456,
  name: 'Admin User',
  email: 'admin@idrinkcoffee.com',
  bio: 'System administrator',
  is_admin: true,
  created_at: new Date('2023-08-01')
};
const promptAdmin = buildUnifiedOrchestratorPrompt('test message', {}, adminUser);
const adminSection = promptAdmin.match(/## User Profile[\s\S]*?(?=##|$)/);
console.log('Admin section:', adminSection ? adminSection[0] : 'NOT FOUND');

console.log('\n' + '='.repeat(60));
console.log('User profile injection test complete!');