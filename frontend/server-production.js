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
    const dashboardAnalyticsRoutes = (await import('./server/api/dashboard-analytics.js')).default;
    const scratchpadRoutes = (await import('./server/api/scratchpad.js')).default;
    
    // Setup routes
    app.use('/api/auth', authRoutes);
    app.use('/api/conversations', convHandler);
    app.use('/api/agent', orchestratorRouter);
    app.use('/api/profile', profileRoutes);
    app.use('/api/memory', memoryManagementRoutes);
    app.use('/api/prompt-library', promptLibraryRoutes);
    app.use('/api/dashboard', dashboardAnalyticsRoutes);
    app.use('/api/scratchpad', scratchpadRoutes);
    
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
  // Serve static files from dist
  app.use(express.static(path.join(__dirname, 'dist')));

  // Fallback to index.html for SPA routing
  app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'dist', 'index.html'));
  });

  app.listen(port, '0.0.0.0', () => {
    console.log(`🚀 Production server running on port ${port}`);
  });
}).catch((error) => {
  console.error('❌ Failed to start server:', error);
  process.exit(1);
});