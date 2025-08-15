import { tool } from '@openai/agents';
import { z } from 'zod';
import fs from 'fs/promises';
import path from 'path';

/**
 * Simple File Operations Tool - Move, copy, and manage files without bash
 */
export const fileOperationsTool = tool({
  name: 'file_operations',
  description: `Perform file operations like move, copy, delete without using bash. 
    This is more reliable for file paths with special characters.
    
    Operations:
    - move: Move a file from source to destination
    - copy: Copy a file from source to destination
    - delete: Delete a file
    - exists: Check if a file exists
    - mkdir: Create a directory`,
  parameters: z.object({
    operation: z.enum(['move', 'copy', 'delete', 'exists', 'mkdir']).describe('Operation to perform'),
    source: z.string().describe('Source file path'),
    destination: z.string().default('').describe('Destination path (for move/copy operations)'),
    recursive: z.boolean().default(false).describe('For mkdir, create parent directories if needed'),
  }),
  execute: async ({ operation, source, destination, recursive }) => {
    try {
      console.log(`[FILE OPS] Operation: ${operation}, Source: ${source}, Destination: ${destination}`);
      
      switch (operation) {
        case 'move':
          if (!destination) {
            return { success: false, error: 'Destination path required for move operation' };
          }
          
          // Ensure destination directory exists
          const destDir = path.dirname(destination);
          await fs.mkdir(destDir, { recursive: true });
          
          // Move the file
          await fs.rename(source, destination);
          
          return {
            success: true,
            message: `File moved successfully from ${source} to ${destination}`,
            sourcePath: source,
            destinationPath: destination
          };
          
        case 'copy':
          if (!destination) {
            return { success: false, error: 'Destination path required for copy operation' };
          }
          
          // Ensure destination directory exists
          const copyDestDir = path.dirname(destination);
          await fs.mkdir(copyDestDir, { recursive: true });
          
          // Copy the file
          await fs.copyFile(source, destination);
          
          return {
            success: true,
            message: `File copied successfully from ${source} to ${destination}`,
            sourcePath: source,
            destinationPath: destination
          };
          
        case 'delete':
          await fs.unlink(source);
          return {
            success: true,
            message: `File deleted successfully: ${source}`,
            deletedPath: source
          };
          
        case 'exists':
          try {
            await fs.access(source);
            const stats = await fs.stat(source);
            return {
              success: true,
              exists: true,
              path: source,
              isFile: stats.isFile(),
              isDirectory: stats.isDirectory(),
              size: stats.size,
              modified: stats.mtime
            };
          } catch (error) {
            return {
              success: true,
              exists: false,
              path: source,
              message: 'File does not exist'
            };
          }
          
        case 'mkdir':
          await fs.mkdir(source, { recursive: recursive });
          return {
            success: true,
            message: `Directory created: ${source}`,
            path: source
          };
          
        default:
          return {
            success: false,
            error: `Unknown operation: ${operation}`
          };
      }
      
    } catch (error) {
      console.error('[FILE OPS] Error:', error);
      return {
        success: false,
        error: `File operation failed: ${error.message}`,
        operation: operation,
        source: source,
        destination: destination
      };
    }
  }
});

// Export as default for easier imports
export default fileOperationsTool;