#!/bin/bash

# Load environment variables
source ../.env 2>/dev/null || source .env 2>/dev/null

echo "======================================"
echo "🧪 Testing GPT-5 API Access"
echo "======================================"

# Test OpenAI Direct
echo -e "\n🔹 Testing OpenAI Direct API..."
response=$(curl -s -w "\n%{http_code}" https://api.openai.com/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{
    "model": "gpt-5-mini",
    "messages": [{"role": "user", "content": "Say hello from GPT-5-mini via OpenAI"}],
    "max_tokens": 50
  }' --max-time 5)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo "✅ OpenAI GPT-5-mini: Working!"
    echo "$body" | grep -o '"content":"[^"]*' | cut -d'"' -f4
else
    echo "❌ OpenAI GPT-5-mini: HTTP $http_code"
    echo "$body" | grep -o '"message":"[^"]*' | cut -d'"' -f4
fi

# Test OpenRouter
echo -e "\n🔹 Testing OpenRouter API..."
response=$(curl -s -w "\n%{http_code}" https://openrouter.ai/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "HTTP-Referer: https://espressobot.com" \
  -H "X-Title: EspressoBot" \
  -d '{
    "model": "openai/gpt-5-mini",
    "messages": [{"role": "user", "content": "Say hello from GPT-5-mini via OpenRouter"}],
    "max_tokens": 50
  }' --max-time 5)

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo "✅ OpenRouter GPT-5-mini: Working!"
    echo "$body" | grep -o '"content":"[^"]*' | cut -d'"' -f4
else
    echo "❌ OpenRouter GPT-5-mini: HTTP $http_code"
    echo "$body" | grep -o '"message":"[^"]*' | cut -d'"' -f4
fi

echo -e "\n======================================"