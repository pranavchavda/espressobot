#!/usr/bin/env node

// Quick diagnostic to check multi-agent UI setup

import fs from 'fs';
import path from 'path';

console.log('🔍 Checking Multi-Agent UI Setup...\n');

// Check environment setup
const envPath = '.env';
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf-8');
  const hasMultiAgent = envContent.includes('USE_MULTI_AGENT=true');
  console.log(`✅ Environment: USE_MULTI_AGENT=${hasMultiAgent ? 'true' : 'false (or not set)'}`);
  if (!hasMultiAgent) {
    console.log('   ⚠️  Set USE_MULTI_AGENT=true in .env to enable multi-agent mode');
  }
} else {
  console.log('❌ No .env file found');
}

// Check if vite is passing the env variable
console.log('\n📦 Vite Configuration:');
const viteConfig = fs.readFileSync('vite.config.js', 'utf-8');
if (viteConfig.includes('VITE_USE_MULTI_AGENT')) {
  console.log('✅ Vite is configured to pass VITE_USE_MULTI_AGENT');
} else {
  console.log('❌ Vite config missing VITE_USE_MULTI_AGENT setup');
}

// Check frontend detection
console.log('\n🎨 Frontend Setup:');
const streamingPage = fs.readFileSync('src/features/chat/StreamingChatPage.jsx', 'utf-8');
if (streamingPage.includes("import.meta.env.VITE_USE_MULTI_AGENT === 'true'")) {
  console.log('✅ Frontend checks VITE_USE_MULTI_AGENT correctly');
} else {
  console.log('❌ Frontend not checking VITE_USE_MULTI_AGENT properly');
}

if (streamingPage.includes('!useBasicAgent')) {
  console.log('✅ Multi-agent event handling is enabled when !useBasicAgent');
} else {
  console.log('❌ Multi-agent event handling not found');
}

if (streamingPage.includes("case 'agent_processing':")) {
  console.log('✅ Agent processing event handler is present');
} else {
  console.log('❌ Agent processing event handler is missing');
}

if (streamingPage.includes('agentProcessingStatus')) {
  console.log('✅ Agent processing status state is defined');
} else {
  console.log('❌ Agent processing status state is missing');
}

// Check backend
console.log('\n🔧 Backend Setup:');
const orchestrator = fs.readFileSync('server/multi-agent-orchestrator.js', 'utf-8');
if (orchestrator.includes('getAgentStatusMessage')) {
  console.log('✅ Agent status message helper is defined');
} else {
  console.log('❌ Agent status message helper is missing');
}

if (orchestrator.includes("sendEvent('agent_processing'")) {
  console.log('✅ Backend sends agent_processing events');
} else {
  console.log('❌ Backend not sending agent_processing events');
}

if (orchestrator.includes("sendEvent('task_plan_created'")) {
  console.log('✅ Backend sends task_plan_created events');
} else {
  console.log('❌ Backend not sending task_plan_created events');
}

console.log('\n📋 Summary:');
console.log('1. Make sure USE_MULTI_AGENT=true is set in .env');
console.log('2. Run with: USE_MULTI_AGENT=true npm run dev');
console.log('3. The backend endpoint should be: /api/multi-agent/run');
console.log('4. Check browser console for "FRONTEND: Multi-agent system started" message');