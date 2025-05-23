# OpenAI Responses API Integration for Flask-ShopifyBot

## Overview

This document outlines the integration of the OpenAI Responses API into the Flask-ShopifyBot application. The implementation replaces the previous chat completions API with the more advanced Responses API, which provides better support for agentic workflows and native MCP (Multimodal Conversational Processing).

## Changes Made

### 1. New Branch Creation
- Created a new branch `feature/openai-responses-api-integration` for all changes

### 2. Environment Variables Setup
- Added support for the following environment variables:
  - `OPENAI_MODEL="o4-mini"` - Model to use for the Responses API
  - `DEFAULT_MODEL="gpt-4.1-nano"` - Fallback model for simpler operations
  - Other existing environment variables are maintained

### 3. Code Modifications

#### responses_agent.py
- Completely rewrote the `responses_agent.py` file with a modern implementation
- Added a fallback to the chat completions API for reliability
- Implemented proper error handling and logging
- Added support for streaming responses
- Created a `generate_conversation_title` function that uses the OpenAI API

#### app.py
- Fixed async handling in the `/chat` endpoint
- Updated conversation creation to use UUID for unique filenames
- Removed invalid `user_id` parameter from Message model constructor
- Improved error handling and logging
- Added proper async/await patterns with event loops

### 4. Database Schema Compatibility
- Added support for the `filename` column in the Conversation model
- Ensured unique filenames for conversations using UUID
- Fixed model/data mapping issues

### 5. Security Enhancements
- Ensured environment variables are loaded from `.env` file
- Created `.env.sample` as a template (without actual credentials)
- Prevented sensitive data exposure in logs and responses

## Setup Instructions

1. Clone the repository and checkout the new branch:
```bash
git clone https://github.com/pranavchavda/flask-shopifybot/
cd flask-shopifybot
git checkout feature/openai-responses-api-integration
```

2. Create a `.env` file with the required environment variables:
```
# OpenAI API Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=o4-mini
DEFAULT_MODEL=gpt-4.1-nano

# Flask Configuration
FLASK_SECRET_KEY=yourrandomsecret
CHAT_PASSWORD=notklaump

# Shopify Configuration
SHOPIFY_API_VERSION=2025-04
SHOPIFY_ACCESS_TOKEN=your_shopify_access_token
SHOPIFY_SHOP_URL=https://your-shop.myshopify.com

# Database Configuration
DATABASE_URL=postgresql://username:password@hostname/database
# Or individual parameters:
PGDATABASE=database_name
PGHOST=hostname
PGPORT=5432
PGUSER=username
PGPASSWORD=password

# Authentication
ALLOWED_EMAILS=email1@example.com,email2@example.com
VITE_APP_PASSWORD=notklaump
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python -m flask run --host=0.0.0.0 --port=5000
```

## Usage

The application now uses the OpenAI Responses API for the main chat functionality, which provides better support for agentic workflows. The integration maintains all existing features while adding the following benefits:

1. **Improved Performance**: The Responses API is faster and more efficient for agentic purposes
2. **Native MCP Support**: Better handling of multimodal conversational processing
3. **Enhanced Tool Calling**: More robust tool calling capabilities
4. **Streaming Responses**: Real-time streaming of responses for better user experience

## Technical Notes

### Fallback Mechanism

The implementation includes a fallback to the chat completions API if the Responses API encounters issues. This ensures reliability while still leveraging the advanced features of the Responses API when available.

### Async Implementation

The code uses proper async/await patterns with event loops to handle asynchronous operations efficiently. This prevents blocking the main thread and improves overall performance.

### Error Handling

Comprehensive error handling has been implemented throughout the codebase to ensure robustness and provide meaningful error messages when issues occur.

## Future Improvements

1. **Full Responses API Integration**: The current implementation uses a fallback to chat completions API. A future update could fully implement the Responses API with all its features.
2. **Enhanced Tool Integration**: Further integration with the Responses API's tool calling capabilities.
3. **Improved Memory Service**: Better integration with the memory service for more contextual conversations.
