// Note: The preprocessBase64Image function below requires the 'sharp' package
// Uncomment the import below if you want to use it
// import sharp from 'sharp';

/**
 * Preprocesses base64 images to ensure they work reliably with OpenAI agents SDK
 * Based on testing, the SDK has intermittent issues with certain base64 formats
 * Note: This function requires the 'sharp' package to be installed
 */
export async function preprocessBase64Image(base64DataUrl) {
  try {
    // Extract base64 data and MIME type
    const dataUrlMatch = base64DataUrl.match(/^data:([^;]+);base64,(.+)$/);
    if (!dataUrlMatch) {
      console.log('[VISION-PREPROCESS] Not a valid data URL, returning as-is');
      return base64DataUrl;
    }
    
    const mimeType = dataUrlMatch[1];
    const base64Data = dataUrlMatch[2];
    
    // Convert base64 to buffer
    const buffer = Buffer.from(base64Data, 'base64');
    
    console.log('[VISION-PREPROCESS] Original image size:', buffer.length, 'bytes');
    
    // Process with sharp to ensure consistent format
    let processedBuffer;
    
    // Always convert to PNG for consistency
    // PNG seems to work more reliably based on testing
    processedBuffer = await sharp(buffer)
      .png({
        compressionLevel: 9, // Max compression for smaller size
        quality: 100 // Maintain quality
      })
      .toBuffer();
    
    console.log('[VISION-PREPROCESS] Processed image size:', processedBuffer.length, 'bytes');
    
    // If the processed image is larger, check if we should resize
    if (processedBuffer.length > 300 * 1024) { // 300KB threshold
      console.log('[VISION-PREPROCESS] Image too large, resizing...');
      
      // Get metadata to determine aspect ratio
      const metadata = await sharp(buffer).metadata();
      const maxDimension = 1024; // Max width/height
      
      let resizeOptions = {};
      if (metadata.width > metadata.height) {
        resizeOptions.width = Math.min(metadata.width, maxDimension);
      } else {
        resizeOptions.height = Math.min(metadata.height, maxDimension);
      }
      
      processedBuffer = await sharp(buffer)
        .resize(resizeOptions)
        .png({
          compressionLevel: 9,
          quality: 85 // Slightly lower quality for size
        })
        .toBuffer();
        
      console.log('[VISION-PREPROCESS] Resized image size:', processedBuffer.length, 'bytes');
    }
    
    // Convert back to base64 data URL
    const processedBase64 = processedBuffer.toString('base64');
    const processedDataUrl = `data:image/png;base64,${processedBase64}`;
    
    return processedDataUrl;
    
  } catch (error) {
    console.error('[VISION-PREPROCESS] Error preprocessing image:', error.message);
    // Return original on error
    return base64DataUrl;
  }
}

/**
 * Alternative: Ensure image has proper formatting without sharp
 * This is a lighter-weight alternative that just validates the format
 */
export function validateAndFixBase64(base64DataUrl) {
  try {
    // Ensure it's a valid data URL
    const dataUrlMatch = base64DataUrl.match(/^data:([^;]+);base64,(.+)$/);
    if (!dataUrlMatch) {
      // Try to fix common issues
      if (base64DataUrl.startsWith('data:image') && base64DataUrl.includes(',')) {
        // Already looks like a data URL, return as-is
        return base64DataUrl;
      }
      
      // Assume PNG if no data URL prefix
      console.log('[VISION-VALIDATE] Adding data URL prefix');
      return `data:image/png;base64,${base64DataUrl}`;
    }
    
    const mimeType = dataUrlMatch[1];
    const base64Data = dataUrlMatch[2];
    
    // Remove any whitespace from base64 data
    const cleanBase64 = base64Data.replace(/\s/g, '');
    
    // Validate base64 characters
    const base64Regex = /^[A-Za-z0-9+/]*={0,2}$/;
    if (!base64Regex.test(cleanBase64)) {
      console.error('[VISION-VALIDATE] Invalid base64 characters detected');
      throw new Error('Invalid base64 data');
    }
    
    // Ensure MIME type is properly formatted
    const validMimeTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif'];
    const cleanMimeType = validMimeTypes.includes(mimeType) ? mimeType : 'image/png';
    
    // Return cleaned data URL
    return `data:${cleanMimeType};base64,${cleanBase64}`;
    
  } catch (error) {
    console.error('[VISION-VALIDATE] Validation error:', error.message);
    return base64DataUrl;
  }
}