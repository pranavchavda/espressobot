#!/usr/bin/env node

import { spawn } from 'child_process';

console.log('🔧 Testing Direct Bash Execution\n');

function executeCommand(command, cwd = '/tmp') {
  return new Promise((resolve) => {
    console.log(`\nExecuting: ${command}`);
    console.log(`CWD: ${cwd}`);
    
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
      console.log(`Exit code: ${code}`);
      if (stdout) console.log(`stdout: ${stdout}`);
      if (stderr) console.log(`stderr: ${stderr}`);
      resolve({ code, stdout, stderr });
    });
    
    proc.on('error', (err) => {
      console.error(`Process error:`, err);
      resolve({ error: err.message });
    });
  });
}

// Run tests
await executeCommand('echo "Hello from bash!"');
await executeCommand('ls -la | head -5');
await executeCommand('python3 --version');
await executeCommand('ls /home/pranav/idc/tools/ | grep product | head -5');

console.log('\n✅ Tests completed!');