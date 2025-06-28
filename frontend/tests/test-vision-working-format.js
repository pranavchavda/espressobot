import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import fs from 'fs';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a test agent
const testAgent = new Agent({
  name: 'Vision_Test_Agent',
  instructions: 'You are a helpful assistant that can analyze images.',
  model: 'gpt-4.1-mini',
  modelSettings: {
    temperature: 0.3
  }
});

async function testWorkingFormat() {
  console.log('Testing vision with the CORRECT format from OpenAI agents SDK docs...\n');
  
  // Test 1: Remote image URL (from the docs examples)
  console.log('Test 1: Remote image URL (should definitely work)');
  console.log('=' + '='.repeat(50));
  
  try {
    // According to the docs, this is how to send images
    const result = await run(testAgent, [
      {
        role: 'user',
        content: [
          {
            type: 'input_text',
            text: 'What type of coffee equipment is shown in this image?'
          },
          {
            type: 'input_image',
            image: 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800&q=80' // Coffee image
          }
        ]
      }
    ]);
    
    console.log('Response:', result.finalOutput);
    console.log('✅ Remote URL works!\n');
    
  } catch (error) {
    console.error('❌ Failed:', error.message);
  }
  
  // Test 2: Local image as base64 (like in local-image.ts example)
  console.log('Test 2: Local image file converted to base64');
  console.log('=' + '='.repeat(50));
  
  try {
    // Create a small test image file
    const testImageBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
    const testImagePath = '/tmp/test-red-square.png';
    
    // Write the image to disk
    fs.writeFileSync(testImagePath, Buffer.from(testImageBase64, 'base64'));
    
    // Read it back and convert to base64 data URL
    const imageBuffer = fs.readFileSync(testImagePath);
    const base64String = imageBuffer.toString('base64');
    const dataUrl = `data:image/png;base64,${base64String}`;
    
    console.log('Image size:', imageBuffer.length, 'bytes');
    console.log('Data URL length:', dataUrl.length, 'chars');
    
    const result = await run(testAgent, [
      {
        role: 'user',
        content: [
          {
            type: 'input_text',
            text: 'What color is this square?'
          },
          {
            type: 'input_image',
            image: dataUrl
          }
        ]
      }
    ]);
    
    console.log('Response:', result.finalOutput);
    
    const sawRed = result.finalOutput.toLowerCase().includes('red');
    console.log(sawRed ? '✅ Correctly saw RED!' : '❌ Did not see red color');
    
    // Clean up
    fs.unlinkSync(testImagePath);
    
  } catch (error) {
    console.error('❌ Failed:', error.message);
  }
  
  // Test 3: Try without the array wrapper (simpler format)
  console.log('\n\nTest 3: Simplified format (just content array)');
  console.log('=' + '='.repeat(50));
  
  try {
    const redSquareBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
    const dataUrl = `data:image/png;base64,${redSquareBase64}`;
    
    // Try passing content array directly
    const result = await run(testAgent, [
      {
        type: 'input_text',
        text: 'What color is this square? Please answer with just the color name.'
      },
      {
        type: 'input_image',
        image: dataUrl
      }
    ]);
    
    console.log('Response:', result.finalOutput);
    
  } catch (error) {
    console.error('❌ Failed:', error.message);
    console.log('Note: This format might not be supported');
  }
  
  // Test 4: Check if the issue is with conversation context
  console.log('\n\nTest 4: With minimal context (no conversation history)');
  console.log('=' + '='.repeat(50));
  
  try {
    const redSquareBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
    const dataUrl = `data:image/png;base64,${redSquareBase64}`;
    
    // Minimal input - just text and image
    const result = await run(testAgent, [
      {
        role: 'user',
        content: [
          {
            type: 'input_text',
            text: 'Color?'
          },
          {
            type: 'input_image',
            image: dataUrl
          }
        ]
      }
    ]);
    
    console.log('Response:', result.finalOutput);
    
  } catch (error) {
    console.error('❌ Failed:', error.message);
  }
}

// Run the test
testWorkingFormat().then(() => {
  console.log('\n\nConclusions:');
  console.log('1. Remote URLs should work perfectly');
  console.log('2. Base64 data URLs might have issues in the SDK');
  console.log('3. The format must match the SDK documentation exactly');
  process.exit(0);
}).catch(error => {
  console.error('Test suite failed:', error);
  process.exit(1);
});