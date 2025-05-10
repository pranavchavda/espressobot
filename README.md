# Shopify Agent Chatbot

A friendly AI-powered chat interface for your Shopify store. Ask questions, run queries, and perform updates using natural language.

## Features

- Chat with your Shopify store using natural language
- View orders, products, and customers
- Update product details and store settings
- Secure, password-protected access
- Conversation history saved in a local database

## Prerequisites

Before you begin, make sure you have:
- **Python 3.8** or higher installed
- **pip** (Python package manager)
- An active **OpenAI API key**
- **OpenAI Model** name (e.g., `gpt-4.1`)
- **Shopify Admin API** credentials:
  - Admin API Access Token
  - Store URL (e.g., `your-store.myshopify.com`)
- **Perplexity API key** (`PERPLEXITY_API_KEY`)
- **SKU Vault credentials**:
  - Tenant Token (`SKUVAULT_TENANT_TOKEN`)
  - User Token (`SKUVAULT_USER_TOKEN`)

## Setup Guide (For Non-Technical Users)

1. **Download the Project**
   - Download the ZIP from GitHub or clone with SSH:
     ```bash
     git clone git@github.com:pranavchavda/flask-shopifybot.git
     ```
     - If you don't have access, ask Pranav to add you as a collaborator or request a pre-filled `.env`.

2. **Create a Python Environment**
   - Linux/macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - Windows:
     ```batch
     python -m venv venv
     venv\Scripts\activate
     ```

3. **Install Required Packages**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**

   - Create a file named `.env` in the project root.
   - Copy and paste the following, replacing values:

     ```env
     OPENAI_API_KEY=your_openai_api_key
     OPENAI_MODEL=gpt-4.1
     SHOPIFY_ACCESS_TOKEN=your_shopify_admin_api_token
     SHOPIFY_SHOP_URL=your-store.myshopify.com
     SHOPIFY_API_VERSION=2025-04
     CHAT_PASSWORD=your_chat_password
     FLASK_SECRET_KEY=yourrandomsecret
     PERPLEXITY_API_KEY=your_perplexity_api_key
     SKUVAULT_TENANT_TOKEN=your_skuvault_tenant_token
     SKUVAULT_USER_TOKEN=your_skuvault_user_token
     DEFAULT_MODEL=gpt-4.1
     ```

5. **Start the Application**

   ```bash
   python app.py
   ```

6. **Access the Chat Interface**

   - Open your browser and go to: `http://localhost:5000`
   - Enter the password you set (`CHAT_PASSWORD`)
   - Start chatting with your Shopify store!

## Usage Tips

- **Query Examples**:
  - "Show me my last 5 orders."
  - "How many products do I have?"
- **Update Examples**:
  - "Update the price of product ID 123456 to $19.99."
  - "Add tag 'On Sale' to product ID 789012."

## Troubleshooting

- **App won't start / module errors**:
  - Make sure your Python environment is activated.
  - Verify your `.env` file is present with correct keys.
- **Password loop**:
  - Confirm `CHAT_PASSWORD` matches in `.env`.
- **Database issues**:
  - Delete `shopify_agent.db` to reset (clears chat history).

## Project Structure

- `app.py` — Flask server and routes
- `simple_agent.py` — AI agent logic & tool execution
- `skuvault_tools.py` — Shop-specific tool definitions
- `database.py` — Local SQLite database setup
- `templates/` — HTML templates for the chat UI
- `requirements.txt` — List of Python dependencies

## Support

Need help? File an issue on GitHub or contact the project maintainer.
