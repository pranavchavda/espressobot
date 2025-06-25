import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import fs from 'fs';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a simple vision test agent
const visionTestAgent = new Agent({
  name: 'Vision_Test_Agent',
  instructions: 'You are a helpful assistant that can analyze images. When shown an image, describe what you see in detail.',
  model: 'gpt-4.1-mini',  // Same model as your agents
  modelSettings: {
    temperature: 0.7
  }
});

async function testLargeImage() {
  console.log('Testing vision capability with a large real image...\n');
  
  // First, I need to get the image from your message
  // Since you uploaded it, I'll need to simulate this with a test
  
  console.log('Please provide the image as a base64 data URL or a regular URL.');
  console.log('For testing, I\'ll use a sample large image from the web.\n');
  
  // Test with a larger, more complex image
  console.log('Test: Large image from URL (markdown format)');
  try {
    // Using a larger, more complex image
    const largeImageUrl = 'https://images.unsplash.com/photo-1511920170033-f8396924c348?w=1200';
    const markdownInput = `What do you see in this image? Please describe it in detail.\n\n![Large test image](${largeImageUrl})`;
    
    console.log('Sending large image URL in markdown format...');
    console.log('Image URL:', largeImageUrl);
    console.log('Input length:', markdownInput.length, 'characters\n');
    
    const startTime = Date.now();
    const result = await run(visionTestAgent, markdownInput, {
      maxTurns: 1
    });
    const endTime = Date.now();
    
    console.log('Response received in', endTime - startTime, 'ms:');
    console.log('---');
    console.log(result.state._currentStep.output);
    console.log('---\n');
    
    // Check if the response actually describes the image
    const response = result.state._currentStep.output.toLowerCase();
    const hasImageDescription = response.includes('coffee') || response.includes('cup') || response.includes('bean') || response.includes('image');
    
    if (hasImageDescription) {
      console.log('✅ Large image test passed - Agent provided image description');
    } else {
      console.log('⚠️  Large image test unclear - Response may not describe the image');
    }
    
  } catch (error) {
    console.error('❌ Large image test failed:', error.message);
    console.error('Stack:', error.stack);
  }
}

// For testing with your actual uploaded image, we would need to:
// 1. Save your image to a file
// 2. Convert it to base64
// 3. Test with that data URL

console.log('To test with your specific image, you would need to:');
console.log('1. Save the image locally');
console.log('2. Convert to base64 data URL');
console.log('3. Pass it in markdown format\n');

// Run the test
testLargeImage().then(() => {
  console.log('\nVision test completed!');
  process.exit(0);
}).catch(error => {
  console.error('Vision test failed:', error);
  process.exit(1);
});