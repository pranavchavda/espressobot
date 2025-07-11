// Simple test for the file parser tool

async function testParser() {
  console.log('Testing file parser tool...\n');
  
  // Import the execute function from the file parser
  const { executeFileParse } = await import('../server/tools/file-parser-tool-safe.js');
  
  // Test CSV parsing
  const csvContent = `Product,Price,Quantity
Coffee Maker,299.99,10
Grinder,199.99,15
Espresso Machine,599.99,5`;
  
  console.log('Testing CSV parsing...');
  const result = await executeFileParse({
    fileType: 'csv',
    textContent: csvContent,
    fileName: 'test.csv'
  });
  
  console.log('CSV Parse result:', JSON.stringify(result, null, 2));
  
  // Test with actual file content
  const fs = await import('fs/promises');
  const actualCsv = await fs.readFile('./test-files/sample.csv', 'utf-8');
  
  console.log('\nTesting with actual CSV file...');
  const actualResult = await executeFileParse({
    fileType: 'csv',
    textContent: actualCsv,
    fileName: 'sample.csv'
  });
  
  console.log('Actual file parse result:', JSON.stringify(actualResult, null, 2));
}

testParser().catch(console.error);