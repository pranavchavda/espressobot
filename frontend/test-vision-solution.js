import { Agent } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import { runWithVisionRetry } from './server/vision-retry-wrapper.js';
import { validateAndFixBase64 } from './server/vision-preprocessor.js';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Test image - red square
const redSquareBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';

async function testVisionSolution() {
  console.log('Testing complete vision solution with retry and validation...\n');
  
  const testAgent = new Agent({
    name: 'Vision_Test_Agent',
    instructions: 'You are a helpful assistant that can analyze images.',
    model: 'gpt-4.1-mini',
    modelSettings: {
      temperature: 0.1
    }
  });
  
  // Test 1: Basic data URL
  console.log('Test 1: Testing with basic base64 (no data URL prefix)');
  console.log('=' + '='.repeat(60));
  
  const validated1 = validateAndFixBase64(redSquareBase64);
  console.log('Validated:', validated1.substring(0, 50) + '...');
  
  // Test 2: Proper data URL
  console.log('\n\nTest 2: Testing with proper data URL');
  console.log('=' + '='.repeat(60));
  
  const dataUrl = `data:image/png;base64,${redSquareBase64}`;
  const validated2 = validateAndFixBase64(dataUrl);
  console.log('Validated:', validated2.substring(0, 50) + '...');
  
  // Test 3: Multiple runs with retry wrapper
  console.log('\n\nTest 3: Testing retry wrapper (10 runs)');
  console.log('=' + '='.repeat(60));
  
  const results = [];
  for (let i = 0; i < 10; i++) {
    try {
      const result = await runWithVisionRetry(testAgent, [{
        role: 'user',
        content: [
          {
            type: 'input_text',
            text: 'What color is this square? Just say the color name.'
          },
          {
            type: 'input_image',
            image: validated2
          }
        ]
      }], { maxTurns: 1 }, 3); // 3 retries max
      
      const response = result.finalOutput || result.state?._currentStep?.output || '';
      const sawRed = response.toLowerCase().includes('red');
      results.push({ attempt: i + 1, success: sawRed, response });
      console.log(`Attempt ${i + 1}: ${sawRed ? '✅' : '❌'} - ${response}`);
      
      // Small delay between tests
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (error) {
      results.push({ attempt: i + 1, success: false, error: error.message });
      console.log(`Attempt ${i + 1}: ❌ - Error: ${error.message}`);
    }
  }
  
  // Summary
  console.log('\n\nSummary:');
  console.log('=' + '='.repeat(60));
  const successCount = results.filter(r => r.success).length;
  console.log(`Success rate: ${successCount}/10 (${successCount * 10}%)`);
  console.log('With retry wrapper, we should see near 100% success rate');
  
  // Analyze failure patterns
  const failures = results.filter(r => !r.success);
  if (failures.length > 0) {
    console.log('\nFailures:');
    failures.forEach(f => {
      console.log(`- Attempt ${f.attempt}: ${f.error || f.response}`);
    });
  }
}

testVisionSolution().catch(console.error);