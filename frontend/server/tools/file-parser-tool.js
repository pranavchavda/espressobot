import { tool } from '@openai/agents';
import { z } from 'zod';
import pdfParse from 'pdf-parse';
import xlsx from 'xlsx';
import { parse as csvParse } from 'csv-parse/sync';
import Papa from 'papaparse';
import fs from 'fs/promises';
import path from 'path';

/**
 * Parse File Tool - Extracts content from various file formats
 * Supports: PDF, Excel (XLSX/XLS), CSV, Text files
 */
export const parseFileTool = tool({
  name: 'parse_file',
  description: `Extract and parse content from uploaded files. Supports:
    - PDF: Extracts text content from PDF files
    - Excel: Reads spreadsheet data from XLSX/XLS files
    - CSV: Parses comma-separated values
    - Text: Reads plain text, markdown, and log files
    
    The tool automatically detects the file type and uses the appropriate parser.`,
  parameters: z.object({
    fileType: z.enum(['pdf', 'excel', 'csv', 'text', 'file']).describe('Type of file to parse'),
    base64Data: z.string().optional().describe('Base64 encoded file data (for binary files)'),
    textContent: z.string().optional().describe('Raw text content (for text files)'),
    fileName: z.string().optional().describe('Original filename for context'),
  }),
  execute: async ({ fileType, base64Data, textContent, fileName }) => {
    try {
      // Check if we have file data from global context
      const fileData = global.currentFileData;
      if (!fileData && !base64Data && !textContent) {
        return {
          success: false,
          error: 'No file data provided. Please upload a file first.'
        };
      }

      let content = '';
      let parsedData = null;

      // Use provided data or fall back to global file data
      const actualFileType = fileType || fileData?.type || 'file';
      const actualBase64 = base64Data || global.currentFileBase64;
      const actualTextContent = textContent || fileData?.content;
      const actualFileName = fileName || fileData?.name || 'unknown';

      switch (actualFileType) {
        case 'pdf':
          if (!actualBase64) {
            return { success: false, error: 'PDF files require base64 data' };
          }
          
          // Extract base64 data (remove data URL prefix if present)
          const pdfBase64 = actualBase64.replace(/^data:.*?;base64,/, '');
          const pdfBuffer = Buffer.from(pdfBase64, 'base64');
          
          try {
            const pdfData = await pdfParse(pdfBuffer);
            content = pdfData.text;
            parsedData = {
              pages: pdfData.numpages,
              info: pdfData.info,
              metadata: pdfData.metadata,
              textLength: pdfData.text.length
            };
          } catch (pdfError) {
            return {
              success: false,
              error: `Failed to parse PDF: ${pdfError.message}`
            };
          }
          break;

        case 'excel':
          if (!actualBase64) {
            return { success: false, error: 'Excel files require base64 data' };
          }
          
          // Extract base64 data
          const excelBase64 = actualBase64.replace(/^data:.*?;base64,/, '');
          const excelBuffer = Buffer.from(excelBase64, 'base64');
          
          try {
            // Read the workbook
            const workbook = xlsx.read(excelBuffer, { type: 'buffer' });
            
            // Get all sheet names
            const sheetNames = workbook.SheetNames;
            parsedData = {
              sheets: {},
              sheetCount: sheetNames.length,
              sheetNames: sheetNames
            };
            
            // Convert each sheet to JSON
            sheetNames.forEach(sheetName => {
              const worksheet = workbook.Sheets[sheetName];
              const jsonData = xlsx.utils.sheet_to_json(worksheet, { 
                header: 1,  // Use array of arrays format
                defval: ''  // Default value for empty cells
              });
              parsedData.sheets[sheetName] = jsonData;
              
              // Also create a CSV representation for easy viewing
              const csvData = xlsx.utils.sheet_to_csv(worksheet);
              content += `\n\n=== Sheet: ${sheetName} ===\n${csvData}`;
            });
            
          } catch (excelError) {
            return {
              success: false,
              error: `Failed to parse Excel file: ${excelError.message}`
            };
          }
          break;

        case 'csv':
          // CSV can be provided as text or base64
          let csvContent = actualTextContent;
          
          if (!csvContent && actualBase64) {
            const csvBase64 = actualBase64.replace(/^data:.*?;base64,/, '');
            csvContent = Buffer.from(csvBase64, 'base64').toString('utf-8');
          }
          
          if (!csvContent) {
            return { success: false, error: 'CSV files require content' };
          }
          
          try {
            // Use Papa Parse for better CSV handling
            const parseResult = Papa.parse(csvContent, {
              header: true,
              dynamicTyping: true,
              skipEmptyLines: true
            });
            
            parsedData = {
              data: parseResult.data,
              fields: parseResult.meta.fields,
              rowCount: parseResult.data.length,
              errors: parseResult.errors
            };
            
            // Create a formatted text representation
            content = `CSV Data (${parsedData.rowCount} rows)\n`;
            content += `Fields: ${parsedData.fields?.join(', ') || 'No headers'}\n\n`;
            
            // Show first few rows as a preview
            const preview = parseResult.data.slice(0, 10);
            content += 'Preview (first 10 rows):\n';
            content += JSON.stringify(preview, null, 2);
            
            if (parsedData.rowCount > 10) {
              content += `\n\n... and ${parsedData.rowCount - 10} more rows`;
            }
            
          } catch (csvError) {
            return {
              success: false,
              error: `Failed to parse CSV: ${csvError.message}`
            };
          }
          break;

        case 'text':
          // Text files are provided directly as content
          if (!actualTextContent) {
            return { success: false, error: 'Text files require content' };
          }
          
          content = actualTextContent;
          parsedData = {
            lines: content.split('\n').length,
            characters: content.length,
            words: content.split(/\s+/).filter(w => w.length > 0).length
          };
          break;

        default:
          // Generic file handling
          return {
            success: false,
            error: `Unsupported file type: ${actualFileType}. Supported types: pdf, excel, csv, text`
          };
      }

      return {
        success: true,
        fileName: actualFileName,
        fileType: actualFileType,
        content: content,
        parsedData: parsedData,
        message: `Successfully parsed ${actualFileType} file: ${actualFileName}`
      };

    } catch (error) {
      console.error('File parser error:', error);
      return {
        success: false,
        error: `Failed to parse file: ${error.message}`
      };
    }
  }
});

// Export as default for easier imports
export default parseFileTool;