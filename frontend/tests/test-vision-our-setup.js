import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a test agent that matches our setup
const testAgent = new Agent({
  name: 'Test_Agent',
  instructions: 'You are a helpful assistant that can analyze images.',
  model: 'gpt-4.1-mini',
  modelSettings: {
    temperature: 0.3,
    parallelToolCalls: false
  }
});

// Test with increasingly large images
async function testWithIncreasingSize() {
  console.log('Testing with our exact setup...\n');
  
  // Sizes to test (in KB)
  const sizes = [50, 100, 200, 300, 400, 500, 1000, 2000];
  
  for (const sizeKB of sizes) {
    console.log(`\nTest: ${sizeKB}KB image`);
    console.log('='.repeat(40));
    
    try {
      // Create a valid base64 image of the specified size
      // Start with a real PNG header
      const pngHeader = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8/5+hnoEIwDiqkL4KAcT9E/f4uc66AAAAAElFTkSuQmCC';
      
      // Calculate padding needed
      const targetSize = sizeKB * 1024;
      const paddingNeeded = Math.max(0, targetSize - pngHeader.length);
      
      // Create valid base64 padding (must be divisible by 4)
      const paddingChars = Math.floor(paddingNeeded / 4) * 4;
      const padding = 'A'.repeat(paddingChars);
      
      const base64Data = pngHeader + padding;
      const dataUrl = `data:image/png;base64,${base64Data}`;
      
      // Build input exactly like our multi-agent orchestrator
      const conversationId = '123';
      const message = 'What do you see in this image?';
      
      // First add the image
      let agentInput = `${message}\n\n![User uploaded image](${dataUrl})`;
      
      // Add conversation history
      const historyText = 'User: Hello\nAssistant: Hi there!';
      agentInput = `Previous conversation:\n${historyText}\n\nUser: ${agentInput}`;
      
      // Add conversation ID
      agentInput = `[Conversation ID: ${conversationId}]\n${agentInput}`;
      
      console.log(`Input size: ${(agentInput.length / 1024).toFixed(0)}KB`);
      console.log(`Base64 size: ${(base64Data.length / 1024).toFixed(0)}KB`);
      
      const startTime = Date.now();
      
      // Add a timeout like our test
      const timeoutMs = 60000; // 60 seconds
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error(`Timeout after ${timeoutMs/1000}s`)), timeoutMs)
      );
      
      const runPromise = run(testAgent, agentInput, {
        maxTurns: 10, // Same as our orchestrator
        context: { conversationId },
        trace: {
          workflow_name: 'Test Workflow',
          metadata: { conversation_id: conversationId }
        }
      });
      
      const result = await Promise.race([runPromise, timeoutPromise]);
      const elapsed = Date.now() - startTime;
      
      console.log(`✅ SUCCESS in ${elapsed}ms`);
      console.log(`Response: ${result.state._currentStep.output.substring(0, 100)}...`);
      
    } catch (error) {
      console.log(`❌ FAILED: ${error.message}`);
      
      // If this size failed, skip larger sizes
      if (error.message.includes('Timeout') || error.message.includes('500')) {
        console.log('\nStopping tests - hit failure threshold');
        break;
      }
    }
  }
}

// Also test what happens with very long conversation history
async function testWithLongHistory() {
  console.log('\n\nTesting impact of conversation history...\n');
  
  // Create a small valid image
  const smallImage = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8/5+hnoEIwDiqkL4KAcT9E/f4uc66AAAAAElFTkSuQmCC';
  const dataUrl = `data:image/png;base64,${smallImage}`;
  
  // Test with different history lengths
  const historyLengths = [0, 10, 50, 100, 200];
  
  for (const numMessages of historyLengths) {
    console.log(`\nTest with ${numMessages} messages in history`);
    
    try {
      let agentInput = `What do you see?\n\n![User uploaded image](${dataUrl})`;
      
      if (numMessages > 0) {
        const history = [];
        for (let i = 0; i < numMessages; i++) {
          history.push(`User: Question ${i}?`);
          history.push(`Assistant: Answer ${i}.`);
        }
        agentInput = `Previous conversation:\n${history.join('\n')}\n\nUser: ${agentInput}`;
      }
      
      agentInput = `[Conversation ID: 123]\n${agentInput}`;
      
      console.log(`Total input size: ${(agentInput.length / 1024).toFixed(0)}KB`);
      
      const startTime = Date.now();
      const result = await run(testAgent, agentInput, { maxTurns: 1 });
      
      console.log(`✅ SUCCESS in ${Date.now() - startTime}ms`);
      
    } catch (error) {
      console.log(`❌ FAILED: ${error.message}`);
    }
  }
}

// Run tests
async function runAllTests() {
  await testWithIncreasingSize();
  await testWithLongHistory();
  
  console.log('\n\nCONCLUSIONS:');
  console.log('============');
  console.log('Based on these tests, we can identify where the actual limits are.');
}

runAllTests().then(() => {
  process.exit(0);
}).catch(error => {
  console.error('Test suite failed:', error);
  process.exit(1);
});