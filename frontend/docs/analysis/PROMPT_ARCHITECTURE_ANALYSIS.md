# Prompt Architecture Analysis & Migration Plan

## Executive Summary

The system is successfully transitioning from subprocess-based Python tools to native MCP (Model Context Protocol) tools. This analysis identifies critical prompt updates needed to support this architectural shift.

## Current State Analysis

### 1. Subprocess-Based Tool References Found

**Primary Locations:**
- `server/tools/bash-tool.js` - Core bash tool implementation
- `server/dynamic-bash-orchestrator.js` - Main orchestrator
- `server/prompts/bash-agent.md` - Agent instructions 
- `server/prompts/bash-agent-enhanced.md` - Enhanced agent instructions
- `server/prompts/orchestrator.md` - Orchestrator instructions

**Current Pattern References:**
```bash
# Found in prompts and code:
python3 /home/pranav/espressobot/frontend/python-tools/[tool_name].py --args
cd /home/pranav/espressobot/frontend/python-tools && python script.py
```

### 2. MCP Tool Integration Status

**Successfully Implemented:**
- 27 tools migrated to MCP (see `python-tools/MCP_MIGRATION_STATUS.md`)
- MCP server running at `python-tools/mcp-server.py`
- Orchestrator has MCP tool wrappers
- Direct tool access available via orchestrator

**Integration Points:**
- Orchestrator: Direct MCP tool access (lines 742-757 in `dynamic-bash-orchestrator.js`)
- Bash agents: Still using subprocess pattern
- Task planning: References old tool discovery system

## Critical Issues Identified

### 1. **Dual-Path Confusion**
- Orchestrator has MCP tools but still instructs bash agents to use subprocess
- Bash agents receive instructions to use python scripts that are now MCP tools
- Tool discovery system references old subprocess patterns

### 2. **Context Management Mismatch**
- Prompts still reference `/python-tools/` directory access
- Instructions focus on bash execution rather than direct tool calls
- No guidance on when to use MCP vs subprocess

### 3. **Workflow Inefficiencies**
- Bash agents executing `python3 /path/to/tool.py` instead of direct MCP calls
- Multiple layers of abstraction (orchestrator → bash agent → subprocess → MCP)
- Redundant tool validation and help text parsing

## Detailed Prompt Issues

### A. Orchestrator Prompts (`dynamic-bash-orchestrator.js`)

**Current Issues:**
```javascript
// Lines 742-757: Contradictory instructions
"### MCP Tools Available: You have 13 native MCP tools loaded"
"### How to Instruct Bash Agents: Tell them EXACTLY what to run"
"- ✅ GOOD: Run: python3 /path/to/tool.py --args"
```

**Problem:** Orchestrator knows about MCP tools but still instructs bash agents to use subprocess.

### B. Bash Agent Prompts (`bash-tool.js`, `bash-agent-enhanced.md`)

**Current Issues:**
```javascript
// Lines 11-30: Subprocess-focused instructions
"You are a bash-enabled agent with full access to Python tools in /home/pranav/espressobot/frontend/python-tools/"
"ALWAYS use the Python tools in /home/pranav/espressobot/frontend/python-tools/ for Shopify operations"
"Examples of CORRECT usage: python3 /home/pranav/espressobot/frontend/python-tools/tool.py"
```

**Problem:** Bash agents don't know MCP tools exist and are instructed to use subprocess.

### C. Task Planning Agent (`task-planning-agent.js`)

**Current Issues:**
```javascript
// Lines 158-164: References old tool discovery
"AVAILABLE TOOLS for reference: ${allToolNames.join(', ')}"
"Additional tools available to bash agents: All Python tools in /home/pranav/idc/tools/"
```

**Problem:** Still references old tool discovery system.

## Migration Strategy

### Phase 1: Immediate Updates (High Priority)

#### 1.1 Update Orchestrator Decision Logic
**File:** `server/dynamic-bash-orchestrator.js`

**Current Decision Tree (Lines 780-790):**
```javascript
// STEP 1: ALWAYS try MCP tools FIRST for simple operations
// STEP 2: Only spawn bash agents for complex workflows
```

**Needed Changes:**
- Expand MCP tool usage instructions
- Reduce bash agent spawning for simple operations
- Update tool capability descriptions

#### 1.2 Update Bash Agent Instructions
**File:** `server/tools/bash-tool.js`

