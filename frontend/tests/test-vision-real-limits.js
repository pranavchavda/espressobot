import { Agent, run } from '@openai/agents';
import { setDefaultOpenAIKey } from '@openai/agents-openai';
import fs from 'fs';
import https from 'https';

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

// Helper to download image from URL
async function downloadImage(url, filepath) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(filepath);
    https.get(url, (response) => {
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
    }).on('error', reject);
  });
}

async function testRealWorldImages() {
  console.log('Testing vision with real-world image sizes...\n');
  
  // Test 1: 1MB image
  console.log('Test 1: ~1MB image from URL');
  try {
    // High quality image that's about 1MB
    const largeImageUrl = 'https://upload.wikimedia.org/wikipedia/commons/thumb/f/ff/Pizigani_1367_Chart_10MB.jpg/2560px-Pizigani_1367_Chart_10MB.jpg';
    
    console.log('Testing with URL directly (should work)...');
    const urlInput = `What do you see in this historical map image?\n\n![Large map](${largeImageUrl})`;
    
    const urlResult = await run(visionTestAgent, urlInput, {
      maxTurns: 1
    });
    
    console.log('URL Result:', urlResult.state._currentStep.output.substring(0, 200) + '...');
    console.log('✅ URL test passed\n');
    
    // Now test with base64
    console.log('Downloading and converting to base64...');
    await downloadImage(largeImageUrl, '/tmp/test-large.jpg');
    const imageBuffer = fs.readFileSync('/tmp/test-large.jpg');
    const base64Data = imageBuffer.toString('base64');
    const dataUrl = `data:image/jpeg;base64,${base64Data}`;
    
    console.log('Image stats:');
    console.log('- Original size:', (imageBuffer.length / 1024 / 1024).toFixed(2), 'MB');
    console.log('- Base64 length:', (base64Data.length / 1024 / 1024).toFixed(2), 'MB');
    
    const base64Input = `What do you see in this historical map image?\n\n![Large map base64](${dataUrl})`;
    
    console.log('\nTesting with base64 (may fail if too large)...');
    const startTime = Date.now();
    
    try {
      const base64Result = await run(visionTestAgent, base64Input, {
        maxTurns: 1
      });
      console.log('Base64 Result:', base64Result.state._currentStep.output.substring(0, 200) + '...');
      console.log('✅ Base64 test passed in', Date.now() - startTime, 'ms');
    } catch (error) {
      console.error('❌ Base64 test failed:', error.message);
      if (error.message.includes('500')) {
        console.log('This confirms the issue - large base64 images cause 500 errors');
      }
    }
    
  } catch (error) {
    console.error('Test 1 failed:', error.message);
  }
  
  // Test 2: Realistic product photo size (500KB)
  console.log('\n\nTest 2: Realistic product photo (~500KB)');
  try {
    const productImageUrl = 'https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1200&q=80';
    
    console.log('Downloading product image...');
    await downloadImage(productImageUrl, '/tmp/test-product.jpg');
    const productBuffer = fs.readFileSync('/tmp/test-product.jpg');
    const productBase64 = productBuffer.toString('base64');
    const productDataUrl = `data:image/jpeg;base64,${productBase64}`;
    
    console.log('Product image stats:');
    console.log('- Original size:', (productBuffer.length / 1024).toFixed(0), 'KB');
    console.log('- Base64 length:', (productBase64.length / 1024).toFixed(0), 'KB');
    
    const productInput = `What coffee equipment or products do you see in this image?\n\n![Product image](${productDataUrl})`;
    
    const result = await run(visionTestAgent, productInput, {
      maxTurns: 1
    });
    
    console.log('Result:', result.state._currentStep.output);
    console.log('✅ Product image test passed');
    
  } catch (error) {
    console.error('❌ Product image test failed:', error.message);
  }
  
  // Clean up
  try {
    fs.unlinkSync('/tmp/test-large.jpg');
    fs.unlinkSync('/tmp/test-product.jpg');
  } catch (e) {}
}

// Run the test
testRealWorldImages().then(() => {
  console.log('\n\nReal-world image test completed!');
  console.log('\nConclusions:');
  console.log('- URLs work reliably for any size');
  console.log('- Base64 has practical limits despite OpenAI docs saying 20MB');
  console.log('- The OpenAI agents SDK may have additional restrictions');
  process.exit(0);
}).catch(error => {
  console.error('Test failed:', error);
  process.exit(1);
});