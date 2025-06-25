import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a test agent
const testAgent = new Agent({
  name: 'Vision_Test_Agent',
  instructions: 'You are a helpful assistant that can analyze images. When shown an image, describe what you see in detail.',
  model: 'gpt-4.1-mini',
  modelSettings: {
    temperature: 0.3,
    parallelToolCalls: false
  }
});

async function testRealImages() {
  console.log('Testing with REAL images to verify vision actually works...\n');
  
  // Test 1: Small real PNG (red square)
  console.log('Test 1: Real 10x10 red square PNG');
  console.log('=' + '='.repeat(40));
  
  try {
    // This is a real 10x10 red square PNG
    const realRedSquare = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
    const dataUrl = `data:image/png;base64,${realRedSquare}`;
    
    console.log('Image size:', realRedSquare.length, 'bytes');
    
    const input = `Please describe exactly what you see in this image. If you cannot see the image, say so.\n\n![Red square](${dataUrl})`;
    
    const result = await run(testAgent, input, { maxTurns: 1 });
    console.log('Response:', result.state._currentStep.output);
    
    const sawRed = result.state._currentStep.output.toLowerCase().includes('red');
    console.log(sawRed ? '✅ Correctly saw red color' : '❌ Did not identify red color');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
  
  // Test 2: Another real small image (blue dot)
  console.log('\n\nTest 2: Real blue dot PNG');
  console.log('=' + '='.repeat(40));
  
  try {
    // This is a real blue dot
    const blueDot = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAH0lEQVR42mNgYPj/n4GBgZGBgWEUjiqcylCHX85oGgAokQMtkuX9qgAAAABJRU5ErkJggg==';
    const dataUrl = `data:image/png;base64,${blueDot}`;
    
    const input = `What color is the main element in this image?\n\n![Blue dot](${dataUrl})`;
    
    const result = await run(testAgent, input, { maxTurns: 1 });
    console.log('Response:', result.state._currentStep.output);
    
    const sawBlue = result.state._currentStep.output.toLowerCase().includes('blue');
    console.log(sawBlue ? '✅ Correctly saw blue color' : '❌ Did not identify blue color');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
  
  // Test 3: Corrupt/invalid base64 that looks valid
  console.log('\n\nTest 3: Invalid image data (should admit it can\'t see)');
  console.log('=' + '='.repeat(40));
  
  try {
    // Start with valid header but corrupt the rest
    const corruptImage = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAA' + 'A'.repeat(100);
    const dataUrl = `data:image/png;base64,${corruptImage}`;
    
    const input = `What do you see in this image? Be honest if you cannot see it.\n\n![Corrupt image](${dataUrl})`;
    
    const result = await run(testAgent, input, { maxTurns: 1 });
    console.log('Response:', result.state._currentStep.output);
    
    const admittedProblem = result.state._currentStep.output.toLowerCase().includes('cannot') || 
                           result.state._currentStep.output.toLowerCase().includes('unable') ||
                           result.state._currentStep.output.toLowerCase().includes('error');
    console.log(admittedProblem ? '✅ Correctly identified problem' : '❌ Hallucinated instead of admitting problem');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
  
  // Test 4: Test with conversation context like our orchestrator
  console.log('\n\nTest 4: Real image with conversation context');
  console.log('=' + '='.repeat(40));
  
  try {
    const realRedSquare = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
    const dataUrl = `data:image/png;base64,${realRedSquare}`;
    
    // Build input like our orchestrator
    let agentInput = `What color is this square?\n\n![User uploaded image](${dataUrl})`;
    
    // Add conversation history
    const historyText = 'User: I want to test image uploads\nAssistant: Sure, I can help you test image uploads. Please share an image.';
    agentInput = `Previous conversation:\n${historyText}\n\nUser: ${agentInput}`;
    
    // Add conversation ID
    agentInput = `[Conversation ID: 123]\n${agentInput}`;
    
    console.log('Input preview:', agentInput.substring(0, 100) + '...');
    
    const result = await run(testAgent, agentInput, { 
      maxTurns: 1,
      context: { conversationId: '123' }
    });
    
    console.log('Response:', result.state._currentStep.output);
    
    const sawRed = result.state._currentStep.output.toLowerCase().includes('red');
    console.log(sawRed ? '✅ Correctly saw red square with context' : '❌ Failed to see red with context');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
  }
}

// Run the test
testRealImages().then(() => {
  console.log('\n\nConclusions:');
  console.log('If the agent correctly identifies colors in real images but hallucinates');
  console.log('with corrupt data, then vision IS working - the issue is with image validity.');
  process.exit(0);
}).catch(error => {
  console.error('Test suite failed:', error);
  process.exit(1);
});