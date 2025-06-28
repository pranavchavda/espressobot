import OpenAI from 'openai';
import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
const apiKey = process.env.OPENAI_API_KEY;
setDefaultOpenAIKey(apiKey);

// Create OpenAI client for direct API calls
const openai = new OpenAI({ apiKey });

// Test image
const redSquareBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
const dataUrl = `data:image/png;base64,${redSquareBase64}`;

async function testDirectAPI() {
  console.log('Test 1: Direct OpenAI Chat Completions API with base64');
  console.log('=' + '='.repeat(60));
  
  try {
    const response = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'text',
              text: 'What color is this square?'
            },
            {
              type: 'image_url',
              image_url: {
                url: dataUrl
              }
            }
          ]
        }
      ],
      max_tokens: 100
    });
    
    console.log('Response:', response.choices[0].message.content);
    const sawRed = response.choices[0].message.content.toLowerCase().includes('red');
    console.log(sawRed ? '✅ API correctly identified RED!' : '❌ API failed to identify red');
    
  } catch (error) {
    console.error('API Error:', error.message);
  }
}

async function testSDK() {
  console.log('\n\nTest 2: OpenAI Agents SDK with same base64');
  console.log('=' + '='.repeat(60));
  
  const testAgent = new Agent({
    name: 'Vision_Test_Agent',
    instructions: 'You are a helpful assistant.',
    model: 'gpt-4o-mini', // Use same model as API test
    modelSettings: {
      temperature: 0.1
    }
  });
  
  try {
    const result = await run(testAgent, [{
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
    }], { maxTurns: 1 });
    
    const response = result.finalOutput || result.state?._currentStep?.output;
    console.log('Response:', response);
    const sawRed = response.toLowerCase().includes('red');
    console.log(sawRed ? '✅ SDK correctly identified RED!' : '❌ SDK failed to identify red');
    
  } catch (error) {
    console.error('SDK Error:', error.message);
  }
}

// Run both tests
async function runComparison() {
  await testDirectAPI();
  await testSDK();
  
  console.log('\n\nConclusion:');
  console.log('If the direct API works but the SDK doesn\'t, there\'s a bug in the SDK.');
  console.log('If both fail, the issue might be with the base64 encoding itself.');
}

runComparison().catch(console.error);