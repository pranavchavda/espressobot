import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Enable debug logging
process.env.DEBUG = 'openai:*';
process.env.OPENAI_AGENTS_DEBUG = 'true';

// Create a test agent
const testAgent = new Agent({
  name: 'Vision_Test_Agent',
  instructions: 'You are a helpful assistant that can analyze images. When you see an image, describe what you see.',
  model: 'gpt-4.1-mini',
  modelSettings: {
    temperature: 0.1
  }
});

async function debugSDKVision() {
  console.log('Debugging OpenAI agents SDK vision handling...\n');
  
  // Test with a valid base64 image that SHOULD work
  const redSquareBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
  
  // Test 1: Exact format the SDK expects
  console.log('Test 1: Using exact SDK format with proper base64 data URL');
  console.log('=' + '='.repeat(60));
  
  try {
    // Create the EXACT format the SDK converter expects
    const userMessage = {
      role: 'user',
      content: [
        {
          type: 'input_text',
          text: 'What color is the square in this image?'
        },
        {
          type: 'input_image',
          image: `data:image/png;base64,${redSquareBase64}` // This is a string, should work!
        }
      ]
    };
    
    console.log('Sending message:', JSON.stringify(userMessage, null, 2));
    
    // Try different ways to call run
    const result = await run(testAgent, [userMessage], {
      maxTurns: 1,
      trace: {
        workflow_name: 'Vision Debug Test'
      }
    });
    
    console.log('\nResult structure:', Object.keys(result));
    console.log('Final output:', result.finalOutput || result.state?._currentStep?.output);
    
    // Check if the response mentions red
    const response = result.finalOutput || result.state?._currentStep?.output || '';
    const sawRed = response.toLowerCase().includes('red');
    console.log(sawRed ? '✅ Correctly identified red!' : '❌ Did not identify red');
    
    // Log raw responses for debugging
    if (result.rawResponses) {
      console.log('\nRaw responses:', JSON.stringify(result.rawResponses, null, 2).substring(0, 500));
    }
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    console.error('Stack:', error.stack);
  }
  
  // Test 2: Try with providerData to pass detail level
  console.log('\n\nTest 2: With providerData for detail level');
  console.log('=' + '='.repeat(60));
  
  try {
    const userMessage = {
      role: 'user',
      content: [
        {
          type: 'input_text',
          text: 'What color is this square?'
        },
        {
          type: 'input_image',
          image: `data:image/png;base64,${redSquareBase64}`,
          providerData: {
            detail: 'high' // Try high detail mode
          }
        }
      ]
    };
    
    const result = await run(testAgent, [userMessage], { maxTurns: 1 });
    console.log('Response:', result.finalOutput || result.state?._currentStep?.output);
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
  
  // Test 3: Try URL to confirm SDK works
  console.log('\n\nTest 3: Control test with URL (should definitely work)');
  console.log('=' + '='.repeat(60));
  
  try {
    const userMessage = {
      role: 'user',
      content: [
        {
          type: 'input_text',
          text: 'What beverage is shown?'
        },
        {
          type: 'input_image',
          image: 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/A_small_cup_of_coffee.JPG/320px-A_small_cup_of_coffee.JPG'
        }
      ]
    };
    
    const result = await run(testAgent, [userMessage], { maxTurns: 1 });
    console.log('Response:', result.finalOutput || result.state?._currentStep?.output);
    console.log('✅ URL test passed');
    
  } catch (error) {
    console.error('❌ URL test failed:', error.message);
  }
}

// Run with detailed logging
debugSDKVision().then(() => {
  console.log('\n\nDebug Summary:');
  console.log('If base64 still fails, the issue is likely:');
  console.log('1. The SDK is not properly passing base64 to the API');
  console.log('2. The API endpoint used by the SDK has different behavior');
  console.log('3. There\'s a bug in the SDK\'s image handling');
  process.exit(0);
}).catch(error => {
  console.error('Debug test failed:', error);
  process.exit(1);
});