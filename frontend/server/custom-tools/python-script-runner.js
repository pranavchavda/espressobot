import { spawn } from 'child_process';
import fs from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * Execute arbitrary Python code with full system access
 * This tool allows running any Python script on the system
 */
async function runPythonScript(pythonCode) {
  // Create a unique temporary file name
  const tempFileName = `script_${crypto.randomBytes(8).toString('hex')}.py`;
  const tempFilePath = path.join(__dirname, '../python-tools/tmp', tempFileName);
  
  try {
    // Write the Python code to a temporary file
    await fs.writeFile(tempFilePath, pythonCode, 'utf8');
    
    // Execute the Python script
    return new Promise((resolve, reject) => {
      const pythonProcess = spawn('python3', [tempFilePath], {
        env: {
          ...process.env,
          PYTHONPATH: path.join(__dirname, '../python-tools')
        }
      });
      
      let stdout = '';
      let stderr = '';
      
      pythonProcess.stdout.on('data', (data) => {
        stdout += data.toString();
      });
      
      pythonProcess.stderr.on('data', (data) => {
        stderr += data.toString();
      });
      
      pythonProcess.on('close', async (code) => {
        // Clean up the temporary file
        try {
          await fs.unlink(tempFilePath);
        } catch (err) {
          console.error('Error cleaning up temp file:', err);
        }
        
        if (code === 0) {
          resolve({
            success: true,
            output: stdout,
            error: stderr || null,
            exitCode: code
          });
        } else {
          resolve({
            success: false,
            output: stdout || null,
            error: stderr || `Process exited with code ${code}`,
            exitCode: code
          });
        }
      });
      
      pythonProcess.on('error', async (err) => {
        // Clean up the temporary file
        try {
          await fs.unlink(tempFilePath);
        } catch (cleanupErr) {
          console.error('Error cleaning up temp file:', cleanupErr);
        }
        
        reject(new Error(`Failed to execute Python script: ${err.message}`));
      });
    });
  } catch (error) {
    // If file write fails, ensure cleanup
    try {
      await fs.unlink(tempFilePath);
    } catch (cleanupErr) {
      // Ignore cleanup errors if file wasn't created
    }
    throw error;
  }
}

export { runPythonScript };