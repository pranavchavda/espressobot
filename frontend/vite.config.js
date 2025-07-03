import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";
import tailwindTypography from "@tailwindcss/typography";
import path from "node:path";
import { fileURLToPath } from "node:url";

// Load environment variables from .env file
import { config } from 'dotenv';
config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);


export default defineConfig({
  define: {
    'import.meta.env.VITE_USE_MULTI_AGENT': JSON.stringify(process.env.USE_MULTI_AGENT || 'false')
  },
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
        // Check if environment variables are available in server middleware
        console.log('SERVER MIDDLEWARE ENV CHECK:');
        console.log('OPENAI_API_KEY available:', !!process.env.OPENAI_API_KEY);
        console.log('OPENAI_MODEL:', process.env.OPENAI_MODEL);
        console.log('DATABASE_URL:', process.env.DATABASE_URL);
        console.log('GOOGLE_CLIENT_ID available:', !!process.env.GOOGLE_CLIENT_ID);
        console.log('GOOGLE_CLIENT_SECRET available:', !!process.env.GOOGLE_CLIENT_SECRET);
        
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
        const session = (await import('express-session')).default;
        const cookieParser = (await import('cookie-parser')).default;
        const passport = (await import('passport')).default;
        
        // Import auth configuration
        const configureGoogleStrategy = (await import('./server/config/auth')).default;
        const authRoutes = (await import('./server/auth')).default;
        const convHandler = (await import('./server/conversations')).default;
        
        // Use bash orchestrator as the default and only orchestrator
        console.log('Using Bash Orchestrator (Shell Agency)');
        
        const orchestratorRouter = (await import('./server/bash-orchestrator-api')).default;

        const apiApp = express();
        
        // Cookie parser middleware
        apiApp.use(cookieParser());
        
        // Session configuration
        apiApp.use(session({
          secret: process.env.SESSION_SECRET || 'your-session-secret-change-this',
          resave: false,
          saveUninitialized: false,
          cookie: {
            secure: process.env.NODE_ENV === 'production',
            httpOnly: true,
            maxAge: 7 * 24 * 60 * 60 * 1000 // 7 days
          }
        }));
        
        // Initialize passport
        apiApp.use(passport.initialize());
        apiApp.use(passport.session());
        
        // Configure Google OAuth strategy
        configureGoogleStrategy();
        
        // Body parser middleware
        apiApp.use(bodyParser.json({ limit: '50mb' }));
        apiApp.use(bodyParser.urlencoded({ limit: '50mb', extended: true }));
        
        // Routes
        apiApp.use('/api/auth', authRoutes);
        apiApp.use('/api/conversations', convHandler);
        apiApp.use('/api/agent', orchestratorRouter);
        
        // Memory management routes (admin only)
        const memoryManagementRoutes = (await import('./server/memory-management')).default;
        apiApp.use('/api/memory', memoryManagementRoutes);
        
        // Prompt library routes (admin only)
        const promptLibraryRoutes = (await import('./server/api/prompt-library')).default;
        apiApp.use('/api/prompt-library', promptLibraryRoutes);
        
        server.middlewares.use(apiApp);
      },
    },
  ],
  server: {
    watch: {
      ignored: [
        '**/dev.db', 
        '**/prisma/migrations/**', 
        '**/.memories/**', 
        '**/memories/**',
        '**/server/memory/data/**',        // Ignore local memory database files
        '**/server/plans/**',              // Ignore TaskGen TODO files
        '**/TODO-*.md',                    // Ignore TODO markdown files
        '**/*.db',                         // Ignore all database files
        '**/*.sqlite',                     // Ignore SQLite files
        '**/*.db-journal',                 // Ignore SQLite journal files
        '**/*.db-wal',                     // Ignore SQLite WAL files
        '**/*.db-shm',                     // Ignore SQLite shared memory files
        '**/espressobot_memory.db*',       // Ignore our specific memory database
        '**/server/memory/test-*.js',      // Ignore memory test files
        '**/server/context-loader/**',     // Ignore context loader cache
        '**/server/prompts/**',            // Ignore prompt files (static)
        '**/server/tool-docs/**',          // Ignore tool documentation
        '**/.env.local*',                  // Ignore local environment files
        '**/logs/**',                      // Ignore log files
        '**/*.log'                         // Ignore individual log files
      ],
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