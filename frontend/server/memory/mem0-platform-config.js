/**
 * Mem0 Platform (hosted service) configuration for EspressoBot
 * Using Mem0's managed cloud service instead of self-hosting
 */

import MemoryClient from 'mem0ai';

// Use Mem0 Platform (hosted service)
// Get your API key from https://mem0.dev/pd-api
const MEM0_API_KEY = process.env.MEM0_API_KEY;

if (!MEM0_API_KEY) {
  console.warn('[Mem0 Platform] MEM0_API_KEY not set. To use Mem0 Platform:');
  console.warn('[Mem0 Platform] 1. Sign up at https://mem0.dev/pd-api');
  console.warn('[Mem0 Platform] 2. Copy your API key from the dashboard');
  console.warn('[Mem0 Platform] 3. Set MEM0_API_KEY environment variable');
  console.warn('[Mem0 Platform] 4. Restart the server');
  console.warn('[Mem0 Platform] Falling back to simple memory store...');
}

// Initialize memory client for hosted service
export const memoryClient = MEM0_API_KEY ? new MemoryClient({ 
  apiKey: MEM0_API_KEY
}) : null;

// Export flag to indicate if platform is available
export const isPlatformAvailable = !!MEM0_API_KEY;