# Google OAuth Setup Instructions

## Problem
The "invalid_client" error occurs because the Google OAuth credentials are not properly configured.

## Current Status
- `.env` file has placeholder values:
  - `GOOGLE_CLIENT_ID=your_google_client_id`
  - `GOOGLE_CLIENT_SECRET=your_google_client_secret`

## Steps to Fix

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing "EspressoBot" project
3. Enable APIs:
   - Gmail API
   - Google Calendar API
   - Google Drive API
   - Google Tasks API
   - Google Analytics Data API

4. Create OAuth 2.0 Credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Web application"
   - Name: "EspressoBot"
   - Authorized JavaScript origins:
     - `http://localhost:5173`
     - `http://localhost:3000`
   - Authorized redirect URIs:
     - `http://localhost:5173/auth/google/callback`
     - `http://localhost:3000/auth/google/callback`
   - Click "Create"

5. Download the credentials and copy:
   - Client ID
   - Client Secret

### 2. Update Environment Variables

Update the `.env` file with real credentials:

```bash
GOOGLE_CLIENT_ID=your_actual_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_actual_client_secret_here
```

### 3. For GA4 Analytics

Also set up:
```bash
GA4_PROPERTY_ID=your_ga4_property_id  # e.g., 325181275
```

### 4. Restart Services

After updating `.env`:
```bash
# Restart backend
pkill -f "uvicorn app.main:app"
cd /home/pranav/espressobot/langgraph-backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Restart frontend
cd /home/pranav/espressobot/frontend
npm run dev
```

## Alternative: Bypass OAuth for Testing

For testing without OAuth, you can:
1. Use the API directly via curl/test scripts
2. Create a test user with pre-configured tokens
3. Use a mock authentication mode

## Router Agent Fix

The router agent issue is separate. The router exists but may need priority adjustments to ensure specialized agents handle appropriate queries before the general agent.

Check:
- `/home/pranav/espressobot/langgraph-backend/app/agents/router.py`
- `/home/pranav/espressobot/langgraph-backend/app/orchestrator.py`

The router should prioritize specialized agents for domain-specific queries.