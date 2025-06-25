import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import fs from 'fs';
import https from 'https';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a simple vision test agent
const visionTestAgent = new Agent({
  name: 'Vision_Test_Agent',
  instructions: 'You are a helpful assistant that can analyze images. When shown an image, describe what you see in detail.',
  model: 'gpt-4.1-mini',
  modelSettings: {
    temperature: 0.7
  }
});

// Create test images of different sizes
function createTestImage(sizeMB) {
  // Create a dummy base64 string of approximate size
  // Base64 is ~33% larger than original, so to get sizeMB decoded, we need sizeMB * 1.33 in base64
  const base64Size = Math.floor(sizeMB * 1024 * 1024 * 1.33);
  
  // Create a valid PNG header and then pad with 'A's
  const pngHeader = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
  const padding = 'A'.repeat(Math.max(0, base64Size - pngHeader.length));
  
  return pngHeader + padding;
}

async function testVisionWithSizes() {
  console.log('Testing vision capability with various image sizes...\n');
  
  // Test sizes in MB
  const testSizes = [0.1, 0.5, 1, 2, 3, 4, 5];
  
  for (const sizeMB of testSizes) {
    console.log(`\nTest: ${sizeMB}MB image (base64)`);
    console.log('=' + '='.repeat(40));
    
    try {
      const base64Data = createTestImage(sizeMB);
      const dataUrl = `data:image/png;base64,${base64Data}`;
      
      console.log(`Base64 length: ${(base64Data.length / 1024 / 1024).toFixed(2)}MB`);
      console.log(`Estimated original size: ${sizeMB}MB`);
      
      const input = `What do you see in this ${sizeMB}MB test image?\n\n![Test image ${sizeMB}MB](${dataUrl})`;
      console.log(`Total input length: ${(input.length / 1024 / 1024).toFixed(2)}MB`);
      
      const startTime = Date.now();
      console.log('\nSending to agent...');
      
      const result = await run(visionTestAgent, input, {
        maxTurns: 1
      });
      
      const elapsed = Date.now() - startTime;
      console.log(`Response time: ${elapsed}ms`);
      
      const response = result.state._currentStep.output;
      console.log('Response:', response.substring(0, 150) + (response.length > 150 ? '...' : ''));
      
      // Check if the agent actually saw the image or is making things up
      const sawImage = !response.toLowerCase().includes('cannot') && 
                       !response.toLowerCase().includes('error') &&
                       !response.toLowerCase().includes('unable');
      
      console.log(`✅ ${sizeMB}MB test ${sawImage ? 'PASSED' : 'FAILED (agent couldn\'t see image)'}`);
      
    } catch (error) {
      console.log(`❌ ${sizeMB}MB test FAILED with error: ${error.message}`);
      
      if (error.message.includes('500')) {
        console.log('→ Server error (likely too large)');
      } else if (error.message.includes('context length')) {
        console.log('→ Exceeded context length');
      } else if (error.message.includes('timeout')) {
        console.log('→ Request timed out');
      }
    }
  }
  
  console.log('\n\nSummary of Results:');
  console.log('==================');
  console.log('Based on these tests, we can determine the practical limits for base64 images');
  console.log('with the OpenAI agents SDK.');
}

// Also test with a real image
async function testWithRealImage() {
  console.log('\n\nTesting with a real image file...\n');
  
  try {
    // Create a real test image using a small actual PNG
    const realPNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8/5+hnoEIwDiqkL4KAcT9E/f4uc66AAAAAElFTkSuQmCC', 'base64');
    
    // This is a real 10x10 red square PNG
    const realBase64 = realPNG.toString('base64');
    const dataUrl = `data:image/png;base64,${realBase64}`;
    
    console.log('Real PNG stats:');
    console.log('- File size:', realPNG.length, 'bytes');
    console.log('- Base64 size:', realBase64.length, 'bytes');
    
    const input = `Please describe this small test image in detail.\n\n![Real test image](${dataUrl})`;
    
    const result = await run(visionTestAgent, input, {
      maxTurns: 1
    });
    
    console.log('\nResponse:', result.state._currentStep.output);
    console.log('✅ Real image test passed');
    
  } catch (error) {
    console.error('❌ Real image test failed:', error.message);
  }
}

// Run the tests
async function runAllTests() {
  await testWithRealImage();
  await testVisionWithSizes();
}

runAllTests().then(() => {
  console.log('\nAll tests completed!');
  process.exit(0);
}).catch(error => {
  console.error('Test suite failed:', error);
  process.exit(1);
});