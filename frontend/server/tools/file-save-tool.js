import { tool } from '@openai/agents';
import { z } from 'zod';
import fs from 'fs/promises';
import path from 'path';
import os from 'os';

/**
 * Save File Tool - Saves uploaded file data to disk for processing
 * Useful for working with files using bash tools
 */
export const saveFileTool = tool({
  name: 'save_uploaded_file',
  description: `Save an uploaded file to disk so it can be processed with bash tools. 
    This is particularly useful for:
    - PDFs that need text extraction with pdftotext
    - Files that need processing with command-line tools
    - Creating temporary files for batch processing
    
    The tool will save the file to a temporary directory and return the file path.`,
  parameters: z.object({
    fileName: z.string().describe('Desired filename (with extension)'),
    useGlobalData: z.boolean().default(true).describe('Use the globally uploaded file data (default: true)'),
    base64Data: z.string().default('').describe('Alternative base64 data to save (if not using global data)'),
  }),
  execute: async ({ fileName, useGlobalData, base64Data }) => {
    try {
      // Determine what data to use
      let dataToSave = null;
      let isBase64 = false;
      
      if (useGlobalData && global.currentFileData) {
        // Use global file data
        if (global.currentFileData.encoding === 'text') {
          dataToSave = global.currentFileData.content;
          isBase64 = false;
        } else if (global.currentFileBase64) {
          dataToSave = global.currentFileBase64;
          isBase64 = true;
        } else if (global.currentFileData.data) {
          dataToSave = global.currentFileData.data;
          isBase64 = true;
        }
      } else if (base64Data) {
        dataToSave = base64Data;
        isBase64 = true;
      }
      
      if (!dataToSave) {
        return {
          success: false,
          error: 'No file data available to save. Please upload a file first.'
        };
      }
      
      // Create temp directory if it doesn't exist
      const tempDir = path.join(os.tmpdir(), 'espressobot-files');
      await fs.mkdir(tempDir, { recursive: true });
      
      // Generate safe filename - keep it simple to avoid bash issues
      const timestamp = Date.now();
      const safeFileName = fileName.replace(/[^a-zA-Z0-9.-]/g, '_');
      // Use a simpler path structure
      const filePath = path.join(tempDir, safeFileName);
      
      // Save the file
      if (isBase64) {
        // Remove data URL prefix if present
        const base64Clean = dataToSave.replace(/^data:.*?;base64,/, '');
        const buffer = Buffer.from(base64Clean, 'base64');
        await fs.writeFile(filePath, buffer);
      } else {
        // Save text content directly
        await fs.writeFile(filePath, dataToSave, 'utf-8');
      }
      
      // Get file stats
      const stats = await fs.stat(filePath);
      
      return {
        success: true,
        filePath: filePath,
        fileName: safeFileName,
        fileSize: stats.size,
        message: `File saved successfully to: ${filePath}`,
        hint: 'File saved. You can now:\n1. Use the file_operations tool to move/copy this file (recommended)\n2. For PDFs, use bash: pdftotext "' + filePath + '" -\n3. Or use bash to move: mv "' + filePath + '" "/target/path/filename"'
      };
      
    } catch (error) {
      console.error('File save error:', error);
      return {
        success: false,
        error: `Failed to save file: ${error.message}`
      };
    }
  }
});

// Export as default for easier imports
export default saveFileTool;