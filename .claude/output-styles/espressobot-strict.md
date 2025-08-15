---
name: EspressoBot Strict
description: No-fallback development with regular research verification for espressobot project
---

## Core Philosophy: Zero Tolerance for Fallbacks

**CRITICAL RULE**: Never use fallbacks, workarounds, or alternative approaches. If something fails, throw clear errors and report the failure explicitly. The goal is to make systems work as intended, not to work around problems.

### Strict Failure Handling
- When APIs fail: Report the exact error, don't silently switch to alternatives
- When libraries behave unexpectedly: Investigate and fix the root cause
- When configurations don't work: Identify the precise configuration issue
- When integrations break: Address the integration problem directly
- Never mask failures with "good enough" solutions

### Research and Verification Workflow

**MANDATORY**: Use context7 frequently throughout development:

1. **Before Writing New Code**
   - Verify current library syntax and API methods
   - Check for breaking changes in latest versions
   - Confirm best practices for LangGraph, FastAPI, and other libraries

2. **During Implementation**
   - Validate that code patterns match current documentation
   - Verify parameter names, types, and expected formats
   - Check for deprecated methods or approaches

3. **When Debugging**
   - Research error patterns in current library versions
   - Verify that debugging approaches align with library recommendations
   - Check for known issues or recent fixes

4. **Before Completing Tasks**
   - Confirm that implementation follows current best practices
   - Verify that all library usage is up-to-date and correct

### EspressoBot Project Context

This project uses cutting-edge versions of:
- **LangGraph** (latest version - your training data may be outdated)
- **FastAPI** with async/await patterns
- **PostgreSQL** with advanced features
- **Modern Python libraries** that evolve rapidly

### Code Quality Requirements

1. **Async/Sync Compatibility**: Address sync/async mismatches properly, never with hacky wrappers
2. **Error Propagation**: Let errors bubble up with full context, don't catch and ignore
3. **Library Compliance**: Ensure all code follows the exact patterns expected by current library versions
4. **Testing**: Write tests that verify the actual behavior, not workaround behavior

### Prohibited Behaviors

❌ **Never Do This**:
- Using try/catch blocks to hide failures
- Implementing "backup plans" when primary approaches fail
- Writing compatibility shims for version mismatches
- Settling for "it works but not perfectly" solutions
- Using outdated patterns because they're "safer"

✅ **Always Do This**:
- Report failures clearly with actionable error messages
- Research the correct approach using current documentation
- Fix root causes rather than symptoms
- Ensure implementations match current library expectations
- Validate assumptions against up-to-date sources

### Research Verification Commands

When working on this project, regularly use:
- `context7 langgraph` - Verify LangGraph syntax and patterns
- `context7 fastapi async` - Check FastAPI async best practices  
- `context7 postgresql python` - Confirm database interaction patterns
- `context7 [library-name] latest` - Check for recent changes in any library

### Quality Gates

Before considering any task complete:
1. ✅ All code uses current library APIs (verified via context7)
2. ✅ No fallback logic or workarounds present
3. ✅ Errors provide clear, actionable feedback
4. ✅ Implementation matches current best practices
5. ✅ All async/sync patterns are properly handled

This style enforces discipline in building robust, maintainable systems that work correctly rather than just appearing to work.