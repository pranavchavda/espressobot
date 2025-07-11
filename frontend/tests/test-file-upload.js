import fetch from 'node-fetch';
import fs from 'fs/promises';
import path from 'path';

const API_URL = 'http://localhost:5173/api/agent/run';

async function testFileUpload() {
  console.log('Testing file upload functionality...\n');

  // Test 1: CSV file upload
  console.log('Test 1: Uploading CSV file');
  const csvContent = await fs.readFile('./test-files/sample.csv', 'utf-8');
  
  const csvRequest = {
    message: 'I uploaded a CSV file with product data. Can you analyze it and tell me what products are in it?',
    file: {
      type: 'csv',
      name: 'sample.csv',
      size: Buffer.byteLength(csvContent),
      encoding: 'text',
      content: csvContent
    }
  };

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(csvRequest)
    });

    if (!response.ok) {
      console.error('CSV test failed:', response.status, response.statusText);
    } else {
      console.log('✓ CSV upload request sent successfully');
      
      // Read the SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.trim() && line.includes('data:')) {
            try {
              const data = JSON.parse(line.replace('data: ', ''));
              if (data.content) {
                console.log('Agent:', data.content.substring(0, 100) + '...');
              }
            } catch (e) {
              // Skip parsing errors
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('CSV test error:', error.message);
  }

  console.log('\n---\n');

  // Test 2: Markdown file upload
  console.log('Test 2: Uploading Markdown file');
  const mdContent = await fs.readFile('./test-files/sample.md', 'utf-8');
  
  const mdRequest = {
    message: 'I uploaded a markdown file. Can you summarize what it contains?',
    file: {
      type: 'text',
      name: 'sample.md',
      size: Buffer.byteLength(mdContent),
      encoding: 'text',
      content: mdContent
    }
  };

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(mdRequest)
    });

    if (!response.ok) {
      console.error('Markdown test failed:', response.status, response.statusText);
    } else {
      console.log('✓ Markdown upload request sent successfully');
    }
  } catch (error) {
    console.error('Markdown test error:', error.message);
  }

  console.log('\n---\n');

  // Test 3: Test file parser tool directly
  console.log('Test 3: Testing file parser tool');
  const { parseFileTool } = await import('../server/tools/file-parser-tool-safe.js');
  
  // The tool object has an _execute property, not execute
  const parseResult = await parseFileTool._execute({
    fileType: 'csv',
    textContent: csvContent,
    fileName: 'test.csv'
  });
  
  console.log('Parse result:', JSON.stringify(parseResult, null, 2));
  
  // Test 4: Test markdown parsing
  console.log('\nTest 4: Testing markdown parser');
  const mdParseResult = await parseFileTool._execute({
    fileType: 'text',
    textContent: mdContent,
    fileName: 'test.md'
  });
  
  console.log('Markdown parse result:', {
    success: mdParseResult.success,
    fileName: mdParseResult.fileName,
    stats: mdParseResult.parsedData,
    contentPreview: mdParseResult.content.substring(0, 100) + '...'
  });
}

// Run the test
testFileUpload().catch(console.error);