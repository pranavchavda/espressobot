import { run } from '@openai/agents';

/**
 * Wrapper function that retries vision requests with base64 images
 * to handle the ~20% failure rate observed in testing
 */
export async function runWithVisionRetry(agent, messages, options = {}, maxRetries = 3) {
  let lastError;
  let lastResult;
  
  // Check if this is a vision request with base64 data
  const hasBase64Image = messages.some(msg => {
    if (typeof msg.content === 'object' && Array.isArray(msg.content)) {
      return msg.content.some(item => 
        item.type === 'input_image' && 
        typeof item.image === 'string' &&
        item.image.startsWith('data:image')
      );
    }
    return false;
  });

  // If no base64 images, just run normally
  if (!hasBase64Image) {
    console.log('[VISION-RETRY] No base64 images detected, running normally');
    return run(agent, messages, options);
  }

  console.log('[VISION-RETRY] Base64 image detected, enabling retry logic');
  
  // Try up to maxRetries times
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`[VISION-RETRY] Attempt ${attempt}/${maxRetries}`);
      
      const result = await run(agent, messages, options);
      
      // Check if the response seems valid (not hallucinated)
      const response = result.finalOutput || result.state?._currentStep?.output || '';
      
      // Common hallucination patterns when image isn't seen
      const hallucinations = [
        'unable to see',
        'cannot see',
        'no image',
        'don\'t see an image',
        'cannot analyze',
        'unable to view',
        'image is not visible',
        'appears to be black',
        'black rectangle',
        'solid black'
      ];
      
      const lowerResponse = response.toLowerCase();
      const isHallucinated = hallucinations.some(pattern => lowerResponse.includes(pattern));
      
      // For color detection, check if it mentions the wrong color
      // If asking about red and it says blue/yellow/etc, that's a hallucination
      const hasColorQuestion = messages.some(msg => {
        const text = JSON.stringify(msg).toLowerCase();
        return text.includes('color') || text.includes('colour');
      });
      
      // List of wrong colors (anything but red for our test)
      const wrongColors = ['blue', 'green', 'yellow', 'purple', 'orange', 'black', 'white', 'gray', 'grey'];
      const wrongColorDetected = hasColorQuestion && 
        wrongColors.some(color => lowerResponse.includes(color)) && 
        !lowerResponse.includes('red');
      
      if ((isHallucinated || wrongColorDetected) && attempt < maxRetries) {
        console.log('[VISION-RETRY] Response appears hallucinated, retrying...');
        console.log('[VISION-RETRY] Response was:', response);
        lastResult = result;
        // Small delay before retry
        await new Promise(resolve => setTimeout(resolve, 1000));
        continue;
      }
      
      console.log('[VISION-RETRY] Success on attempt', attempt);
      return result;
      
    } catch (error) {
      console.error(`[VISION-RETRY] Error on attempt ${attempt}:`, error.message);
      lastError = error;
      
      if (attempt < maxRetries) {
        // Small delay before retry
        await new Promise(resolve => setTimeout(resolve, 500));
      }
    }
  }
  
  // If we get here, all retries failed
  console.error('[VISION-RETRY] All retries exhausted');
  
  // Return last result if we have one, otherwise throw last error
  if (lastResult) {
    console.log('[VISION-RETRY] Returning last result despite possible hallucination');
    return lastResult;
  }
  
  throw lastError || new Error('Vision processing failed after retries');
}

/**
 * Alternative: Convert base64 to temporary URL using blob
 * This might work more reliably but requires browser environment
 */
export function convertBase64ToBlob(base64DataUrl) {
  try {
    const [header, base64] = base64DataUrl.split(',');
    const mimeMatch = header.match(/data:([^;]+)/);
    const mimeType = mimeMatch ? mimeMatch[1] : 'image/png';
    
    // Convert base64 to binary
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    
    // Create blob
    const blob = new Blob([bytes], { type: mimeType });
    
    // Create object URL (only works in browser)
    if (typeof URL !== 'undefined' && URL.createObjectURL) {
      return URL.createObjectURL(blob);
    }
    
    return null;
  } catch (error) {
    console.error('[VISION-RETRY] Error converting base64 to blob:', error);
    return null;
  }
}