import { Agent, tool, MCPServerStdio } from '@openai/agents';
import { z } from 'zod';
import fs from 'fs/promises';
import path from 'path';
import { executeBashCommand } from '../tools/bash-tool.js';

/**
 * Tool for creating ad-hoc Python tools
 */
const createAdHocTool = tool({
  name: 'create_adhoc_tool',
  description: 'Create a temporary Python tool for immediate use',
  parameters: z.object({
    toolName: z.string().describe('Name for the tool file (without .py extension)'),
    code: z.string().describe('Complete Python code for the tool'),
    description: z.string().describe('Brief description of what the tool does')
  }),
  execute: async ({ toolName, code, description }) => {
    const tmpDir = '/home/pranav/espressobot/frontend/tmp';
    // Ensure tmp directory exists
    await fs.mkdir(tmpDir, { recursive: true });
    
    const tmpPath = `${tmpDir}/${toolName}.py`;
    
    // Add shebang and make executable
    const fullCode = `#!/usr/bin/env python3
"""
${description}
Created: ${new Date().toISOString()}
Type: Ad-hoc tool
"""

${code}`;
    
    await fs.writeFile(tmpPath, fullCode);
    await fs.chmod(tmpPath, 0o755);
    
    return {
      path: tmpPath,
      message: `Created ad-hoc tool at ${tmpPath}`,
      usage: `python3 ${tmpPath} [args]`
    };
  }
});

/**
 * Tool for creating permanent Python tools
 */
const createPermanentTool = tool({
  name: 'create_permanent_tool',
  description: 'Create a permanent Python tool in the python-tools directory',
  parameters: z.object({
    toolName: z.string().describe('Name for the tool file (without .py extension)'),
    code: z.string().describe('Complete Python code for the tool'),
    description: z.string().describe('Brief description of what the tool does'),
    category: z.string().nullable().describe('Category subfolder (e.g., "inventory", "pricing", null for root)')
  }),
  execute: async ({ toolName, code, description, category }) => {
    const baseDir = '/home/pranav/espressobot/frontend/python-tools';
    const targetDir = category ? path.join(baseDir, category) : baseDir;
    const toolPath = path.join(targetDir, `${toolName}.py`);
    
    // Ensure directory exists
    await fs.mkdir(targetDir, { recursive: true });
    
    // Add proper header and documentation
    const fullCode = `#!/usr/bin/env python3
"""
${description}

Created: ${new Date().toISOString()}
Type: Permanent tool
Category: ${category || 'General'}
"""

${code}`;
    
    await fs.writeFile(toolPath, fullCode);
    await fs.chmod(toolPath, 0o755);
    
    // Update tool documentation
    const docPath = `/home/pranav/espressobot/frontend/server/tool-docs/${toolName}.md`;
    const documentation = `# ${toolName}

## Description
${description}

## Location
\`${toolPath}\`

## Category
${category || 'General'}

## Usage
\`\`\`bash
python3 ${toolPath} [arguments]
\`\`\`

## Created
${new Date().toISOString()}
`;
    
    await fs.writeFile(docPath, documentation);
    
    return {
      path: toolPath,
      docPath: docPath,
      message: `Created permanent tool at ${toolPath} with documentation`,
      usage: `python3 ${toolPath} [args]`
    };
  }
});

/**
 * Tool for analyzing and improving existing tools
 */
const analyzeTool = tool({
  name: 'analyze_tool',
  description: 'Analyze an existing tool and suggest improvements',
  parameters: z.object({
    toolPath: z.string().describe('Path to the tool to analyze')
  }),
  execute: async ({ toolPath }) => {
    try {
      const code = await fs.readFile(toolPath, 'utf-8');
      
      // Basic analysis
      const lines = code.split('\n');
      const hasShebang = lines[0]?.startsWith('#!');
      const hasDocstring = code.includes('"""') || code.includes("'''");
      const hasArgparse = code.includes('argparse');
      const hasErrorHandling = code.includes('try:') && code.includes('except');
      const hasMainGuard = code.includes('if __name__ == "__main__":');
      
      const analysis = {
        path: toolPath,
        lineCount: lines.length,
        hasShebang,
        hasDocstring,
        hasArgparse,
        hasErrorHandling,
        hasMainGuard,
        suggestions: []
      };
      
      // Generate suggestions
      if (!hasShebang) {
        analysis.suggestions.push('Add shebang: #!/usr/bin/env python3');
      }
      if (!hasDocstring) {
        analysis.suggestions.push('Add module-level docstring explaining the tool\'s purpose');
      }
      if (!hasArgparse) {
        analysis.suggestions.push('Consider using argparse for better CLI argument handling');
      }
      if (!hasErrorHandling) {
        analysis.suggestions.push('Add try/except blocks for error handling');
      }
      if (!hasMainGuard) {
        analysis.suggestions.push('Add if __name__ == "__main__": guard');
      }
      
      return analysis;
    } catch (error) {
      return {
        error: `Failed to analyze tool: ${error.message}`
      };
    }
  }
});

