<!-- markdownlint-disable MD041 MD025 -->
# Shopify Agent Chatbot (Frontend Only)

> A modern, AI-powered chat interface for your Shopify store, built as a full-stack React Router 7 application with Node.js, Prisma, and the OpenAI Agents SDK & Responses API.

## Features

- **Basic Chat**: Uses the OpenAI Responses API with built‑in tools (e.g., `web_search_preview`)
- **Agentic Workflows**: Leverage the OpenAI Agents JS SDK for custom agents and tool integration
- **Persistent Storage**: Conversations and messages stored in Postgres (Neon DB) via Prisma
- **React Router 7 (Framework Edition)**: File-based routing with loaders & actions (no Flask)
- **Single-User Local Dev**: No auth—runs locally for user ID 1 only

## Prerequisites

- **nvm** (Node.js Version Manager) configured in your shell (e.g. `source ~/.nvm/nvm.sh`)
- **Node.js** (>=22) and **npm**
- **PostgreSQL** (Neon DB or compatible) for persistence
- **OpenAI API Key** for both Responses API and Agents SDK

## Getting Started

1. **Clone the repo**
   ```bash
   git clone <repo-url>
   cd <project-root>
   ```

2. **Copy and configure environment variables**
   ```bash
   cp .env frontend/.env.local
   # Edit frontend/.env.local and set DATABASE_URL, OPENAI_API_KEY, and OPENAI_MODEL
   ```

3. **Switch to the correct Node version**
   ```bash
   source ~/.nvm/nvm.sh && nvm use 22
   ```

4. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

5. **Set up Prisma**
   ```bash
   npx prisma db pull      # introspect existing Neon DB schema
   npx prisma generate     # generate the Prisma client
   ```

6. **Run the dev server**
   ```bash
   npm run dev             # starts Vite on http://localhost:5173
   ```

7. **Open the app (and test the chat API stub)**
   - Visit `http://localhost:5173/api/chat` → it should return:
     ```json
     { "message": "Chat API is working" }
     ```
   - Then navigate to `http://localhost:5173` to launch the React UI.

8. **(Optional) Test the conversation endpoints**
   ```bash
   curl http://localhost:5173/api/conversations        # list all conversations
   curl http://localhost:5173/api/conversations/1      # fetch messages for conversation ID 1
   ```

## Project Structure

```text
<project-root>/
├── frontend/             # React Router 7 app (Vite)
│   ├── prisma/           # Prisma schema & migrations
│   │   └── schema.prisma
│   ├── src/              # Components, routes, and client code
│   ├── .env.local        # Local env vars (gitignored)
│   ├── package.json
│   └── vite.config.js
├── TODO.md               # Roadmap & next steps
├── .gitignore            # Ignore patterns
└── README.md             # This file
```

## Next Steps

- Build out chat UI: loaders/actions for conversations and messages
- Integrate OpenAI Agents JS SDK for Shopify tool chains
- Add support for custom MCP servers and Node-based MCPS via NPX