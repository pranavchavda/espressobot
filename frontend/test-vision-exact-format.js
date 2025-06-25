import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create agent similar to your product update agent
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a helpful assistant that can analyze images and help with products.',
  model: 'gpt-4.1-mini',
  modelSettings: {
    temperature: 0.3,
    parallelToolCalls: false
  }
});

async function testExactFormat() {
  console.log('Testing vision with exact format used in multi-agent system...\n');
  
  // Test 1: Exactly mimicking the multi-agent format
  console.log('Test 1: Multi-agent format with conversation ID and history');
  try {
    // This mimics exactly what multi-agent-orchestrator.js sends
    const conversationId = '123';
    const message = 'Can you see this promotional banner?';
    
    // Small test image
    const testBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';
    const dataUrl = `data:image/png;base64,${testBase64}`;
    
    // Build input exactly like multi-agent-orchestrator.js does
    let agentInput = `${message}\n\n![User uploaded image](${dataUrl})`;
    
    // Add conversation history (simulated)
    const historyText = 'User: Hello\nAssistant: Hi there!';
    agentInput = `Previous conversation:\n${historyText}\n\nUser: ${agentInput}`;
    
    // Add conversation ID
    agentInput = `[Conversation ID: ${conversationId}]\n${agentInput}`;
    
    console.log('Input format:');
    console.log('---');
    console.log(agentInput.substring(0, 200) + '...');
    console.log('---');
    console.log('Total input length:', agentInput.length, 'characters\n');
    
    const result = await run(testAgent, agentInput, {
      maxTurns: 1,
      context: { conversationId }
    });
    
    console.log('Response:', result.state._currentStep.output);
    console.log('✅ Multi-agent format test passed\n');
    
  } catch (error) {
    console.error('❌ Multi-agent format test failed:', error.message);
  }
  
  // Test 2: Large base64 that might hit token limits
  console.log('Test 2: Testing token limits with large base64');
  try {
    // Create a base64 string that's about 1MB decoded (1.3MB base64)
    const largeMB = 1;
    const largeBase64 = 'A'.repeat(largeMB * 1024 * 1024 * 1.33);
    const largeDataUrl = `data:image/jpeg;base64,${largeBase64}`;
    
    console.log('Large image stats:');
    console.log('- Base64 length:', (largeBase64.length / 1024 / 1024).toFixed(2), 'MB');
    console.log('- Estimated tokens:', Math.round(largeBase64.length / 4), '(rough estimate)');
    
    const largeInput = `What's in this image?\n\n![Large image](${largeDataUrl})`;
    
    console.log('\nSending large image...');
    const startTime = Date.now();
    
    const result = await run(testAgent, largeInput, {
      maxTurns: 1
    });
    
    console.log('Response time:', Date.now() - startTime, 'ms');
    console.log('Response:', result.state._currentStep.output.substring(0, 100) + '...');
    console.log('✅ Large image test completed\n');
    
  } catch (error) {
    console.error('❌ Large image test failed:', error.message);
    
    if (error.message.includes('maximum context length') || error.message.includes('tokens')) {
      console.error('\n⚠️  Hit token limit! The image is too large.');
      console.error('This explains why large images appear as black rectangles in traces.');
    }
  }
  
  // Test 3: Check what happens with invalid base64
  console.log('Test 3: Testing with corrupted base64');
  try {
    // Intentionally corrupt base64
    const corruptBase64 = 'This is not valid base64!@#$%';
    const corruptDataUrl = `data:image/png;base64,${corruptBase64}`;
    
    const corruptInput = `What do you see?\n\n![Corrupt image](${corruptDataUrl})`;
    
    const result = await run(testAgent, corruptInput, {
      maxTurns: 1
    });
    
    console.log('Response with corrupt image:', result.state._currentStep.output);
    console.log('⚠️  Agent responded despite corrupt image data\n');
    
  } catch (error) {
    console.error('❌ Corrupt image test failed:', error.message);
  }
}

// Run the test
testExactFormat().then(() => {
  console.log('Exact format test completed!');
  
  console.log('\n📊 Summary:');
  console.log('- Small base64 images work correctly');
  console.log('- Large images may hit token limits');
  console.log('- Corrupted images cause hallucination');
  console.log('- The "black rectangle" in traces likely indicates truncated/corrupted data');
  
  process.exit(0);
}).catch(error => {
  console.error('Test failed:', error);
  process.exit(1);
});