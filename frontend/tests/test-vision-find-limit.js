import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';

// Set the OpenAI API key
setDefaultOpenAIKey(process.env.OPENAI_API_KEY);

// Create a simple vision test agent
const visionTestAgent = new Agent({
  name: 'Vision_Test_Agent',
  instructions: 'You are a helpful assistant that can analyze images. When shown an image, describe what you see in detail.',
  model: 'gpt-4.1-mini',
  modelSettings: {
    temperature: 0.7
  }
});

// Create a more realistic test image
function createRealisticTestImage(sizeKB) {
  // Start with a real small PNG (this is a 10x10 red square)
  const realPNGBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8/5+hnoEIwDiqkL4KAcT9E/f4uc66AAAAAElFTkSuQmCC';
  
  // Calculate how much padding we need
  const targetBase64Length = sizeKB * 1024;
  const currentLength = realPNGBase64.length;
  
  if (targetBase64Length <= currentLength) {
    return realPNGBase64;
  }
  
  // PNG files can have comments, so we can pad safely
  // But for base64, we'll just repeat a valid base64 pattern
  const paddingNeeded = targetBase64Length - currentLength;
  const padding = 'A'.repeat(paddingNeeded);
  
  // Return the original PNG header plus padding
  // This creates an invalid PNG but valid base64
  return realPNGBase64 + padding;
}

async function findLimit() {
  console.log('Finding the practical base64 image size limit for OpenAI agents SDK...\n');
  
  // Test sizes in KB (more granular)
  const testSizesKB = [50, 100, 200, 300, 400, 500, 750, 1000];
  let lastWorkingSize = 0;
  let firstFailingSize = null;
  
  for (const sizeKB of testSizesKB) {
    console.log(`\nTesting ${sizeKB}KB image...`);
    
    try {
      const base64Data = createRealisticTestImage(sizeKB);
      const dataUrl = `data:image/png;base64,${base64Data}`;
      
      console.log(`Base64 length: ${base64Data.length} chars (${(base64Data.length / 1024).toFixed(0)}KB)`);
      
      const input = `What do you see in this image?\n\n![Test image](${dataUrl})`;
      
      const startTime = Date.now();
      
      // Set a shorter timeout to avoid hanging
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Timeout after 30s')), 30000)
      );
      
      const runPromise = run(visionTestAgent, input, {
        maxTurns: 1
      });
      
      const result = await Promise.race([runPromise, timeoutPromise]);
      
      const elapsed = Date.now() - startTime;
      console.log(`Response time: ${elapsed}ms`);
      
      const response = result.state._currentStep.output;
      console.log('Response preview:', response.substring(0, 80) + '...');
      
      console.log(`✅ ${sizeKB}KB - SUCCESS`);
      lastWorkingSize = sizeKB;
      
    } catch (error) {
      console.log(`❌ ${sizeKB}KB - FAILED: ${error.message}`);
      if (!firstFailingSize) {
        firstFailingSize = sizeKB;
      }
      
      // If we hit a failure, no point testing larger sizes
      break;
    }
  }
  
  console.log('\n\nRESULTS:');
  console.log('========');
  console.log(`✅ Last working size: ${lastWorkingSize}KB`);
  console.log(`❌ First failing size: ${firstFailingSize}KB`);
  
  if (firstFailingSize) {
    console.log(`\n📊 The practical limit appears to be between ${lastWorkingSize}KB and ${firstFailingSize}KB`);
    console.log('\nRECOMMENDATION:');
    console.log(`Set the limit to ${lastWorkingSize}KB for base64 images to ensure reliability.`);
    console.log('For larger images, use URLs instead of base64 encoding.');
  } else {
    console.log('\n✅ All tested sizes worked! The limit may be higher than tested.');
  }
}

// Run the test
findLimit().then(() => {
  console.log('\nLimit detection completed!');
  process.exit(0);
}).catch(error => {
  console.error('Test failed:', error);
  process.exit(1);
});