**Current Core Issue (Lines 11-30):**
```javascript
"ALWAYS use the Python tools in /home/pranav/espressobot/frontend/python-tools/"
"Examples of CORRECT usage: python3 /home/pranav/espressobot/frontend/python-tools/tool.py"
```

**Needed Changes:**
- Add MCP tool awareness
- Provide fallback to subprocess only when MCP unavailable
- Update examples to show MCP-first approach

#### 1.3 Update Prompt Files
**Files:** `server/prompts/bash-agent.md`, `server/prompts/bash-agent-enhanced.md`

**Current Focus:** Subprocess execution patterns
**Needed Changes:** Hybrid approach with MCP awareness

### Phase 2: Context Management Updates

#### 2.1 Tool Discovery System
**File:** `server/custom-tool-discovery.js`

**Current Issue:** References filesystem-based tool discovery
**Needed Changes:** Integrate MCP tool discovery

#### 2.2 Task Planning Context
**File:** `server/agents/task-planning-agent.js`

**Current Issue:** References old tool names
**Needed Changes:** Use MCP tool names and capabilities

### Phase 3: Workflow Optimization

#### 3.1 Direct Tool Execution
**Goal:** Reduce unnecessary bash agent spawning for simple operations

**Current Inefficient Pattern:**
```
User Request → Orchestrator → Bash Agent → Subprocess → MCP Tool
```

**Desired Efficient Pattern:**
```
User Request → Orchestrator → MCP Tool (direct)
```

#### 3.2 Bash Agent Scope Reduction
**Goal:** Limit bash agents to genuinely complex workflows

**Examples of Operations That Should Stay MCP-Direct:**
- Single product updates
- Simple searches
- Basic inventory management
- Tag operations

**Examples of Operations That Should Use Bash Agents:**
- Multi-step workflows requiring decision trees
- Operations requiring file manipulation
- Complex data transformations
- Error recovery workflows

## Implementation Plan

### Week 1: Core Prompt Updates
1. **Update orchestrator decision logic** (Priority: Critical)
   - Expand MCP tool usage section
   - Reduce bash agent spawning criteria
   - Update tool capability descriptions

2. **Update bash agent prompts** (Priority: High)
   - Add MCP tool awareness to bash-tool.js
   - Update prompt files with hybrid approach
   - Provide clear fallback patterns

### Week 2: Context System Updates
1. **Integrate MCP tool discovery** (Priority: Medium)
   - Update custom-tool-discovery.js
   - Modify task planning context
   - Update tool capability descriptions

2. **Test and validate** (Priority: High)
   - Comprehensive testing of new prompt patterns
   - Performance comparison (MCP vs subprocess)
   - Error handling validation

### Week 3: Workflow Optimization
1. **Optimize tool selection logic** (Priority: Medium)
   - Implement smart tool routing
   - Add performance monitoring
   - Create fallback mechanisms

2. **Documentation and training** (Priority: Low)
   - Update system documentation
   - Create troubleshooting guides
   - Performance optimization recommendations

## Success Metrics

### Performance Metrics
- **Tool Execution Time:** MCP tools should be 2-3x faster than subprocess
- **Error Rate:** Should maintain or improve current error rates
- **Resource Usage:** Should reduce CPU/memory usage

### Functionality Metrics
- **Tool Availability:** All 27 MCP tools should be accessible
- **Fallback Success:** Subprocess fallback should work seamlessly
- **User Experience:** No change in functionality from user perspective

## Risk Assessment

### High Risk Items
1. **Prompt Confusion:** Agents receiving mixed instructions about tool usage
2. **Tool Discovery Failures:** New tool discovery not finding MCP tools
3. **Performance Regression:** MCP tools performing worse than subprocess

### Mitigation Strategies
1. **Gradual Rollout:** Update prompts incrementally with testing
2. **Fallback Mechanisms:** Ensure subprocess path remains available
3. **Monitoring:** Implement comprehensive logging for tool usage patterns

## Next Steps

1. **Immediate Action Required:** Update orchestrator decision logic (Lines 780-790 in dynamic-bash-orchestrator.js)
2. **High Priority:** Update bash agent prompts to include MCP awareness
3. **Medium Priority:** Integrate MCP tool discovery into context system
4. **Ongoing:** Monitor performance and user experience

## Conclusion

The prompt architecture needs significant updates to support the MCP transition. The current system has contradictory instructions that can confuse agents and lead to inefficient tool usage. The proposed migration strategy will ensure agents understand when to use MCP tools directly vs. when to fall back to subprocess execution, ultimately improving performance and reliability.