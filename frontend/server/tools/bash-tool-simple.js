import { spawn } from 'child_process';

/**
 * Simple bash execution function for testing
 */
export async function executeBash(command, cwd = '/tmp') {
  return new Promise((resolve) => {
    console.log(`[BASH] Executing: ${command}`);
    console.log(`[BASH] Working directory: ${cwd}`);
    
    const proc = spawn('bash', ['-c', command], {
      cwd,
      env: process.env,
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
      console.log(`[BASH] Exit code: ${code}`);
      if (stdout) console.log(`[BASH] stdout: ${stdout.substring(0, 200)}${stdout.length > 200 ? '...' : ''}`);
      if (stderr) console.log(`[BASH] stderr: ${stderr.substring(0, 200)}${stderr.length > 200 ? '...' : ''}`);
      
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
  });
}