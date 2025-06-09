// Simple script to check environment variables
import 'dotenv/config';

console.log('====== ENVIRONMENT VARIABLES CHECK ======');
console.log('OPENAI_API_KEY:', process.env.OPENAI_API_KEY ? 'Set (hidden for security)' : 'NOT SET');
console.log('OPENAI_MODEL:', process.env.OPENAI_MODEL || 'NOT SET');
console.log('SHOPIFY_ACCESS_TOKEN:', process.env.SHOPIFY_ACCESS_TOKEN ? 'Set (hidden for security)' : 'NOT SET'); 
console.log('MCP_BEARER_TOKEN:', process.env.MCP_BEARER_TOKEN ? 'Set (hidden for security)' : 'NOT SET');
console.log('DATABASE_URL:', process.env.DATABASE_URL || 'NOT SET');
console.log('========================================');
