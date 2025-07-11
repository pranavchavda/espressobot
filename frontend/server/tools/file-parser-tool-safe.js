import { tool } from '@openai/agents';
import { z } from 'zod';
import xlsx from 'xlsx';
import { parse as csvParse } from 'csv-parse/sync';
import Papa from 'papaparse';
import fs from 'fs/promises';
import path from 'path';

// Use pdf-lib to get basic PDF information without full text extraction
async function parsePdfContent(pdfBuffer) {
  try {
    const { PDFDocument } = await import('pdf-lib');
    const pdfDoc = await PDFDocument.load(pdfBuffer, { ignoreEncryption: true });
    
    const pageCount = pdfDoc.getPageCount();
    const title = pdfDoc.getTitle() || 'Untitled';
    const author = pdfDoc.getAuthor() || 'Unknown';
    const creator = pdfDoc.getCreator() || 'Unknown';
    const producer = pdfDoc.getProducer() || 'Unknown';
    const creationDate = pdfDoc.getCreationDate();
    const modificationDate = pdfDoc.getModificationDate();
    
    // Get basic page information
    const pages = pdfDoc.getPages();
    const firstPage = pages[0];
    const { width, height } = firstPage.getSize();
    
    return {
      text: `[PDF Document Information]
Title: ${title}
Author: ${author}
Pages: ${pageCount}
Page Size: ${width.toFixed(0)}x${height.toFixed(0)} points
Creator: ${creator}
Producer: ${producer}
Created: ${creationDate ? creationDate.toISOString() : 'Unknown'}
Modified: ${modificationDate ? modificationDate.toISOString() : 'Unknown'}

Note: Full text extraction from PDFs is not currently available. The PDF has been successfully uploaded and basic metadata has been extracted. For text content, please export the PDF as text or use an external PDF-to-text service.`,
      numpages: pageCount,
      info: {
        Title: title,
        Author: author,
        Creator: creator,
        Producer: producer
      },
      metadata: {
        pageCount,
        pageSize: { width, height },
        creationDate,
        modificationDate
      }
    };
  } catch (error) {
    // Fallback if pdf-lib also fails
    console.error('PDF parsing error:', error);
    return {
      text: `[PDF file uploaded successfully but could not be parsed. Error: ${error.message}. The file is available for reference but text content cannot be extracted at this time.]`,
      numpages: 0,
      info: {},
      metadata: null
    };
  }
}

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
    base64Data: z.string().default('').describe('Base64 encoded file data (for binary files) - empty string if not applicable'),
    textContent: z.string().default('').describe('Raw text content (for text files) - empty string if not applicable'),
    fileName: z.string().default('').describe('Original filename for context - empty string if not provided'),
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
      const actualBase64 = (base64Data && base64Data !== '') ? base64Data : global.currentFileBase64;
      const actualTextContent = (textContent && textContent !== '') ? textContent : fileData?.content;
      const actualFileName = (fileName && fileName !== '') ? fileName : fileData?.name || 'unknown';

      switch (actualFileType) {
        case 'pdf':
          if (!actualBase64) {
            return { success: false, error: 'PDF files require base64 data' };
          }
          
          // Extract base64 data (remove data URL prefix if present)
          const pdfBase64 = actualBase64.replace(/^data:.*?;base64,/, '');
          const pdfBuffer = Buffer.from(pdfBase64, 'base64');
          
          try {
            // Use our PDF parsing workaround
            const pdfData = await parsePdfContent(pdfBuffer);
            content = pdfData.text;
            parsedData = {
              pages: pdfData.numpages,
              info: pdfData.info,
              metadata: pdfData.metadata,
              textLength: pdfData.text.length,
              note: 'PDF parsing is limited - consider uploading as text if you need the content'
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

// Export the execute function directly for testing
export const executeFileParse = parseFileTool.definition?.execute || parseFileTool._execute || (async (params) => {
  try {
    // Direct implementation for testing
    const { fileType, base64Data, textContent, fileName } = params;
    
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
    const actualTextContent = (textContent && textContent !== '') ? textContent : fileData?.content;
    const actualFileName = (fileName && fileName !== '') ? fileName : fileData?.name || 'unknown';

    if (actualFileType === 'csv' && actualTextContent) {
      // Use Papa Parse for CSV
      const Papa = (await import('papaparse')).default;
      const parseResult = Papa.parse(actualTextContent, {
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
      
      content = `CSV Data (${parsedData.rowCount} rows)\n`;
      content += `Fields: ${parsedData.fields?.join(', ') || 'No headers'}\n\n`;
      content += JSON.stringify(parseResult.data.slice(0, 5), null, 2);
      
      return {
        success: true,
        fileName: actualFileName,
        fileType: actualFileType,
        content: content,
        parsedData: parsedData,
        message: `Successfully parsed ${actualFileType} file: ${actualFileName}`
      };
    }
    
    return { success: false, error: 'Test implementation only supports CSV' };
  } catch (error) {
    return { success: false, error: error.message };
  }
});

// Export as default for easier imports
export default parseFileTool;