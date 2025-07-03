#!/usr/bin/env node

/**
 * Script to validate tool documentation integrity
 */

import { memoryOperations } from '../server/memory/memory-operations-local.js';
import fs from 'fs/promises';
import path from 'path';

async function validateToolDocumentation() {
  console.log('🔍 Validating tool documentation system...\n');
  
  const errors = [];
  const warnings = [];
  let totalChecks = 0;
  
  try {
    // 1. Check if documentation exists
    console.log('📋 Checking documentation database...');
    const allDocs = await memoryOperations.getAllSystemPromptFragments();
    const toolDocs = allDocs.filter(doc => 
      doc.metadata?.category === 'tools' && 
      doc.metadata?.tool_name
    );
    
    totalChecks++;
    if (toolDocs.length === 0) {
      errors.push('No tool documentation found in database');
    } else {
      console.log(`✅ Found ${toolDocs.length} tool documentation entries`);
    }
    
    // 2. Validate each tool document structure
    console.log('\n📝 Validating documentation structure...');
    const requiredFields = ['tool_name', 'tool_type', 'category', 'priority'];
    const validToolTypes = ['python', 'orchestrator', 'bash', 'guide'];
    const validPriorities = ['high', 'medium', 'low'];
    
    for (const doc of toolDocs) {
      totalChecks++;
      const toolName = doc.metadata.tool_name;
      
      // Check required metadata fields
      for (const field of requiredFields) {
        if (!doc.metadata[field]) {
          errors.push(`Tool "${toolName}" missing required field: ${field}`);
        }
      }
      
      // Validate tool type
      if (doc.metadata.tool_type && !validToolTypes.includes(doc.metadata.tool_type)) {
        warnings.push(`Tool "${toolName}" has invalid tool_type: ${doc.metadata.tool_type}`);
      }
      
      // Validate priority
      if (doc.metadata.priority && !validPriorities.includes(doc.metadata.priority)) {
        warnings.push(`Tool "${toolName}" has invalid priority: ${doc.metadata.priority}`);
      }
      
      // Check content structure
      const content = doc.memory;
      if (!content.includes('**Purpose**')) {
        warnings.push(`Tool "${toolName}" missing Purpose section`);
      }
      if (!content.includes('**Example Usage**') && !content.includes('**Access**')) {
        warnings.push(`Tool "${toolName}" missing usage examples`);
      }
    }
    
    // 3. Check Python tools exist
    console.log('\n🐍 Validating Python tools...');
    const pythonTools = toolDocs.filter(doc => doc.metadata.tool_type === 'python');
    
    for (const tool of pythonTools) {
      totalChecks++;
      const toolName = tool.metadata.tool_name;
      const expectedPath = path.join('python-tools', `${toolName}.py`);
      
      try {
        await fs.access(expectedPath);
        console.log(`✅ Python tool exists: ${toolName}`);
      } catch (error) {
        // Try common variations
        const variations = [
          `${toolName.replace(/_/g, '-')}.py`,
          `${toolName.replace(/-/g, '_')}.py`
        ];
        
        let found = false;
        for (const variation of variations) {
          try {
            await fs.access(path.join('python-tools', variation));
            warnings.push(`Tool "${toolName}" found as "${variation}" instead of "${toolName}.py"`);
            found = true;
            break;
          } catch {}
        }
        
        if (!found) {
          errors.push(`Python tool file not found: ${expectedPath}`);
        }
      }
    }
    
    // 4. Check for undocumented Python tools
    console.log('\n🔍 Checking for undocumented Python tools...');
    try {
      const pythonFiles = await fs.readdir('python-tools');
      const documentedTools = new Set(pythonTools.map(t => t.metadata.tool_name));
      
      for (const file of pythonFiles) {
        if (file.endsWith('.py') && file !== '__init__.py' && file !== 'base.py') {
          totalChecks++;
          const toolName = file.replace('.py', '');
          
          // Check various naming conventions
          const possibleNames = [
            toolName,
            toolName.replace(/-/g, '_'),
            toolName.replace(/_/g, '-')
          ];
          
          const isDocumented = possibleNames.some(name => documentedTools.has(name));
          
          if (!isDocumented) {
            warnings.push(`Python tool not documented: ${file}`);
          }
        }
      }
    } catch (error) {
      errors.push(`Could not scan python-tools directory: ${error.message}`);
    }
    
    // 5. Validate search functionality
    console.log('\n🔎 Testing search functionality...');
    try {
      totalChecks++;
      const searchResults = await memoryOperations.searchSystemPromptFragments('shopify', 10);
      const toolResults = searchResults.filter(doc => 
        doc.metadata?.category === 'tools'
      );
      
      if (toolResults.length > 0) {
        console.log(`✅ Search working: Found ${toolResults.length} tool results for "shopify"`);
      } else {
        warnings.push('Search returned no tool results for "shopify" query');
      }
    } catch (error) {
      errors.push(`Search functionality error: ${error.message}`);
    }
    
    // 6. Check documentation completeness
    console.log('\n📊 Checking documentation completeness...');
    const categoryStats = {};
    const priorityStats = {};
    
    for (const doc of toolDocs) {
      const category = doc.metadata.tool_type || 'unknown';
      const priority = doc.metadata.priority || 'unknown';
      
      categoryStats[category] = (categoryStats[category] || 0) + 1;
      priorityStats[priority] = (priorityStats[priority] || 0) + 1;
    }
    
    console.log('\n📈 Documentation Statistics:');
    console.log('By Category:');
    Object.entries(categoryStats).forEach(([cat, count]) => {
      console.log(`  ${cat}: ${count} tools`);
    });
    
    console.log('By Priority:');
    Object.entries(priorityStats).forEach(([priority, count]) => {
      console.log(`  ${priority}: ${count} tools`);
    });
    
    // 7. Summary
    console.log('\n' + '='.repeat(60));
    console.log('📋 VALIDATION SUMMARY');
    console.log('='.repeat(60));
    
    console.log(`Total Checks: ${totalChecks}`);
    console.log(`Errors: ${errors.length}`);
    console.log(`Warnings: ${warnings.length}`);
    console.log(`Tools Documented: ${toolDocs.length}`);
    
    if (errors.length > 0) {
      console.log('\n❌ ERRORS:');
      errors.forEach(error => console.log(`  - ${error}`));
    }
    
    if (warnings.length > 0) {
      console.log('\n⚠️  WARNINGS:');
      warnings.forEach(warning => console.log(`  - ${warning}`));
    }
    
    if (errors.length === 0 && warnings.length === 0) {
      console.log('\n🎉 All validation checks passed!');
      console.log('Tool documentation system is working correctly.');
    } else if (errors.length === 0) {
      console.log('\n✅ No critical errors found.');
      console.log('Some warnings exist but system is functional.');
    } else {
      console.log('\n🚨 Critical errors found that need attention.');
    }
    
    // Exit with appropriate code
    process.exit(errors.length > 0 ? 1 : 0);
    
  } catch (error) {
    console.error('❌ Validation failed:', error);
    process.exit(1);
  }
}

// Help text
if (process.argv.includes('--help') || process.argv.includes('-h')) {
  console.log(`
🔍 Tool Documentation Validation Script

This script validates the integrity of the tool documentation system by checking:
- Database connectivity and content
- Documentation structure and required fields  
- Python tool file existence
- Search functionality
- Completeness statistics

Usage:
  node scripts/validate-tool-docs.js

Exit codes:
  0 - All checks passed (warnings allowed)
  1 - Critical errors found
`);
  process.exit(0);
}

// Run validation
validateToolDocumentation().catch(console.error);