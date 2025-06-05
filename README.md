<!-- markdownlint-disable MD041 MD025 -->
# Shopify Agent Chatbot (Frontend Only)

> A modern, AI-powered chat interface for your Shopify store, built as a full-stack React Router 7 application with Node.js, Prisma, and the OpenAI Agents SDK & Responses API.

## Features

- **Basic Chat**: Uses the OpenAI Responses API with built‑in tools (e.g., `web_search_preview`)
- **Streaming Responses**: Real-time token updates via Server-Sent Events (SSE) for a live chat experience
- **Title Creator**: Automatically generate concise titles for chat conversations in the history sidebar
- **Agentic Workflows**: Leverage the OpenAI Agents JS SDK for custom agents and tool integration
- **Persistent Storage**: Conversations and messages stored in SQLite (local dev) or Postgres via Prisma
- **React Router 7 (Framework Edition)**: File-based routing with loaders & actions (no Flask)
- **Single-User Local Dev**: No auth—runs locally for user ID 1 only

## Prerequisites

- **nvm** (Node.js Version Manager) configured in your shell (e.g. `source ~/.nvm/nvm.sh`)
- **Node.js** (>=22) and **npm**
- **SQLite** (file-based, for local development) or **PostgreSQL** (Neon DB or compatible) for persistence
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
# Edit frontend/.env.local and set:
#   • DATABASE_URL (e.g. `file:./dev.db` for SQLite or a Postgres URL)
#   • OPENAI_API_KEY, OPENAI_MODEL
#   • (optional) PLANNER_AGENT_MODEL (default: o4-mini)
#   • (optional) MEMORY_FILE_PATH (path to your memory file, e.g. storage/memory.json)
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
   npx prisma migrate dev --name init  # run initial migration (creates dev.db for SQLite)
   npx prisma generate               # generate the Prisma client
   ```

6. **Run the dev server**
```bash
npm run dev             # starts Vite on http://localhost:5173
```

7. **(Optional) Start a local memory server for agent context**
```bash
# Only needed for Agent Mode and memory-based tools:
npx -y @modelcontextprotocol/server-memory
```
# The server uses the MEMORY_FILE_PATH environment variable (set in frontend/.env.local) to persist memory.

8. **Open the app (and test the chat API stub)**
   - Visit `http://localhost:5173/api/chat` → it should return:
     ```json
     { "message": "Chat API is working" }
     ```
   - Then navigate to `http://localhost:5173` to launch the React UI.

9. **(Optional) Test the conversation endpoints**
   ```bash
   curl http://localhost:5173/api/conversations        # list all conversations
   curl http://localhost:5173/api/conversations/1      # fetch messages for conversation ID 1
   ```

10. **(Optional) Test the Planner agent endpoint**
   ```bash
   curl -X POST http://localhost:5173/api/agent/planner \
     -H 'Content-Type: application/json' \
     -d '{"conv_id": 1}'
   ```

11. **(Optional) Test the Master Agent orchestration endpoint**
   ```bash
   curl -N -X POST http://localhost:5173/api/agent/run \
     -H 'Content-Type: application/json' \
     -d '{"message": "Upload product Widget 3000 to SkuVault"}'
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

	- [x] Scaffold Planner agent endpoint and UI toggle for agentic planning workflows
	- [x] Add support for custom MCP servers and Node-based MCP via NPX
	- [x] Add end-to-end tests for front-end UI and API middleware
	- [x] Polish UI/UX (styling, loading states, error handling)
   - [ ] Reintroduce memory storage, retrival and proactive injection of memory into the system prompt based on the conversation history and context
   - [ ] Strengthen agentic architecture and be more agentic
   - [ ] Add Google tasks, Gmail, Calendar, Drive, and Sheets integration
   - [ ] Add Klaviyo, Attentive, Yotpo and Recharge integration for admin tasks
   - [ ] Add Google Ads and GA4 integration for marketing tasks
   - [ ] Display yesterday's and today's Sales, Ads, and Marketing metrics in the UI (Sidebar?)
   - [ ] Reintroduce the authentication flow for multiple users - use Google OAuth + Whitelist defined in .env