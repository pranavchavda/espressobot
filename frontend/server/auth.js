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
router.get('/google', 
  passport.authenticate('google', { 
    scope: ['profile', 'email'],
    accessType: 'offline',
    prompt: 'consent'
  })
);

router.get('/google/callback',
  passport.authenticate('google', { 
    failureRedirect: '/login?error=auth_failed',
    failureMessage: true 
  }),
  (req, res) => {
    // Generate JWT token
    const token = generateToken(req.user);
    
    // Redirect to frontend with token
    res.redirect(`/?token=${token}`);
  }
);

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