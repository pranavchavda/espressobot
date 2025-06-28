import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

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

async function testVision() {
  console.log('Testing vision capability with OpenAI agents SDK...\n');
  
  // Test 1: Simple text message
  console.log('Test 1: Text-only message');
  try {
    const textResult = await run(visionTestAgent, 'Hello, can you see images?', {
      maxTurns: 1
    });
    console.log('Response:', textResult.state._currentStep.output);
    console.log('✅ Text test passed\n');
  } catch (error) {
    console.error('❌ Text test failed:', error.message);
  }
  
  // Test 2: Message with image (markdown format)
  console.log('Test 2: Markdown format with test image');
  try {
    // Create a small test image as base64
    const testImageBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==';
    const dataUrl = `data:image/png;base64,${testImageBase64}`;
    
    // Test with markdown format
    const markdownInput = `What do you see in this image?\n\n![test image](${dataUrl})`;
    
    console.log('Sending markdown format input...');
    const imageResult = await run(visionTestAgent, markdownInput, {
      maxTurns: 1
    });
    
    console.log('Response:', imageResult.state._currentStep.output);
    console.log('✅ Markdown image test passed\n');
  } catch (error) {
    console.error('❌ Markdown image test failed:', error.message);
    console.error('Stack:', error.stack);
  }
  
  // Test 3: Test with a URL image (markdown format)
  console.log('Test 3: URL image test (markdown format)');
  try {
    const urlInput = `What is in this image?\n\n![coffee image](https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/A_small_cup_of_coffee.JPG/640px-A_small_cup_of_coffee.JPG)`;
    
    console.log('Sending URL image in markdown...');
    const urlResult = await run(visionTestAgent, urlInput, {
      maxTurns: 1
    });
    
    console.log('Response:', urlResult.state._currentStep.output);
    console.log('✅ URL image test passed\n');
  } catch (error) {
    console.error('❌ URL image test failed:', error.message);
  }
  
  // Test 4: Let's also test the actual multimodal format that might work
  console.log('Test 4: Testing different multimodal formats');
  try {
    // Try direct object format
    const objectFormat = {
      role: 'user',
      content: [
        { type: 'text', text: 'What do you see?' },
        { type: 'image_url', image_url: { url: 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/A_small_cup_of_coffee.JPG/640px-A_small_cup_of_coffee.JPG' } }
      ]
    };
    
    console.log('Trying object format...');
    const objResult = await run(visionTestAgent, objectFormat, { maxTurns: 1 });
    console.log('Response:', objResult.state._currentStep.output);
    console.log('✅ Object format test passed\n');
  } catch (error) {
    console.error('❌ Object format test failed:', error.message);
  }
}

// Run the test
testVision().then(() => {
  console.log('Vision test completed!');
  process.exit(0);
}).catch(error => {
  console.error('Vision test failed:', error);
  process.exit(1);
});