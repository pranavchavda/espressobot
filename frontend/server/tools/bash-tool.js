import { tool } from '@openai/agents';
import { z } from 'zod';
import { spawn } from 'child_process';
import path from 'path';

/**
 * Core bash execution function
 */
export const executeBashCommand = async ({ command, cwd = '/tmp' }) => {
  return new Promise((resolve) => {
    console.log(`[BASH] Executing: ${command}`);
    console.log(`[BASH] Working directory: ${cwd}`);
    
    // Safety checks
    const dangerousPatterns = [
      /rm\s+-rf\s+\//,  // rm -rf /
      /:\(\)\{.*\|:&\};:/,  // Fork bomb
      /mkfs/,  // Formatting commands
      /dd\s+if=.*of=\/dev/,  // Direct disk writes
    ];
    
    for (const pattern of dangerousPatterns) {
      if (pattern.test(command)) {
        resolve({
          success: false,
          error: 'Command blocked for safety reasons',
          stdout: '',
          stderr: 'This command pattern is not allowed'
        });
        return;
      }
    }
    
    // Execute command
    const proc = spawn('bash', ['-c', command], {
      cwd,
      env: {
        ...process.env,
        // Ensure Python tools have access to Shopify credentials
        SHOPIFY_SHOP_URL: process.env.SHOPIFY_SHOP_URL,
        SHOPIFY_ACCESS_TOKEN: process.env.SHOPIFY_ACCESS_TOKEN,
        OPENAI_API_KEY: process.env.OPENAI_API_KEY,
        PERPLEXITY_API_KEY: process.env.PERPLEXITY_API_KEY,
      },
      // Capture output
      shell: false
    });
    
    let stdout = '';
    let stderr = '';
    
    proc.stdout.on('data', (data) => {
      stdout += data.toString();
    });
    
    proc.stderr.on('data', (data) => {
      stderr += data.toString();
    });
    
    proc.on('close', (code) => {
      const result = {
        success: code === 0,
        exitCode: code,
        stdout: stdout.trim(),
        stderr: stderr.trim()
      };
      
      console.log(`[BASH] Exit code: ${code}`);
      if (stdout) console.log(`[BASH] stdout: ${stdout.substring(0, 200)}${stdout.length > 200 ? '...' : ''}`);
      if (stderr) console.log(`[BASH] stderr: ${stderr.substring(0, 200)}${stderr.length > 200 ? '...' : ''}`);
      
      // Format result for agent
      if (code === 0) {
        resolve(stdout || 'Command executed successfully (no output)');
      } else {
        resolve(`Command failed with exit code ${code}\n${stderr || stdout || 'No error output'}`);
      }
    });
    
    proc.on('error', (err) => {
      console.error(`[BASH] Process error:`, err);
      resolve(`Failed to execute command: ${err.message}`);
    });
    
    // Timeout after 30 seconds
    setTimeout(() => {
      proc.kill();
      resolve('Command timed out after 30 seconds');
    }, 30000);
  });
};

/**
 * Bash tool for agents - provides controlled command line access
 */
export const bashTool = tool({
  name: 'bash',
  description: `Execute bash commands. You have access to:
    - Python tools in /home/pranav/idc/tools/ and /home/pranav/espressobot/frontend/server/python-tools/
    - Standard Unix utilities (grep, awk, sed, jq, etc.)
    - Python 3 with all Shopify/e-commerce libraries installed
    - Can read/write temporary files in /tmp/
    
    Examples:
    - python3 /home/pranav/idc/tools/search_products.py "coffee" --status active
    - python3 /home/pranav/idc/tools/get_product.py SKU123 | jq '.price'
    - echo "SKU123,49.99" > /tmp/price_updates.csv && python3 /home/pranav/idc/tools/bulk_price_update.py /tmp/price_updates.csv
    
    Safety notes:
    - Always use absolute paths for tools
    - Be careful with quotes and escaping
    - Check command output for errors`,
  parameters: z.object({
    command: z.string().describe('The bash command to execute'),
    cwd: z.string().nullable().default('/tmp').describe('Working directory (defaults to /tmp)')
  }),
  execute: executeBashCommand
});

/**
 * Create a bash-enabled agent
 */
export function createBashAgent(name, task) {
  const { Agent } = require('@openai/agents');
  
  return new Agent({
    name,
    instructions: `You are a bash-enabled agent. Your task: ${task}
    
    You have full bash access with Python tools available at:
    - /home/pranav/idc/tools/ (main tools)
    - /home/pranav/espressobot/frontend/server/python-tools/ (additional tools)
    
    Best practices:
    1. Always check if a tool exists before using it: ls -la /path/to/tool.py
    2. Use --help to understand tool parameters: python3 tool.py --help
    3. Check exit codes and stderr for errors
    4. Use temporary files in /tmp/ when needed
    5. Chain commands with && for sequential operations
    6. Use jq for JSON parsing when needed
    
    Example workflow:
    - First explore available tools: ls /home/pranav/idc/tools/*.py
    - Check tool usage: python3 /home/pranav/idc/tools/search_products.py --help
    - Execute tool: python3 /home/pranav/idc/tools/search_products.py "query" --status active
    - Process results: ... | jq '.[] | select(.vendor == "Test")'`,
    tools: [bashTool],
    model: 'gpt-4.1-mini'
  });
}