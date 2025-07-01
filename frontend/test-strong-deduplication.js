#!/usr/bin/env node
/**
 * Test strong deduplication system
 */

import { simpleLocalMemory } from './server/memory/simple-local-memory.js';

const testUserId = 'dedup_test_user';

const testMemories = [
  // Exact duplicates
  "The user's name is Pranav.",
  "The user's name is Pranav.",
  
  // Case variations
  "The user's name is pranav.",
  "THE USER'S NAME IS PRANAV.",
  
  // Punctuation variations
  "The users name is Pranav",
  "The user's name is Pranav!",
  
  // Similar semantic content
  "Pranav is the user's name.",
  "The name of the user is Pranav.",
  "User name: Pranav",
  
  // Additional info with same core fact
  "The user's name is Pranav and he manages iDrinkCoffee.com.",
  "Pranav manages the iDrinkCoffee.com store.",
  
  // Different facts
  "The user prefers Ethiopian Yirgacheffe coffee.",
  "iDrinkCoffee.com offers 15% bulk discounts.",
  "The CEO of iDrinkCoffee.com is Slawek Janicki.",
  
  // Similar but different facts
  "The user likes Ethiopian coffee.",
  "The user enjoys Yirgacheffe beans.",
  
  // Key phrase overlap
  "Pranav was born on June 25th 1985.",
  "On June 25th 1985, the user celebrated their birthday.",
];

async function testDeduplication() {
  console.log('=== Testing Strong Deduplication System ===\n');
  
  // Clean up any existing test data
  await simpleLocalMemory.deleteAll(testUserId);
  
  let successCount = 0;
  let duplicateCount = 0;
  const results = [];
  
  // Try to add all test memories
  for (const memory of testMemories) {
    const result = await simpleLocalMemory.add(memory, testUserId, {
      source: 'dedup_test'
    });
    
    results.push({
      memory: memory,
      success: result.success,
      reason: result.reason || 'stored'
    });
    
    if (result.success) {
      successCount++;
      console.log(`✅ Stored: "${memory}"`);
    } else {
      duplicateCount++;
      console.log(`❌ Duplicate (${result.reason}): "${memory}"`);
      if (result.existingContent) {
        console.log(`   Existing: "${result.existingContent}"`);
      }
    }
  }
  
  console.log(`\n=== Summary ===`);
  console.log(`Total memories tested: ${testMemories.length}`);
  console.log(`Successfully stored: ${successCount}`);
  console.log(`Rejected as duplicates: ${duplicateCount}`);
  
  // Show what was actually stored
  console.log(`\n=== Stored Memories ===`);
  const storedMemories = await simpleLocalMemory.getAll(testUserId);
  storedMemories.forEach((mem, i) => {
    console.log(`${i + 1}. ${mem.memory}`);
  });
  
  // Test consolidation
  console.log(`\n=== Testing Memory Consolidation ===`);
  const dryRunResult = await simpleLocalMemory.mergeRelatedMemories(testUserId, { dryRun: true });
  
  if (dryRunResult.groups && dryRunResult.groups.length > 0) {
    console.log(`Found ${dryRunResult.groups.length} groups that could be merged:`);
    dryRunResult.groups.forEach((group, i) => {
      console.log(`\nGroup ${i + 1} (${group.count} memories):`);
      group.memories.forEach(m => console.log(`  - ${m}`));
    });
    
    // Actually perform the merge
    console.log(`\n=== Performing Consolidation ===`);
    const mergeResult = await simpleLocalMemory.mergeRelatedMemories(testUserId);
    
    if (mergeResult.success) {
      console.log(`Merged ${mergeResult.merged} groups`);
      mergeResult.results.forEach((result, i) => {
        console.log(`\nMerge ${i + 1}:`);
        console.log('Original memories:');
        result.original.forEach(m => console.log(`  - ${m}`));
        console.log(`Consolidated to: "${result.consolidated}"`);
      });
      
      // Show final memories
      console.log(`\n=== Final Memories After Consolidation ===`);
      const finalMemories = await simpleLocalMemory.getAll(testUserId);
      finalMemories.forEach((mem, i) => {
        console.log(`${i + 1}. ${mem.memory}`);
      });
    }
  } else {
    console.log('No related memories found to merge.');
  }
  
  // Clean up
  await simpleLocalMemory.deleteAll(testUserId);
  console.log('\n✅ Test data cleaned up');
}

// Run the test
testDeduplication().then(() => {
  console.log('\n=== Test Complete ===');
  process.exit(0);
}).catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});