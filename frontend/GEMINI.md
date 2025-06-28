
# EspressoBot Frontend

This project is a React-based web application that serves as the frontend for EspressoBot, an agent-based system. It includes a server-side component built with Express.js that handles API requests and orchestrates the agentic workflows.

## Key Technologies

*   **Frontend:** React, Vite, Tailwind CSS
*   **Backend:** Node.js, Express.js
*   **Database:** Prisma
*   **Agents:** `@openai/agents`

## Project Structure

The project is organized into the following main directories:

*   `src/`: Contains the React frontend code.
*   `server/`: Contains the Express.js backend code, including the agent and tool definitions.
*   `prisma/`: Contains the Prisma schema and migrations for the database.
*   `public/`: Contains static assets for the web application.

## Architecture

The application follows an agentic architecture, with a central orchestrator that manages the interaction between different agents and tools. The orchestrator can be configured to use either a multi-agent or a unified approach, depending on the `USE_MULTI_AGENT` environment variable.

The system is designed to be extensible, with support for custom tools, including Python scripts. It also has built-in vision capabilities, with a robust solution for handling base64-encoded images.

## Getting Started

To run the application, you'll need to have Node.js and pnpm installed. Then, follow these steps:

1.  Install the dependencies: `pnpm install`
2.  Start the development server: `pnpm dev`

This will start the Vite development server and the Express.js backend. You can then access the application in your browser at `http://localhost:5173`.

## Building for Production

To build the application for production, run the following command:

```
pnpm build
```

This will create a `dist/` directory with the optimized and minified assets.

## Testing

The project includes a large number of test files, located in the root directory. These tests cover various aspects of the application, from the agent orchestration to the UI components. To run the tests, you'll need to have the necessary test runners and frameworks installed.
