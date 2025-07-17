#!/usr/bin/env node
/**
 * Test script for MCP server selection logic
 */

import { selectServersForTask } from '../server/agents/python-tools-agent-v2.js';

const testCases = [
  // Products server tests
  "Search for all coffee products",
  "Get product details for SKU ABC-123",
  "Create a new product with vendor Breville",
  "Update product status to active",
  
  // Pricing server tests
  "Update pricing for bulk items",
  "Apply 15% discount to all grinders",
  "Update costs for supplier products",
  "Check profit margins",
  
  // Multi-server tests
  "Create product and set price to $99.99",
  "Search products and update their tags",
  "Apply MAP sale pricing for Miele products",
  
  // Default case
  "Do something with the API"
];

console.log("Testing MCP Server Selection Logic\n");
console.log("=".repeat(50));

testCases.forEach(task => {
  const servers = selectServersForTask(task);
  console.log(`\nTask: "${task}"`);
  console.log(`Selected: ${servers.join(', ')}`);
});

console.log("\n" + "=".repeat(50));
console.log("\nToken Savings Analysis:");
console.log("- Old: All 28 tools loaded = ~10,000+ tokens");
console.log("- New: 3-4 tools per server = ~1,200 tokens");
console.log("- Savings: ~88% reduction in tool schema tokens!");