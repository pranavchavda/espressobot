import express from 'express';
import { fileURLToPath } from 'url';
import path from 'path';
import dotenv from 'dotenv';
import cors from 'cors';
import bodyParser from 'body-parser';
import session from 'express-session';
import cookieParser from 'cookie-parser';
import passport from 'passport';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const port = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(cookieParser());
app.use(session({
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

app.use(passport.initialize());
app.use(passport.session());
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Setup routes
async function setupRoutes() {
  try {
    // Import and setup auth
    const configureGoogleStrategy = (await import('./server/config/auth.js')).default;
    configureGoogleStrategy();
    
    // Import all routes
    const authRoutes = (await import('./server/auth.js')).default;
    const convHandler = (await import('./server/conversations.js')).default;
    const orchestratorRouter = (await import('./server/bash-orchestrator-api.js')).default;
    const profileRoutes = (await import('./server/profile.js')).default;
    const memoryManagementRoutes = (await import('./server/memory-management.js')).default;
    const promptLibraryRoutes = (await import('./server/api/prompt-library.js')).default;
    const dashboardProxyRoutes = (await import('./server/api/dashboard-proxy.js')).default;
    const scratchpadRoutes = (await import('./server/api/scratchpad.js')).default;
    const priceMonitorProxyRoutes = (await import('./server/api/price-monitor-proxy.js')).default;
    
    // Setup routes
    app.use('/api/auth', authRoutes);
    app.use('/api/conversations', convHandler);
    app.use('/api/agent', orchestratorRouter);
    app.use('/api/profile', profileRoutes);
    app.use('/api/memory', memoryManagementRoutes);
    app.use('/api/prompt-library', promptLibraryRoutes);
    app.use('/api/dashboard', dashboardProxyRoutes);
    app.use('/api/scratchpad', scratchpadRoutes);
    app.use('/api/price-monitor', priceMonitorProxyRoutes);
    
    // Guardrail routes
    const { setupGuardrailRoutes } = await import('./server/api/guardrail-decision-handler.js');
    setupGuardrailRoutes(app);
    
    console.log('✅ All routes configured successfully');
  } catch (error) {
    console.error('❌ Error setting up routes:', error);
    process.exit(1);
  }
}

// Initialize routes and start server
setupRoutes().then(() => {
  // Add aggressive cache-busting middleware for all responses
  app.use((req, res, next) => {
    // Check if it's a hard refresh (Ctrl+Shift+R or Ctrl+F5)
    const isHardRefresh = req.headers['cache-control'] === 'no-cache' || 
                         req.headers['pragma'] === 'no-cache';
    
    // Always set aggressive cache-busting headers for HTML files and API endpoints
    if (req.path.endsWith('.html') || req.path.startsWith('/api/') || req.path === '/') {
      res.set({
        'Cache-Control': 'no-cache, no-store, must-revalidate, private, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0',
        'Last-Modified': new Date().toUTCString(),
        'ETag': `"${Date.now()}-${Math.random()}"`, // Dynamic ETag
        'Vary': 'Cache-Control, Pragma'
      });
    }
    // For hard refresh requests, bust cache on all assets
    else if (isHardRefresh) {
      res.set({
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'Last-Modified': new Date().toUTCString(),
        'ETag': `"${Date.now()}-${Math.random()}"`
      });
    }
    // For static assets, short cache with revalidation
    else {
      res.set({
        'Cache-Control': 'public, max-age=300, must-revalidate', // 5 minutes
        'Last-Modified': new Date().toUTCString(),
        'ETag': `"${Date.now()}-${Math.random()}"`
      });
    }
    
    next();
  });

  // Serve static files from dist with cache control
  app.use(express.static(path.join(__dirname, 'dist'), {
    maxAge: 0, // No caching
    etag: true,
    lastModified: true,
    setHeaders: (res, path) => {
      res.set({
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      });
    }
  }));

  // Fallback to index.html for SPA routing with cache busting
  app.get('*', (req, res) => {
    res.set({
      'Cache-Control': 'no-cache, no-store, must-revalidate, private, max-age=0',
      'Pragma': 'no-cache',
      'Expires': '0',
      'Last-Modified': new Date().toUTCString(),
      'ETag': `"${Date.now()}-${Math.random()}"`
    });
    res.sendFile(path.join(__dirname, 'dist', 'index.html'));
  });

  app.listen(port, '0.0.0.0', () => {
    console.log(`🚀 Production server running on port ${port}`);
    console.log(`🔧 Cache-busting enabled for aggressive browser cache prevention`);
  });
}).catch((error) => {
  console.error('❌ Failed to start server:', error);
  process.exit(1);
});