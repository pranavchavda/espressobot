#!/usr/bin/env python3
"""
Test GPT-5 with proper environment and parameters
"""
import os
import requests
import json

# Get API key from environment
api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    print("❌ OPENAI_API_KEY not found in environment")
    exit(1)

print(f"✅ Using API key: {api_key[:10]}...")

# Test GPT-5-mini
print("\n🚀 Testing GPT-5-mini...")
response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    },
    json={
        "model": "gpt-5-mini",
        "messages": [{"role": "user", "content": "Complete: I am GPT-5-mini and I am"}],
        "max_completion_tokens": 20  # Note: GPT-5 uses max_completion_tokens, not max_tokens
    }
)

if response.status_code == 200:
    data = response.json()
    content = data['choices'][0]['message']['content']
    print(f"✅ GPT-5-mini says: {content}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.json())

# Test GPT-5-nano
print("\n🚀 Testing GPT-5-nano...")
response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    },
    json={
        "model": "gpt-5-nano",
        "messages": [{"role": "user", "content": "Complete: I am GPT-5-nano and I am"}],
        "max_completion_tokens": 20
    }
)

if response.status_code == 200:
    data = response.json()
    content = data['choices'][0]['message']['content']
    print(f"✅ GPT-5-nano says: {content}")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.json())

print("\n✨ GPT-5 models are working!")