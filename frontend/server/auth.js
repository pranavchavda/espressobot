import { Router } from 'express';
import passport from 'passport';
import jwt from 'jsonwebtoken';

const router = Router();

// JWT secret
const JWT_SECRET = process.env.JWT_SECRET || 'your-jwt-secret-change-this';

// Generate JWT token
const generateToken = (user) => {
  return jwt.sign(
    { 
      id: user.id, 
      email: user.email,
      name: user.name 
    },
    JWT_SECRET,
    { expiresIn: '7d' }
  );
};

// Google OAuth routes
router.get('/google', (req, res, next) => {
  // Log the current host for debugging
  const host = req.get('host');
  const protocol = req.get('x-forwarded-proto') || req.protocol;
  console.log('OAuth request from:', `${protocol}://${host}`);
  
  // Ensure we're using HTTPS in production (Replit)
  if (host.includes('replit.dev') && protocol !== 'https') {
    return res.redirect(`https://${host}${req.originalUrl}`);
  }
  
  // Generate a state parameter to prevent CSRF and duplicate callbacks
  const state = Math.random().toString(36).substring(7);
  req.session.oauthState = state;
  
  passport.authenticate('google', { 
    scope: ['profile', 'email'],
    accessType: 'offline',
    prompt: 'consent',
    state: state
  })(req, res, next);
});

router.get('/google/callback', (req, res, next) => {
  console.log('OAuth callback received:', {
    query: req.query,
    host: req.get('host'),
    protocol: req.get('x-forwarded-proto') || req.protocol,
    fullUrl: req.originalUrl,
    session: req.session?.id,
    sessionState: req.session?.oauthState,
    queryState: req.query.state,
    cookies: req.headers.cookie
  });

  // Check if this callback has already been processed
  if (req.session.oauthProcessed) {
    console.log('OAuth callback already processed, redirecting to home');
    return res.redirect('/');
  }

  // Validate state parameter
  if (req.session.oauthState && req.query.state !== req.session.oauthState) {
    console.error('OAuth state mismatch');
    return res.redirect('/login?error=state_mismatch');
  }

  passport.authenticate('google', { 
    failureRedirect: '/login?error=auth_failed',
    failureMessage: true 
  }, (err, user, info) => {
    if (err) {
      console.error('OAuth error:', err);
      return res.redirect('/login?error=server_error');
    }
    if (!user) {
      console.error('OAuth failed:', info);
      return res.redirect('/login?error=auth_failed');
    }
    
    req.logIn(user, (err) => {
      if (err) {
        console.error('Login error:', err);
        return res.redirect('/login?error=login_failed');
      }
      
      // Mark session as processed to prevent duplicate callbacks
      req.session.oauthProcessed = true;
      
      // Generate JWT token
      const token = generateToken(user);
      console.log('OAuth success, redirecting with token for user:', user.email);
      
      // Clear OAuth state
      delete req.session.oauthState;
      
      // Save session before redirect
      req.session.save((saveErr) => {
        if (saveErr) {
          console.error('Session save error:', saveErr);
        }
        // Redirect to frontend with token
        res.redirect(`/?token=${token}`);
      });
    });
  })(req, res, next);
});

// Get current user
router.get('/me', async (req, res) => {
  if (req.user) {
    // Fetch fresh user data to get is_whitelisted status
    try {
      const { PrismaClient } = await import('@prisma/client');
      const prisma = new PrismaClient();
      const user = await prisma.users.findUnique({
        where: { id: req.user.id }
      });
      
      res.json({
        id: user.id,
        email: user.email,
        name: user.name,
        profile_picture: user.profile_picture,
        is_whitelisted: user.is_whitelisted,
      });
    } catch (error) {
      res.json({
        id: req.user.id,
        email: req.user.email,
        name: req.user.name,
        profile_picture: req.user.profile_picture,
        is_whitelisted: true, // Default to true if can't fetch
      });
    }
  } else {
    res.status(401).json({ error: 'Not authenticated' });
  }
});

// Logout
router.post('/logout', (req, res) => {
  req.logout((err) => {
    if (err) {
      return res.status(500).json({ error: 'Logout failed' });
    }
    res.json({ message: 'Logged out successfully' });
  });
});

// Verify JWT token middleware
export const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    // Allow localhost terminal requests for testing
    const isLocalhost = req.ip === '127.0.0.1' || req.ip === '::1' || req.ip === '::ffff:127.0.0.1';
    const isTerminalRequest = req.headers['x-terminal-request'] === 'true';
    
    if (isLocalhost && isTerminalRequest) {
      // Use the userId from the request body if provided, convert to integer
      let userId = req.body?.userId;
      
      // Convert string user IDs to integers
      if (userId === 'user_2') userId = 2;
      else if (userId === 'user_1') userId = 1;
      else if (typeof userId === 'string') userId = parseInt(userId);
      else if (!userId) userId = 2; // Default to user 2
      
      req.user = { id: userId, email: `user${userId}@localhost`, name: 'Terminal User' };
      return next();
    }
    
    // In development, allow unauthenticated access with default user
    if (process.env.NODE_ENV === 'development' && process.env.ALLOW_UNAUTHENTICATED === 'true') {
      req.user = { id: 1, email: 'dev@localhost', name: 'Development User' };
      return next();
    }
    return res.status(401).json({ error: 'Access token required' });
  }

  jwt.verify(token, JWT_SECRET, (err, user) => {
    if (err) {
      return res.status(403).json({ error: 'Invalid token' });
    }
    req.user = user;
    next();
  });
};

export default router;