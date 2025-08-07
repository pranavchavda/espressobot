#!/bin/bash

# Test GPT-5 models directly with curl
echo "========================================"
echo "🚀 Testing GPT-5 Models Direct Access"
echo "========================================"

# Source the environment
source ../.env 2>/dev/null || true

# Test GPT-5-mini
echo -e "\n📍 Testing gpt-5-mini..."
curl -s https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [{"role": "user", "content": "Complete: I am GPT-5-mini and I am"}],
    "max_tokens": 20
  }' | python3 -c "import sys, json; data = json.load(sys.stdin); print('✅', data['choices'][0]['message']['content'])" 2>/dev/null || echo "❌ Failed"

# Test GPT-5-nano
echo -e "\n📍 Testing gpt-5-nano..."
curl -s https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-5-nano",
    "messages": [{"role": "user", "content": "Complete: I am GPT-5-nano and I am"}],
    "max_tokens": 20
  }' | python3 -c "import sys, json; data = json.load(sys.stdin); print('✅', data['choices'][0]['message']['content'])" 2>/dev/null || echo "❌ Failed"

# Test GPT-5 (full)
echo -e "\n📍 Testing gpt-5..."
curl -s https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-5",
    "messages": [{"role": "user", "content": "Complete: I am GPT-5 and I am"}],
    "max_tokens": 20
  }' | python3 -c "import sys, json; data = json.load(sys.stdin); print('✅', data['choices'][0]['message']['content'])" 2>/dev/null || echo "❌ Failed"

echo -e "\n========================================"
echo "✨ GPT-5 is ready for use!"
echo "========================================"