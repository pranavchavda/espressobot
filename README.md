# Shopify Agent Chatbot

A modern, AI-powered chat interface for your Shopify store with a React frontend and Flask backend. Interact with your store using natural language, manage tasks, and get intelligent assistance.

## Features

- **Modern Web Interface**: Built with React and Vite for a smooth user experience
- **User Authentication**: Secure email/password login with whitelist support
- **Real-time Chat**: Token-by-token streaming for natural conversation flow
- **Shopify Integration**: Query and manage your store data using natural language
- **Task Management**: Integrated with Google Tasks API (coming soon)
- **Multi-user Support**: Each user has their own chat history and preferences
- **Responsive Design**: Works on desktop and mobile devices

## Prerequisites

Before you begin, make sure you have:
- **Python 3.8** or higher
- **Node.js 22.x** (required for the React frontend)
- **pip** (Python package manager)
- **npm** or **yarn** (Node package manager)
- **Required API Keys**:
  - OpenAI API key (`OPENAI_API_KEY`)
  - Shopify Admin API credentials:
    - Admin API Access Token (`SHOPIFY_ACCESS_TOKEN`)
    - Store URL (`SHOPIFY_SHOP_URL`)
  - Perplexity API key (`PERPLEXITY_API_KEY`)
  - (Optional) Google OAuth credentials for task integration

## Setup Guide

1. **Clone the Repository**
   ```bash
   git clone git@github.com:pranavchavda/flask-shopifybot.git
   cd flask-shopifybot
   ```

2. **Set Up Python Environment**
   ```bash
   # Create and activate virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

3. **Set Up Node.js Environment**
   ```bash
   # Navigate to frontend directory
   cd frontend
   
   # Make sure you're using Node.js 22.x
   nvm use 22
   
   # Install Node.js dependencies
   npm install
   
   # Return to project root
   cd ..
   ```

4. **Configure Environment Variables**
   - Create a `.env` file in the project root with the following variables:
     ```env
     # Flask Configuration
     FLASK_APP=app.py
     FLASK_ENV=development
     FLASK_SECRET_KEY=your-secret-key-here
     
     # Database
     DATABASE_URL=sqlite:///app.db
     
     # Authentication
     SECRET_KEY=your-secret-key-here
     ALLOWED_EMAILS=user1@example.com,user2@example.com
     
     # API Keys
     OPENAI_API_KEY=your_openai_api_key
     OPENAI_MODEL=gpt-4.1
     PERPLEXITY_API_KEY=your_perplexity_api_key
     
     # Shopify Configuration
     SHOPIFY_ACCESS_TOKEN=your_shopify_admin_api_token
     SHOPIFY_SHOP_URL=your-store.myshopify.com
     SHOPIFY_API_VERSION=2025-04
     
     # SKU Vault (optional)
     SKUVAULT_TENANT_TOKEN=your_skuvault_tenant_token
     SKUVAULT_USER_TOKEN=your_skuvault_user_token
     ```

5. **Initialize the Database**
   ```bash
   # Create database tables and initial admin user
   flask db upgrade
   ```

6. **Start the Development Servers**
   In separate terminal windows:
   
   **Backend (Flask):**
   ```bash
   # In project root
   flask run --port 5001
   ```
   
   **Frontend (Vite):**
   ```bash
   # In frontend directory
   cd frontend
   npm run dev
   ```

7. **Access the Application**
   - Open your browser to: `http://localhost:5173`
   - Register with a whitelisted email address
   - Log in and start chatting with your Shopify store!

## Usage

### Chat Interface
- Ask questions about your store in natural language
- Get real-time responses with token-by-token streaming
- View conversation history

### Example Queries
- "Show me my recent orders"
- "What products are low in stock?"
- "Create a new task to follow up with customers"
- "Analyze my sales from last month"

### User Management
- Register with a whitelisted email address
- Secure password-based authentication
- Individual chat histories for each user

## Troubleshooting

