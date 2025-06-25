import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a test agent matching our setup
const testAgent = new Agent({
  name: 'Vision_Test_Agent',
  instructions: 'You are a helpful assistant that can analyze images. When shown an image, describe what you see in detail.',
  model: 'gpt-4.1-mini',
  modelSettings: {
    temperature: 0.3,
    parallelToolCalls: false
  }
});

async function testCorrectFormat() {
  console.log('Testing vision with CORRECT OpenAI agents SDK format...\n');
  
  // Test 1: Simple image with correct format
  console.log('Test 1: Real red square with correct format');
  console.log('=' + '='.repeat(50));
  
  try {
    // Real 10x10 red square PNG
    const redSquare = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
    const dataUrl = `data:image/png;base64,${redSquare}`;
    
    // Use correct format with content array
    const agentInput = [{
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
    }];
    
    console.log('Sending multimodal input with content array...');
    const result = await run(testAgent, agentInput, { maxTurns: 1 });
    
    console.log('Response:', result.state._currentStep.output);
    
    const sawRed = result.state._currentStep.output.toLowerCase().includes('red');
    console.log(sawRed ? '✅ Correctly identified RED color' : '❌ Failed to identify red color');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
  
  // Test 2: With conversation context (like our orchestrator)
  console.log('\n\nTest 2: Image with conversation context');
  console.log('=' + '='.repeat(50));
  
  try {
    const blueSquare = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAH0lEQVR42mNgYPj/n4GBgZGBgWEUjiqcylCHX85oGgAokQMtkuX9qgAAAABJRU5ErkJggg==';
    const dataUrl = `data:image/png;base64,${blueSquare}`;
    
    // Build like our orchestrator
    const agentInput = [{
      role: 'user',
      content: [
        {
          type: 'input_text',
          text: '[Conversation ID: 123]\nPrevious conversation:\nUser: I want to test colors\nAssistant: Sure, show me an image.\n\nUser: What color is this square?'
        },
        {
          type: 'input_image',
          image: dataUrl
        }
      ]
    }];
    
    const result = await run(testAgent, agentInput, { 
      maxTurns: 1,
      context: { conversationId: '123' }
    });
    
    console.log('Response:', result.state._currentStep.output);
    
    const sawBlue = result.state._currentStep.output.toLowerCase().includes('blue');
    console.log(sawBlue ? '✅ Correctly identified BLUE color with context' : '❌ Failed to identify blue color');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
  
  // Test 3: URL image
  console.log('\n\nTest 3: URL image with correct format');
  console.log('=' + '='.repeat(50));
  
  try {
    const agentInput = [{
      role: 'user',
      content: [
        {
          type: 'input_text',
          text: 'What type of beverage is shown in this image?'
        },
        {
          type: 'input_image',
          image: 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/A_small_cup_of_coffee.JPG/640px-A_small_cup_of_coffee.JPG'
        }
      ]
    }];
    
    const result = await run(testAgent, agentInput, { maxTurns: 1 });
    
    console.log('Response:', result.state._currentStep.output);
    
    const sawCoffee = result.state._currentStep.output.toLowerCase().includes('coffee');
    console.log(sawCoffee ? '✅ Correctly identified coffee' : '❌ Failed to identify coffee');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
  
  // Test 4: Larger base64 image
  console.log('\n\nTest 4: Larger image (200KB base64)');
  console.log('=' + '='.repeat(50));
  
  try {
    // Create a 200KB base64 string
    const largeImage = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC' + 'A'.repeat(200 * 1024 - 104);
    const dataUrl = `data:image/png;base64,${largeImage}`;
    
    const agentInput = [{
      role: 'user',
      content: [
        {
          type: 'input_text',
          text: 'Can you see this larger image?'
        },
        {
          type: 'input_image',
          image: dataUrl
        }
      ]
    }];
    
    console.log('Sending 200KB base64 image...');
    const startTime = Date.now();
    
    const result = await run(testAgent, agentInput, { maxTurns: 1 });
    
    console.log('Response time:', Date.now() - startTime, 'ms');
    console.log('Response:', result.state._currentStep.output.substring(0, 100) + '...');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

// Run the test
testCorrectFormat().then(() => {
  console.log('\n\nConclusions:');
  console.log('If these tests work, then the correct format is the content array with input_text and input_image.');
  console.log('The markdown format was never correct for the OpenAI agents SDK.');
  process.exit(0);
}).catch(error => {
  console.error('Test suite failed:', error);
  process.exit(1);
});