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
- [x] Title Creator agent for auto-generating conversation titles in sidebar

## Upcoming Enhancements
- [x] Integrate OpenAI Agents JS SDK workflows (tool chaining, agent planning)
- [x] Connect to remote Shopify MCP server for shopify-specific tools
	- [x] Scaffold Master Agent orchestration endpoint and Agent Mode toggle in chat UI
- [x] Add support for local stdio-based MCP servers via NPX for custom tools
- [x] Add support for local memory server via NPX for agent context memory
- [x] Enable full SSE streaming for multi-agent orchestrator (planner, dispatcher, synthesizer statuses, and token-by-token assistant responses).
    - [x] Backend: Correctly handle `agent_text_delta_stream_event` for synthesizer token streaming.
    - [x] Frontend: Parse all orchestrator SSE events and update UI accordingly.
- [x] Resolve non-agent mode spinner issue (ensure `setIsSending(false)` on `data.done === true`).
- [ ] Restore and verify planner status display and `TaskProgress` UI component in Agent Mode.
    - [ ] Ensure `currentPlan` and `currentTasks` states are correctly populated from SSE events.
    - [ ] Verify UI elements for plan steps and task progress are visible and functional.
- [ ] Validate and refine Planner sub-agent instructions and model parameters for reliable JSON plan output (ongoing).
- [ ] Add end-to-end tests for front-end UI and API middleware.
- [ ] General UI/UX Polish (styling, loading states, error handling improvements).
## Fully Agentized
- [ ] Make full use of openai-agents-js SDK for agent orchestration and tool chaining
