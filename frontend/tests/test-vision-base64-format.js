import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

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

async function testBase64Formats() {
  console.log('Testing different base64 formats with OpenAI agents SDK...\n');
  
  // Real 10x10 red square PNG
  const redSquareBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
  
  // Test 1: With data URL prefix
  console.log('Test 1: Base64 with data URL prefix');
  console.log('=' + '='.repeat(40));
  try {
    const dataUrl = `data:image/png;base64,${redSquareBase64}`;
    
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
    
    const result = await run(testAgent, agentInput, { maxTurns: 1 });
    console.log('Response:', result.state._currentStep.output);
    
  } catch (error) {
    console.error('❌ Failed:', error.message);
  }
  
  // Test 2: Just base64 without prefix
  console.log('\n\nTest 2: Just base64 string (no data URL prefix)');
  console.log('=' + '='.repeat(40));
  try {
    const agentInput = [{
      role: 'user',
      content: [
        {
          type: 'input_text',
          text: 'What color is this square?'
        },
        {
          type: 'input_image',
          image: redSquareBase64
        }
      ]
    }];
    
    const result = await run(testAgent, agentInput, { maxTurns: 1 });
    console.log('Response:', result.state._currentStep.output);
    
  } catch (error) {
    console.error('❌ Failed:', error.message);
  }
  
  // Test 3: With different MIME type
  console.log('\n\nTest 3: Different MIME type (jpeg)');
  console.log('=' + '='.repeat(40));
  try {
    const dataUrl = `data:image/jpeg;base64,${redSquareBase64}`;
    
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
    
    const result = await run(testAgent, agentInput, { maxTurns: 1 });
    console.log('Response:', result.state._currentStep.output);
    
  } catch (error) {
    console.error('❌ Failed:', error.message);
  }
  
  // Test 4: Check what format the SDK documentation suggests
  console.log('\n\nTest 4: Testing with a known working URL first');
  console.log('=' + '='.repeat(40));
  try {
    const agentInput = [{
      role: 'user',
      content: [
        {
          type: 'input_text',
          text: 'What beverage is this?'
        },
        {
          type: 'input_image',
          image: 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/A_small_cup_of_coffee.JPG/320px-A_small_cup_of_coffee.JPG'
        }
      ]
    }];
    
    const result = await run(testAgent, agentInput, { maxTurns: 1 });
    console.log('✅ URL works:', result.state._currentStep.output);
    
  } catch (error) {
    console.error('❌ Failed:', error.message);
  }
}

// Run the test
testBase64Formats().then(() => {
  console.log('\n\nBased on these tests, we can determine the correct base64 format.');
  process.exit(0);
}).catch(error => {
  console.error('Test suite failed:', error);
  process.exit(1);
});