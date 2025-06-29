# Google OAuth Setup for EspressoBot

This guide walks you through setting up Google OAuth for EspressoBot.

## Prerequisites

- Google Cloud Console account
- Access to your Google Workspace (if using workspace accounts)

## Steps

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note down your project ID

### 2. Enable Google+ API

1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "Google+ API"
3. Click on it and press "Enable"

### 3. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen first:
   - Choose "Internal" for Google Workspace users only
   - Choose "External" for any Google account
   - Fill in the required fields
   - Add your email to test users if using External

4. For the OAuth client:
   - Application type: "Web application"
   - Name: "EspressoBot"
   - Authorized JavaScript origins:
     - `http://localhost:5173` (for development)
     - Your production URL (when deployed)
   - Authorized redirect URIs:
     - `http://localhost:5173/api/auth/google/callback` (for development)
     - `https://your-domain.com/api/auth/google/callback` (for production)

5. Click "Create" and note down:
   - Client ID
   - Client Secret

### 4. Configure EspressoBot

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update the following variables in `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id-here
   GOOGLE_CLIENT_SECRET=your-client-secret-here
   GOOGLE_CALLBACK_URL=http://localhost:5173/api/auth/google/callback
   ```

3. Generate secure secrets for sessions and JWT:
   ```bash
   # Generate a secure session secret
   openssl rand -base64 32
   
   # Generate a secure JWT secret
   openssl rand -base64 32
   ```

4. Update `.env` with the generated secrets:
   ```env
   SESSION_SECRET=your-generated-session-secret
   JWT_SECRET=your-generated-jwt-secret
   ```

### 5. Update Database Schema

The database schema has been updated to support Google OAuth. The users table now includes:
- `google_id`: Unique Google user ID
- `profile_picture`: URL to user's Google profile picture
- `password_hash`: Now optional (for OAuth users)

### 6. Test the Setup

1. Start the development server:
   ```bash
   npm run dev
   ```

2. Navigate to http://localhost:5173
3. You should see the login page
4. Click "Sign in with Google"
5. Complete the OAuth flow
6. You should be redirected back and logged in

## Troubleshooting

### "Access blocked" error
- Make sure you've added your email to test users in the OAuth consent screen
- Verify the redirect URI matches exactly

### "Invalid client" error
- Double-check your client ID and secret in `.env`
- Ensure there are no extra spaces or quotes

### Session issues
- Make sure `SESSION_SECRET` is set and consistent
- Check that cookies are enabled in your browser

## Production Deployment

When deploying to production:

1. Update the authorized redirect URIs in Google Cloud Console
2. Update `GOOGLE_CALLBACK_URL` in your production environment
3. Set `NODE_ENV=production`
4. Use HTTPS for all URLs
5. Set `secure: true` for session cookies (already configured)