- **Node.js Version Issues**:
  ```bash
  # Make sure to use Node.js 22.x
  nvm use 22
  ```

- **Python Package Issues**:
  ```bash
  # Ensure virtual environment is activated
  source venv/bin/activate  # or venv\Scripts\activate on Windows
  pip install -r requirements.txt
  ```

- **Database Issues**:
  ```bash
  # Reset the database (warning: deletes all data)
  rm instance/app.db
  flask db upgrade
  ```

- **Frontend Not Connecting to Backend**:
  - Ensure both servers are running
  - Check that the frontend's `vite.config.js` has the correct proxy URL

## Project Structure

```
flask-shopifybot/
├── frontend/              # React frontend
│   ├── public/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── features/      # Feature modules
│   │   ├── App.jsx        # Main App component
│   │   └── main.jsx       # Entry point
│   ├── package.json
│   └── vite.config.js
│
├── migrations/           # Database migrations
├── static/               # Static files (CSS, JS, images)
├── templates/            # Legacy templates (being phased out)
│
├── .env.example         # Example environment variables
├── app.py               # Flask application
├── config.py            # Configuration settings
├── mcp_server.py        # MCP server implementations for various services
├── simple_memory.py     # Simple in-memory storage implementation
├── models.py            # Database models
├── requirements.txt     # Python dependencies
└── README.md            # This file
```

## Development

### Backend Development
```bash
# Run Flask development server
flask run --port 5001 --debug

# Create new database migration
export FLASK_APP=app.py
flask db migrate -m "description of changes"
flask db upgrade
```

### Frontend Development
```bash
cd frontend
npm run dev  # Start Vite dev server
npm run build  # Build for production
npm run preview  # Preview production build
```

## Deployment

### Prerequisites
- PostgreSQL database
- Gunicorn or similar WSGI server
- Nginx or similar reverse proxy

### Environment Variables
Set these in your production environment:
- `FLASK_ENV=production`
- `DATABASE_URL=postgresql://user:password@localhost/dbname`
- `SECRET_KEY` (generate a strong secret key)
- Other required API keys and credentials

## Advanced Features

### MCP Server Integration

The application includes model-controlled program (MCP) servers for various services:

- **Shopify MCP Server**: For querying the Shopify Admin API schema and documentation (uses npx @shopify/dev-mcp)
- **Perplexity MCP Server**: For accessing Perplexity AI services (direct API implementation)
- **Fetch MCP Server**: For web content fetching with advanced capabilities (hybrid implementation)
- **Memory MCP Server**: For persistent user-specific memory storage (simplified implementation)
- **Sequential Thinking MCP Server**: For structured step-by-step reasoning (hybrid implementation, attempts to use npx @modelcontextprotocol/server-sequential-thinking when available, with OpenAI API fallback)
- **Filesystem MCP Server**: For safe file operations within designated directories (simplified implementation)

These servers support two operation modes:
1. **Full MCP mode**: Uses official MCP packages when available for optimal functionality
2. **Simplified mode**: Falls back to direct API calls when packages aren't installed

To enable full MCP functionality, uncomment and install the optional packages in requirements.txt:
```
# Python MCP packages
mcp-client>=0.1.0
mcp-server-fetch>=0.1.0

# Node.js MCP packages (installed automatically with npx)
@modelcontextprotocol/server-sequential-thinking
```

You can test the MCP server implementations using the provided test scripts:
- `test_fetch_mcp.py`: Test the fetch server functionality
- `test_thinking_mcp.py`: Test the sequential thinking server functionality
- `test_mcp.py`: Test the Shopify and Perplexity MCP servers

## Future Enhancements

- [ ] Google OAuth integration
- [ ] Google Tasks API integration
- [ ] Enhanced admin dashboard
- [ ] Multi-store support
- [ ] Advanced analytics and reporting
- [x] MCP server integration with package support

## Support

For support, please [open an issue](https://github.com/pranavchavda/flask-shopifybot/issues) on GitHub or contact the project maintainer.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
