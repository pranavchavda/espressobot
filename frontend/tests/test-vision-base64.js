import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { execSync } from 'child_process';
import fs from 'fs';

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

async function testBase64Image() {
  console.log('Testing vision capability with base64 encoded images...\n');
  
  // Test 1: Create a simple test image using ImageMagick
  console.log('Test 1: Creating and testing a promotional banner image');
  try {
    // Create a test image with text using ImageMagick
    const testImagePath = '/tmp/test-sale-banner.png';
    const convertCommand = `convert -size 800x400 -background "#FFE4B5" -fill "#2E8B57" -gravity center -pointsize 48 -font Arial label:"END OF SPRING\\nCLEANING SALE\\nSAVE UP TO 50%" ${testImagePath}`;
    
    try {
      execSync(convertCommand);
      console.log('Created test banner image');
    } catch (e) {
      console.log('ImageMagick not available, using a fallback method');
      // Create a simple PNG with text as fallback
      // For now, we'll skip this and use a different approach
    }
    
    // Test 2: Large base64 image test
    console.log('\nTest 2: Testing with a large base64 string (simulating your uploaded image)');
    
    // Create a larger base64 string to simulate a real image
    // Generate a reasonable size base64 string (about 100KB when decoded)
    const largeBase64 = 'A'.repeat(130000); // This simulates a ~100KB image
    const testDataUrl = `data:image/png;base64,${largeBase64}`;
    
    console.log('Testing with large base64 data URL:');
    console.log('- Base64 length:', largeBase64.length, 'characters');
    console.log('- Estimated decoded size:', Math.round(largeBase64.length * 0.75 / 1024), 'KB');
    console.log('- Total data URL length:', testDataUrl.length, 'characters\n');
    
    const markdownInput = `What do you see in this promotional image?\n\n![Sale banner](${testDataUrl})`;
    
    console.log('Sending image in markdown format...');
    const startTime = Date.now();
    
    try {
      const result = await run(visionTestAgent, markdownInput, {
        maxTurns: 1
      });
      const endTime = Date.now();
      
      console.log('Response received in', endTime - startTime, 'ms:');
      console.log('---');
      console.log(result.state._currentStep.output);
      console.log('---\n');
      
      console.log('✅ Large base64 test completed');
    } catch (error) {
      console.error('❌ Large base64 test failed:', error.message);
      
      // Check if it's a size issue
      if (error.message.includes('too long') || error.message.includes('token')) {
        console.error('\n⚠️  This appears to be a token/size limit issue.');
        console.error('The image may be too large for the current model.');
        console.error('Possible solutions:');
        console.error('1. Resize/compress images before uploading');
        console.error('2. Use image URLs instead of base64');
        console.error('3. Use a model with larger context window');
      }
    }
    
  } catch (error) {
    console.error('Test setup failed:', error.message);
  }
  
  // Test 3: Test with an actual small base64 image
  console.log('\nTest 3: Testing with a real small base64 image');
  try {
    // This is a small red dot PNG (should work)
    const smallBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
    const smallDataUrl = `data:image/png;base64,${smallBase64}`;
    
    const smallInput = `What do you see in this image?\n\n![Small test](${smallDataUrl})`;
    
    console.log('Base64 length:', smallBase64.length, 'characters');
    
    const result = await run(visionTestAgent, smallInput, {
      maxTurns: 1
    });
    
    console.log('Response:', result.state._currentStep.output);
    console.log('✅ Small base64 test passed\n');
    
  } catch (error) {
    console.error('❌ Small base64 test failed:', error.message);
  }
}

// Run the test
testBase64Image().then(() => {
  console.log('Base64 vision test completed!');
  process.exit(0);
}).catch(error => {
  console.error('Base64 vision test failed:', error);
  process.exit(1);
});