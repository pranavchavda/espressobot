import passport from 'passport';
import { Strategy as GoogleStrategy } from 'passport-google-oauth20';
import { PrismaClient } from '@prisma/client';

const prisma = new PrismaClient();

// Google OAuth configuration
const configureGoogleStrategy = () => {
  const clientID = process.env.GOOGLE_CLIENT_ID || 'your-client-id';
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET || 'your-client-secret';
  const callbackURL = process.env.GOOGLE_CALLBACK_URL || 'http://localhost:5173/api/auth/google/callback';
  
  console.log('Google OAuth Config:', {
    clientID: clientID.substring(0, 10) + '...',
    clientSecret: clientSecret.substring(0, 10) + '...',
    callbackURL
  });
  
  passport.use(
    new GoogleStrategy(
      {
        clientID,
        clientSecret,
        callbackURL,
      },
      async (accessToken, refreshToken, profile, done) => {
        try {
          console.log('Google OAuth Success! Profile:', {
            id: profile.id,
            email: profile.emails?.[0]?.value,
            name: profile.displayName
          });
          
          const userEmail = profile.emails[0].value;
          
          // Access control checks
          const allowedEmails = process.env.ALLOWED_EMAILS?.split(',').map(e => e.trim()) || [];
          const restrictedDomain = process.env.RESTRICTED_DOMAIN;
          
          // Check domain restriction
          if (restrictedDomain && !userEmail.endsWith(`@${restrictedDomain}`)) {
            return done(null, false, { message: 'Access restricted to company accounts' });
          }
          
          // Check if user exists
          let user = await prisma.users.findUnique({
            where: { email: userEmail },
          });

          if (!user) {
            // Create new user
            user = await prisma.users.create({
              data: {
                email: userEmail,
                name: profile.displayName,
                google_id: profile.id,
                profile_picture: profile.photos[0]?.value,
                created_at: new Date(),
                is_whitelisted: allowedEmails.includes(userEmail),
              },
            });
          } else {
            // Update existing user
            user = await prisma.users.update({
              where: { id: user.id },
              data: {
                google_id: profile.id,
                name: profile.displayName,
                profile_picture: profile.photos[0]?.value,
                is_whitelisted: allowedEmails.includes(userEmail),
              },
            });
          }

          // Store tokens if needed for future Google API access
          user.accessToken = accessToken;
          user.refreshToken = refreshToken;

          return done(null, user);
        } catch (error) {
          return done(error, null);
        }
      }
    )
  );

  // Serialize user for session
  passport.serializeUser((user, done) => {
    done(null, user.id);
  });

  // Deserialize user from session
  passport.deserializeUser(async (id, done) => {
    try {
      const user = await prisma.users.findUnique({
        where: { id },
      });
      done(null, user);
    } catch (error) {
      done(error, null);
    }
  });
};

export default configureGoogleStrategy;