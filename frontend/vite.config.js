import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";
import tailwindTypography from "@tailwindcss/typography";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);


export default defineConfig({
  plugins: [
    react(),
    tailwindcss({
      config: {
        darkMode: "class",
        content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
        theme: {
          extend: {
            colors: {
              shopifyPurple: "#5c6ac4",
            },
          },
        },
        plugins: [tailwindTypography],
      },
    }),
    {
      name: 'server-middleware',
      async configureServer(server) {
        if (!process.env.SKIP_MEMORY_SERVER) {
          const { spawn } = await import('child_process');
          console.log('Starting local memory server for agent context...');
          const memoryProc = spawn(
            'npx', ['-y', '@modelcontextprotocol/server-memory'],
            {
              env: {
                ...process.env,
                MEMORY_FILE_PATH: process.env.MEMORY_FILE_PATH,
              },
              stdio: 'inherit',
              detached: true,
            }
          );
          memoryProc.unref();
          const cleanup = () => {
            try {
              process.kill(-memoryProc.pid);
            } catch {}
          };
          process.on('SIGINT', () => {
            cleanup();
            process.exit();
          });
          process.on('exit', cleanup);
        }
        const express = (await import('express')).default;
        const bodyParser = (await import('body-parser')).default;
        const chatHandler = (await import('./server/chat')).default;
        const convHandler = (await import('./server/conversations')).default;
        const streamChatHandler = (await import('./server/stream_chat')).default;
        const plannerHandler = (await import('./server/agent_planner')).default;
        const masterHandler = (await import('./server/agent_master')).default;

        const apiApp = express();
        apiApp.use(bodyParser.json({ limit: '50mb' }));
        apiApp.use(bodyParser.urlencoded({ limit: '50mb', extended: true }));
        apiApp.use('/api/conversations', convHandler);
        apiApp.use('/api/chat', chatHandler);
        apiApp.use('/stream_chat', streamChatHandler);
        apiApp.use('/api/agent/planner', plannerHandler);
        apiApp.use('/api/agent/run', masterHandler);
        server.middlewares.use(apiApp);
      },
    },
  ],
  server: {
    watch: {
      ignored: ['**/dev.db', '**/prisma/migrations/**'],
    },
    port: 5173,
    open: true,
    host: "0.0.0.0",
  },
  resolve: {
    alias: {
      "@components": path.resolve(__dirname, "src/components"),
      "@common": path.resolve(__dirname, "src/components/common"),
      "@features": path.resolve(__dirname, "src/features"),
      "@routes": path.resolve(__dirname, "src/routes"),
      "@lib": path.resolve(__dirname, "src/lib"),
    },
  },
});