/**
 * Create MCP servers that will be initialized when the agent runs
 */
function createMCPServers() {
  const shopifyDevMCP = new MCPServerStdio({
    name: 'Shopify Dev Docs',
    fullCommand: 'npx -y @shopify/dev-mcp',
    cacheToolsList: true
  });
  
  const context7MCP = new MCPServerStdio({
    name: 'Context7', 
    fullCommand: 'npx -y @upstash/context7-mcp@latest',
    cacheToolsList: true
  });
  
  return [shopifyDevMCP, context7MCP];
}

/**
 * SWE Agent - Software Engineering Agent
 */
export const sweAgent = new Agent({
  name: 'SWE_Agent',
  instructions: `You are a Software Engineering Agent specialized in creating and maintaining tools for the EspressoBot system. You use advanced reasoning to analyze requirements, design solutions, and implement high-quality code.

## Your Capabilities:
- You have access to MCP servers (Shopify Dev Docs and Context7)
- When you need documentation or API information, the MCP tools will be automatically available
- You can introspect GraphQL schemas, search documentation, and explore external libraries

## Your Responsibilities:
1. Create new Python tools (both ad-hoc and permanent)
2. Analyze and improve existing tools
3. Write comprehensive documentation
4. Ensure code quality and best practices
5. Create tool templates for common patterns

## Python Tool Best Practices:
1. Always include a shebang: #!/usr/bin/env python3
2. Add comprehensive docstrings
3. Use argparse for CLI arguments
4. Include proper error handling
5. Follow PEP 8 style guidelines
6. Add --help documentation
7. Return appropriate exit codes
8. Output JSON when possible for easy parsing
9. Include type hints where beneficial

## Tool Categories:
- **Product Management**: search, create, update products
- **Inventory**: stock management, SKU operations
- **Pricing**: price updates, bulk operations
- **Integration**: external services (SkuVault, Perplexity)
- **Analytics**: reporting and data analysis
- **Utilities**: general purpose tools

## When Creating Tools:
1. Understand the exact requirements
2. Check if similar tools exist (avoid duplication)
3. Use Shopify Dev MCP to verify API fields and mutations before implementing
4. Design for composability (Unix philosophy)
5. Test the tool thoroughly
6. Document usage with examples
7. Consider edge cases and error scenarios

## Using MCP Servers:
- **Before creating Shopify tools**: Always introspect the GraphQL schema to ensure correct field names and types
- **When unsure about API**: Search Shopify docs using search_dev_docs
- **For external integrations**: Use Context7 to explore library documentation (e.g., for SkuVault, Perplexity APIs)

## Available Resources:
- Python 3 with all Shopify/e-commerce libraries
- Access to existing tools in /home/pranav/espressobot/frontend/python-tools/
- Bash for testing and file operations
- Tool documentation directory at /home/pranav/espressobot/frontend/server/tool-docs/
- Shopify Dev MCP for API documentation and GraphQL schema introspection
- Context7 MCP for exploring external repositories and documentation

## MCP Tools Available:
- **Shopify Dev MCP**: Use search_dev_docs, introspect_admin_schema, fetch_docs_by_path for Shopify API reference
- **Context7 MCP**: Use resolve-library-id and get-library-docs to explore external libraries and frameworks

Remember: Good tools are simple, focused, and composable. One tool should do one thing well.`,
  tools: [
    createAdHocTool,
    createPermanentTool,
    analyzeTool,
    tool({
      name: 'bash',
      description: 'Execute bash commands for testing tools or file operations',
      parameters: z.object({
        command: z.string(),
        cwd: z.string().nullable().default('/home/pranav/espressobot/frontend/python-tools')
      }),
      execute: executeBashCommand
    })
  ],
  mcpServers: createMCPServers(),
  model: 'o3' // Using o3 reasoning model for complex software engineering tasks
});

/**
 * Create a SWE agent with a specific task
 */
export function createSWEAgent(task) {
  return new Agent({
    name: 'SWE_Agent_Specialized',
    instructions: `${sweAgent.instructions}\n\nYour specific task: ${task}`,
    tools: sweAgent.tools,
    mcpServers: createMCPServers(), // Create fresh MCP instances on demand
    model: 'o3' // Using o3 reasoning model for complex software engineering tasks
  });
}