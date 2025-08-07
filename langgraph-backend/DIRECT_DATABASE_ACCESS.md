# Direct Database Access Migration

This document describes the migration of Google Workspace and GA4 agents from using an auth bridge/proxy to direct PostgreSQL database access.

## Changes Made

### 1. Database Model Updates

Added `ga4_property_id` field to the `User` model in `/app/database/models.py`:
```python
# GA4 Analytics configuration  
ga4_property_id = Column(String(255))
```

### 2. Google Workspace Agent (`google_workspace_native_mcp.py`)

- Removed dependency on `GoogleAuthHelper` and auth bridge
- Updated all `_get_google_credentials()` methods to directly query the database
- Added proper token refresh handling with database updates
- Improved error handling and logging

### 3. GA4 Analytics Agent (`ga4_analytics_native_mcp.py`)

- Removed dependency on `GoogleAuthHelper` and auth bridge  
- Updated all `_get_ga4_credentials()` methods to directly query the database
- Added support for user-specific GA4 property IDs (falls back to environment variable)
- Added proper token refresh handling with database updates
- Updated initialization checks and error messages

## Database Schema

The unified database schema now includes:

```sql
-- Users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    -- Google OAuth tokens
    google_access_token TEXT,
    google_refresh_token TEXT, 
    google_token_expiry TIMESTAMP,
    
    -- GA4 configuration
    ga4_property_id VARCHAR(255)
);
```

## Migration Steps

### 1. Add New Database Column

Run the migration script to add the `ga4_property_id` column:

```bash
cd langgraph-backend
python migrate_ga4_column.py
```

### 2. Update Environment Variables

Make sure these environment variables are set:
- `DATABASE_URL` - PostgreSQL connection URL (e.g., `postgresql://user:pass@node.idrinkcoffee.info/espressobot`)
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret
- `GA4_PROPERTY_ID` - (Optional) Global GA4 property ID fallback

### 3. User Data Migration

For each user, ensure they have:
- `google_access_token` - Valid Google OAuth access token
- `google_refresh_token` - Google OAuth refresh token
- `google_token_expiry` - Token expiration timestamp
- `ga4_property_id` - (Optional) User-specific GA4 property ID

## Benefits

1. **Simplified Architecture**: No more auth bridge/proxy dependency
2. **Better Performance**: Direct database queries are faster than HTTP calls
3. **Unified Data**: Both frontend and backend use the same database
4. **User-Specific Configuration**: Each user can have their own GA4 property ID
5. **Improved Error Handling**: Better token refresh and error recovery
6. **Reduced Complexity**: Fewer moving parts and dependencies

## Authentication Flow

1. User authenticates via Google OAuth (handled by frontend)
2. Frontend stores tokens in PostgreSQL users table
3. Agents directly query database for user tokens
4. Agents automatically refresh expired tokens and update database
5. All Google API calls use fresh tokens

## Error Handling

The agents now handle these scenarios gracefully:
- Missing user authentication
- Expired tokens (automatic refresh)
- Invalid refresh tokens
- Missing GA4 property ID configuration
- Database connection errors
- Google API errors

## Testing

To test the migration:

1. Ensure a user has valid Google tokens in the database
2. Make requests to Google Workspace agent (Gmail, Calendar, etc.)
3. Make requests to GA4 Analytics agent
4. Verify tokens are refreshed automatically when expired
5. Check database for updated token values after refresh

## Rollback

If needed to rollback:
1. Restore the original agent files with `GoogleAuthHelper` dependency
2. Restart the auth bridge/proxy service
3. Update environment variables to point to auth proxy