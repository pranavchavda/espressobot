# EspressoBot Prompt Porting Strategy

## Overview
This document outlines a strategic approach to port the comprehensive Old-Prompt.md content into EspressoBot's Shell Agency architecture, ensuring no information loss while optimizing for the new system.

## Current Architecture Context
- **EspressoBot Shell Agency**: Agents operate in bash shell with direct tool access
- **Memory System**: Mem0 integration for persistent context
- **Task Management**: Integrated task tracking with markdown files
- **Dynamic Orchestrator**: Main agent that spawns specialized bash agents

## Porting Strategy

### 1. **Core Identity & Purpose** (Priority: HIGH)
**Content**: Lines 1-8 from Old-Prompt.md
**Strategy**: 
- Integrate into `/server/prompts/bash-agent.md` as foundational identity
- Add to dynamic orchestrator instructions in `/server/dynamic-bash-orchestrator.js`
- Preserve the emphasis on being an e-commerce expert for iDrinkCoffee.com

### 2. **Tool Documentation** (Priority: CRITICAL)
**Content**: Lines 22-62 (Available Tools section)
**Strategy**:
- Create `/server/tool-docs/TOOL_USAGE_GUIDE.md` with comprehensive tool documentation
- Update bash agent prompt to reference this guide
- Include tool examples and best practices
- Add tool discovery hints to orchestrator instructions

### 3. **Workflow Examples** (Priority: HIGH)
**Content**: Lines 83-431 (Common Workflows)
**Strategy**:
- Create `/server/tool-docs/WORKFLOW_EXAMPLES.md` 
- Organize by task type (search/update, creation, bulk ops, etc.)
- Include in bash agent context for reference
- Add workflow pattern recognition to orchestrator

### 4. **Business Rules & Conventions** (Priority: CRITICAL)
**Content**: Lines 457-502, 569-592 (Conventions & IDC-specific notes)
**Strategy**:
- Create `/server/prompts/idc-business-rules.md`
- Include critical business logic:
  - Preorder tag management
  - Inventory policy rules
  - Sale end date formatting
  - Channel configurations
  - Pricing conventions
- Inject into both orchestrator and bash agent contexts

### 5. **Product Guidelines** (Priority: HIGH)
**Content**: Lines 557-567 + docs/product-guidelines/
**Strategy**:
- Keep existing documentation structure in `/docs/product-guidelines/`
- Create summary reference in `/server/prompts/product-guidelines-summary.md`
- Include key principles in agent instructions
- Reference full docs for detailed operations

### 6. **Task Management Integration** (Priority: MEDIUM)
**Content**: Lines 61-81 (Taskwarrior)
**Strategy**:
- Since we have our own task system, create mapping guide
- Document in `/server/tool-docs/TASK_MANAGEMENT.md`
- Show how to use EspressoBot's task system for similar workflows

### 7. **Memory System Integration** (Priority: HIGH)
**Content**: Lines 582-592 (Memories section)
**Strategy**:
- Extract key operational memories
- Store in Mem0 as persistent context
- Create memory categories:
  - Tool usage patterns
  - Common fixes
  - Business rules
  - Vendor-specific information

### 8. **Error Handling & Best Practices** (Priority: MEDIUM)
**Content**: Lines 483-556
**Strategy**:
- Create `/server/prompts/error-handling-guide.md`
- Include in bash agent instructions
- Add error pattern recognition to tools

## Implementation Plan

### Phase 1: Core Integration (Immediate)
1. Update `/server/prompts/bash-agent.md` with:
   - Core identity (lines 1-8)
   - Tool access information
   - Key business rules
   
2. Update `/server/dynamic-bash-orchestrator.js` instructions with:
   - Business context
   - Workflow patterns
   - Error handling guidance

### Phase 2: Documentation Structure (Day 1-2)
1. Create tool documentation hierarchy:
   ```
   /server/tool-docs/
   ├── TOOL_USAGE_GUIDE.md
   ├── WORKFLOW_EXAMPLES.md
   ├── BUSINESS_RULES.md
   └── ERROR_HANDLING.md
   ```

2. Create prompt templates:
   ```
   /server/prompts/
   ├── bash-agent.md (updated)
   ├── idc-business-rules.md
   ├── product-guidelines-summary.md
   └── error-handling-guide.md
   ```

### Phase 3: Memory Population (Day 2-3)
1. Extract and categorize memories:
   - Tool-specific knowledge
   - Business rules
   - Common patterns
   - Vendor information

2. Store in Mem0 with proper tags for retrieval

### Phase 4: Testing & Refinement (Day 3-4)
1. Test common workflows
2. Verify business rule compliance
3. Ensure no information loss
4. Optimize prompt sizes

## Key Considerations

### 1. **Prompt Size Management**
- Break large sections into separate files
- Use dynamic loading based on task context
- Prioritize most-used information in core prompts

### 2. **Context Injection Strategy**
- Orchestrator gets high-level business context
- Bash agents get task-specific details
- Use task context to inject relevant workflows

### 3. **Memory vs. Static Prompts**
- Static: Core identity, tool locations, critical rules
- Memory: Learned patterns, temporary rules, user preferences

### 4. **Version Control**
- Keep Old-Prompt.md as reference
- Document all transformations
- Maintain change log for business rules

## Success Metrics
1. All tools documented and accessible
2. Business rules enforced correctly
3. Workflows execute without information gaps
4. Agents can handle all previous use cases
5. No degradation in task completion quality

## Risk Mitigation
1. **Information Loss**: Create comprehensive mapping document
2. **Context Overflow**: Implement smart context loading
3. **Business Rule Conflicts**: Centralize rule management
4. **Tool Discovery**: Improve tool search capabilities

## Next Steps
1. Review and approve strategy
2. Begin Phase 1 implementation
3. Create tracking document for progress
4. Test with common use cases
5. Iterate based on results