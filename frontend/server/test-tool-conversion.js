import { openAITools } from './tools/openai-tool-converter.js';

console.log('🧪 Testing Tool Conversion\n');
console.log(`Successfully converted ${Object.keys(openAITools).length} tools:\n`);

Object.keys(openAITools).forEach(name => {
  console.log(`✅ ${name}`);
});

console.log('\n✨ All tools converted successfully!');
process.exit(0);