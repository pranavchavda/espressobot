# Roadmap & Next Steps

This document outlines the key next steps for the Shopify Agent Chatbot (frontend-only).

## Completed Tasks
- [x] Remove Flask backend and Python code
- [x] Scaffold chat UI routes and components (conversations list, message view, input form)
- [x] Implement loader/action functions for conversations and messages using Prisma client
- [x] Integrate OpenAI Responses API for basic chat completion flows (web_search_preview)
- [x] Configure Prisma schema via introspection and generate client for Neon DB
- [x] Mount Express/Vite middleware for /api/chat and /api/conversations endpoints
- [x] Update README with NVM/Node 22, Prisma setup, and chat API instructions

## Upcoming Enhancements
- [ ] Integrate OpenAI Agents JS SDK workflows (tool chaining, agent planning)
- [x] Connect to remote Shopify MCP server for shopify-specific tools
- [ ] Add support for local stdio-based MCP servers via NPX for custom tools
- [ ] Enable streaming responses in the chat UI for real-time token updates
- [ ] Add end-to-end tests for front-end UI and API middleware
- [ ] Polish UI/UX (styling, loading states, error handling)
