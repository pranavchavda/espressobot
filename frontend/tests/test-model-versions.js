import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Test image
const redSquareBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
const dataUrl = `data:image/png;base64,${redSquareBase64}`;

async function testModel(modelName) {
  console.log(`\nTesting model: ${modelName}`);
  console.log('=' + '='.repeat(40));
  
  const agent = new Agent({
    name: 'Vision_Test_Agent',
    instructions: 'You are a helpful assistant that can analyze images.',
    model: modelName,
    modelSettings: {
      temperature: 0.1
    }
  });
  
  try {
    const result = await run(agent, [{
      role: 'user',
      content: [
        {
          type: 'input_text',
          text: 'What color is this square? Just say the color name.'
        },
        {
          type: 'input_image',
          image: dataUrl
        }
      ]
    }], { maxTurns: 1 });
    
    const response = result.finalOutput || result.state?._currentStep?.output || '';
    console.log('Response:', response);
    
    const sawRed = response.toLowerCase().includes('red');
    console.log(sawRed ? '✅ Correctly saw RED' : `❌ Failed - saw: ${response}`);
    
    return { model: modelName, success: sawRed, response };
    
  } catch (error) {
    console.error(`❌ Error: ${error.message}`);
    return { model: modelName, success: false, error: error.message };
  }
}

async function testAllModels() {
  console.log('Testing base64 vision across different models...');
  
  const models = [
    'gpt-4o-mini',      // Latest mini model with vision
    'gpt-4o',           // Full model
    'gpt-4.1-mini',     // The model you're using
    'gpt-4-turbo',      // Turbo model
  ];
  
  const results = [];
  
  for (const model of models) {
    const result = await testModel(model);
    results.push(result);
    
    // Small delay between tests
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  console.log('\n\nSummary:');
  console.log('========');
  results.forEach(r => {
    if (r.success) {
      console.log(`✅ ${r.model} - Works correctly`);
    } else if (r.error) {
      console.log(`❌ ${r.model} - Error: ${r.error}`);
    } else {
      console.log(`❌ ${r.model} - Saw: ${r.response}`);
    }
  });
  
  // Test multiple times with same model to check consistency
  console.log('\n\nConsistency test with gpt-4.1-mini (5 runs):');
  console.log('=' + '='.repeat(40));
  
  const consistencyResults = [];
  for (let i = 0; i < 5; i++) {
    const result = await testModel('gpt-4.1-mini');
    consistencyResults.push(result.response);
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  
  console.log('Results:', consistencyResults);
  const uniqueResponses = [...new Set(consistencyResults)];
  console.log(`Consistency: ${uniqueResponses.length === 1 ? '✅ Consistent' : '❌ Inconsistent'}`);
  console.log('Unique responses:', uniqueResponses);
}

testAllModels().catch(console.error);