import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";
import tailwindTypography from "@tailwindcss/typography";
import path from "node:path";
import { fileURLToPath } from "node:url";

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
            typography: ({ theme }) => ({
              DEFAULT: {
                css: {
                  '--tw-prose-body': theme('colors.zinc[700]'),
                  '--tw-prose-headings': theme('colors.zinc[900]'),
                  '--tw-prose-links': theme('colors.indigo[600]'),
                  '--tw-prose-bold': theme('colors.zinc[900]'),
                  '--tw-prose-counters': theme('colors.zinc[500]'),
                  '--tw-prose-bullets': theme('colors.zinc[500]'),
                  '--tw-prose-hr': theme('colors.zinc[200]'),
                  '--tw-prose-quotes': theme('colors.zinc[900]'),
                  '--tw-prose-quote-borders': theme('colors.zinc[300]'),
                  '--tw-prose-captions': theme('colors.zinc[500]'),
                  '--tw-prose-code': theme('colors.zinc[900]'),
                  '--tw-prose-pre-code': theme('colors.zinc[200]'),
                  '--tw-prose-pre-bg': theme('colors.zinc[800]'),
                  '--tw-prose-th-borders': theme('colors.zinc[300]'),
                  '--tw-prose-td-borders': theme('colors.zinc[200]'),
                  '--tw-prose-invert-body': theme('colors.zinc[300]'),
                  '--tw-prose-invert-headings': theme('colors.white'),
                  '--tw-prose-invert-links': theme('colors.indigo[400]'),
                  '--tw-prose-invert-bold': theme('colors.white'),
                  '--tw-prose-invert-counters': theme('colors.zinc[400]'),
                  '--tw-prose-invert-bullets': theme('colors.zinc[400]'),
                  '--tw-prose-invert-hr': theme('colors.zinc[700]'),
                  '--tw-prose-invert-quotes': theme('colors.zinc[100]'),
                  '--tw-prose-invert-quote-borders': theme('colors.zinc[700]'),
                  '--tw-prose-invert-captions': theme('colors.zinc[400]'),
                  '--tw-prose-invert-code': theme('colors.white'),
                  '--tw-prose-invert-pre-code': theme('colors.zinc[300]'),
                  '--tw-prose-invert-pre-bg': 'rgb(0 0 0 / 50%)',
                  '--tw-prose-invert-th-borders': theme('colors.zinc[600]'),
                  '--tw-prose-invert-td-borders': theme('colors.zinc[700]'),
                  'ul > li::marker': { color: theme('colors.zinc[500]') },
                  'ol > li::marker': { color: theme('colors.zinc[500]') },
                  'ul, ol': { paddingLeft: '1.5rem', marginTop: '1rem', marginBottom: '1rem' },
                  'li': { marginTop: '0.25rem', marginBottom: '0.25rem' },
                  'table': { width: '100%', borderCollapse: 'collapse', marginTop: '1.5rem', marginBottom: '1.5rem' },
                  'thead': { backgroundColor: theme('colors.zinc[100]'), borderBottomWidth: '2px' },
                  'th': { padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: '600' },
                  'td': { padding: '0.5rem 0.75rem', borderTopWidth: '1px' },
                  'tbody tr:nth-child(even)': { backgroundColor: theme('colors.zinc[50]') },
                  '.dark tbody tr:nth-child(even)': { backgroundColor: theme('colors.zinc[800]/0.4') }
                },
              },
            }),
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
        
        // Initialize database connection
        try {
          const { testConnection, startConnectionHealthMonitor } = await import('./server/config/database.js');
          console.log('🔗 Testing database connection...');
          const dbOk = await testConnection(1); // Single retry
          if (dbOk) {
            console.log('✅ Database connection verified');
            // Start connection health monitoring
            startConnectionHealthMonitor();
          } else {
            console.warn('⚠️ Database connection failed, but continuing...');
          }
        } catch (error) {
          console.error('❌ Database initialization error:', error.message);
        }
        
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
        const { authenticateToken } = await import('./server/auth');
        const convHandler = (await import('./server/conversations')).default;
        
        // Check if we should use LangGraph backend
        const useLangGraph = process.env.USE_LANGGRAPH === 'true';
        
        let orchestratorRouter;
        if (useLangGraph) {
          console.log('Using LangGraph Backend Integration');
          orchestratorRouter = (await import('./server/langgraph-orchestrator')).default;
        } else {
          console.log('Using Bash Orchestrator (Shell Agency)');
          orchestratorRouter = (await import('./server/bash-orchestrator-api')).default;
        }

        const apiApp = express();
        
        // Cookie parser middleware
        apiApp.use(cookieParser());
        
        // Session configuration
        apiApp.use(session({
          secret: process.env.SESSION_SECRET || 'your-session-secret-change-this',
          resave: false,
          saveUninitialized: true, // Changed to true for OAuth flows
          cookie: {
            secure: process.env.NODE_ENV === 'production',
            httpOnly: true,
            maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
            sameSite: 'lax' // Important for OAuth redirects
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
        // Apply authentication to agent routes so user_id is available
        apiApp.use('/api/agent', authenticateToken, orchestratorRouter);
        
        // Profile routes
        const profileRoutes = (await import('./server/profile')).default;
        apiApp.use('/api/profile', profileRoutes);
        
        // Tasks routes
        const tasksRoutes = (await import('./server/tasks')).default;
        apiApp.use('/api/tasks', tasksRoutes);
        apiApp.use('/api/authorize/google', (req, res) => {
          res.status(501).json({ 
            error: 'Google Tasks OAuth is not configured',
            message: 'This feature requires Google Tasks API and OAuth setup'
          });
        });
        
        // Memory management routes - proxy to LangGraph backend
        const memoryProxyRoutes = (await import('./server/api/memory-proxy')).default;
        apiApp.use('/api/memory', memoryProxyRoutes);
        
        // Prompt library routes (admin only)
        const promptLibraryRoutes = (await import('./server/api/prompt-library')).default;
        apiApp.use('/api/prompt-library', promptLibraryRoutes);
        
        // Guardrail decision routes
        const { setupGuardrailRoutes } = await import('./server/api/guardrail-decision-handler.js');
        setupGuardrailRoutes(apiApp);
        
        // Dashboard analytics routes - proxy to Python backend
        const dashboardProxyRoutes = (await import('./server/api/dashboard-proxy.js')).default;
        apiApp.use('/api/dashboard', dashboardProxyRoutes);
        
        // Scratchpad routes
        const scratchpadRoutes = (await import('./server/api/scratchpad.js')).default;
        apiApp.use('/api/scratchpad', scratchpadRoutes);
        
        // Price monitor routes - proxy to Python backend
        const priceMonitorProxyRoutes = (await import('./server/api/price-monitor-proxy.js')).default;
        apiApp.use('/api/price-monitor', priceMonitorProxyRoutes);
        
        // Agent management routes - proxy to Python backend
        const agentManagementProxy = (await import('./server/api/agent-management-proxy.js')).default;
        apiApp.use('/api/agent-management', agentManagementProxy);
        
        // Dynamic agents routes - proxy to Python backend
        const dynamicAgentsProxy = (await import('./server/api/dynamic-agents-proxy.js')).default;
        apiApp.use('/api/dynamic-agents', dynamicAgentsProxy);
        
        // User MCP servers routes - proxy to Python backend
        const userMCPServersProxy = (await import('./server/api/user-mcp-servers-proxy.js')).default;
        apiApp.use('/api/user-mcp-servers', userMCPServersProxy);
        
        // Add aggressive cache-busting middleware before API routes
        server.middlewares.use((req, res, next) => {
          // Check if it's a hard refresh (Ctrl+Shift+R or Ctrl+F5)
          const isHardRefresh = req.headers['cache-control'] === 'no-cache' || 
                               req.headers['pragma'] === 'no-cache';
          
          // Always set aggressive cache-busting headers for HTML files and API endpoints
          if (req.url.endsWith('.html') || req.url.startsWith('/api/') || req.url === '/') {
            res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate, private, max-age=0');
            res.setHeader('Pragma', 'no-cache');
            res.setHeader('Expires', '0');
            res.setHeader('Last-Modified', new Date().toUTCString());
            res.setHeader('ETag', `"${Date.now()}-${Math.random()}"`); // Dynamic ETag
            res.setHeader('Vary', 'Cache-Control, Pragma');
          }
          // For hard refresh requests, bust cache on all assets
          else if (isHardRefresh) {
            res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
            res.setHeader('Pragma', 'no-cache');
            res.setHeader('Expires', '0');
            res.setHeader('Last-Modified', new Date().toUTCString());
            res.setHeader('ETag', `"${Date.now()}-${Math.random()}"`);
          }
          // For static assets in development, short cache with revalidation
          else {
            res.setHeader('Cache-Control', 'public, max-age=0, must-revalidate'); // No cache in dev
            res.setHeader('Last-Modified', new Date().toUTCString());
            res.setHeader('ETag', `"${Date.now()}-${Math.random()}"`);
          }
          
          next();
        });
        
        server.middlewares.use(apiApp);
      },
    },
  ],
  server: {
    allowedHosts: [
      'localhost',
      '.replit.dev',
      /^.*\.replit\.dev$/
    ],
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
    open: false,
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