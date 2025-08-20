import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import tailwindcss from "@tailwindcss/vite";
import tailwindTypography from "@tailwindcss/typography";
import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

// Load environment variables
dotenv.config();

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
      name: 'full-auth-middleware',
      async configureServer(server) {
        console.log('🔐 Setting up full authentication middleware...');
        
        try {
          const express = (await import('express')).default;
          const bodyParser = (await import('body-parser')).default;
          const session = (await import('express-session')).default;
          const cookieParser = (await import('cookie-parser')).default;
          const passport = (await import('passport')).default;
          
          // Add LangGraph backend proxy using http-proxy-middleware (restored from archive)
          const { createProxyMiddleware } = await import('http-proxy-middleware');
          const LANGGRAPH_BACKEND_URL = 'http://localhost:8000';
          
          console.log(`🔗 Setting up LangGraph proxy to: ${LANGGRAPH_BACKEND_URL}`);
          
          // Create general proxy for agent endpoints
          const langGraphProxy = createProxyMiddleware({
            target: LANGGRAPH_BACKEND_URL,
            changeOrigin: true,
            pathRewrite: {
              // Don't rewrite paths - keep them as-is
            },
            onProxyReq: (proxyReq, req, res) => {
              console.log(`[LangGraph Proxy] ${req.method} ${req.originalUrl || req.url} -> ${LANGGRAPH_BACKEND_URL}${req.originalUrl || req.url}`);
              
              // Forward the body for POST requests
              if (req.body && (req.method === 'POST' || req.method === 'PUT' || req.method === 'PATCH')) {
                const bodyData = JSON.stringify(req.body);
                proxyReq.setHeader('Content-Type', 'application/json');
                proxyReq.setHeader('Content-Length', Buffer.byteLength(bodyData));
                proxyReq.write(bodyData);
              }
            },
            onError: (err, req, res) => {
              console.error('[LangGraph Proxy] Error:', err);
              res.status(502).json({
                error: 'Backend connection failed',
                message: err.message,
                backend: LANGGRAPH_BACKEND_URL
              });
            }
          });
          
          // Apply proxy - use middleware that matches full paths and forwards them intact
          server.middlewares.use((req, res, next) => {
            if (req.url.startsWith('/api/agent') || 
                req.url.startsWith('/api/memory') || 
                req.url.startsWith('/api/conversations') ||
                req.url.startsWith('/api/dashboard') ||
                req.url.startsWith('/api/price-monitor') ||
                req.url.startsWith('/api/scratchpad') ||
                req.url.startsWith('/api/dynamic-agents') ||
                req.url.startsWith('/api/user-mcp-servers') ||
                req.url.startsWith('/api/agent-management') ||
                req.url.startsWith('/api/orchestrator')) {
              langGraphProxy(req, res, next);
            } else {
              next();
            }
          });
          
          console.log('✅ LangGraph proxy middleware active');
          
          // Import auth configuration from archived backend
          const configureGoogleStrategy = (await import('./archive/legacy-nodejs-backend/server/config/auth.js')).default;
          const authRoutes = (await import('./archive/legacy-nodejs-backend/server/auth.js')).default;
          const { authenticateToken } = await import('./archive/legacy-nodejs-backend/server/auth.js');
          
          const authApp = express();
          
          // Cookie parser middleware
          authApp.use(cookieParser());
          
          // Session configuration
          authApp.use(session({
            secret: process.env.SESSION_SECRET || 'your-session-secret-change-this',
            resave: false,
            saveUninitialized: true,
            cookie: {
              secure: process.env.NODE_ENV === 'production',
              httpOnly: true,
              maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
              sameSite: 'lax'
            }
          }));
          
          // Initialize passport
          authApp.use(passport.initialize());
          authApp.use(passport.session());
          
          // Configure Google OAuth strategy
          await configureGoogleStrategy();
          console.log('✅ Google OAuth strategy configured');
          
          // Body parser middleware
          authApp.use(bodyParser.json({ limit: '10mb' }));
          authApp.use(bodyParser.urlencoded({ limit: '10mb', extended: true }));
          
          // Auth routes
          authApp.use('/api/auth', authRoutes);
          
          server.middlewares.use(authApp);
          console.log('✅ Authentication middleware active');
        } catch (error) {
          console.error('❌ Auth setup failed:', error.message);
          console.log('🔄 Falling back to minimal auth...');
          
          // Fallback minimal auth
          const express = (await import('express')).default;
          const authApp = express();
          
          authApp.get('/api/auth/google', (req, res) => {
            res.status(501).json({ 
              error: 'Auth setup failed',
              message: 'Check console for details',
              details: error.message
            });
          });
          
          authApp.get('/api/auth/me', (req, res) => {
            res.json({ id: 1, email: 'dev@example.com', name: 'Development User' });
          });
          
          server.middlewares.use(authApp);
        }
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
        '**/data/**',                      // Ignore data files
        '**/archive/**',                   // Ignore archived content
        '**/TODO-*.md',                    // Ignore TODO markdown files
        '**/*.db',                         // Ignore all database files
        '**/*.sqlite',                     // Ignore SQLite files
        '**/*.db-journal',                 // Ignore SQLite journal files
        '**/*.db-wal',                     // Ignore SQLite WAL files
        '**/*.db-shm',                     // Ignore SQLite shared memory files
        '**/espressobot_memory.db*',       // Ignore memory database
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