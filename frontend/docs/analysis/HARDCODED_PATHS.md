# Hardcoded Absolute Paths in EspressoBot

## Files with `/home/pranav/espressobot` references:

### Core Operational Files:
1. **server/tools/bash-tool.js**
   - Line 245: `Python tools in /home/pranav/espressobot/frontend/python-tools/`

2. **server/dynamic-bash-orchestrator.js**
   - Line 862: `/home/pranav/espressobot/frontend/server/prompts/idc-business-rules.md`
   - Line 863: `/home/pranav/espressobot/frontend/server/tool-docs/TOOL_USAGE_GUIDE.md`

3. **server/agents/swe-agent-connected.js**
   - Line 17: `const tmpDir = '/home/pranav/espressobot/frontend/tmp';`
   - Line 186: `cwd: z.string().nullable().default('/home/pranav/espressobot/frontend/python-tools')`

4. **server/prompts/orchestrator.md**
   - Line 36: `Tools are located in /home/pranav/espressobot/frontend/python-tools/`

### Documentation Files:
- CLAUDE.md
- MCP_TEST_RESULTS.md
- PROMPT_ARCHITECTURE_ANALYSIS.md
- MEMORY_SYSTEM_DOCUMENTATION.md
- docs/CONVERSATION_TOPIC_SYSTEM.md
- docs/idc-to-espressobot-migration-analysis.md
- docs/multi-agent-prompt-structure.md
- server/tool-docs/TOOL_USAGE_GUIDE.md
- server/tool-docs/WORKFLOW_EXAMPLES.md
- python-tools/README.md

### Script Files:
- scripts/add-tool-documentation.js
- server/create-rag-orchestrator.js

## Recommendations:
1. Replace hardcoded paths with relative paths or environment variables
2. Use `process.cwd()` or `__dirname` for dynamic path resolution
3. Create a central configuration file for paths
4. Update documentation to use placeholders like `<PROJECT_ROOT>`