// Example Frontend Integration for Google OAuth Authentication Bridge
// This shows how the frontend can push tokens to the backend auth proxy

/**
 * Store Google OAuth tokens in backend auth proxy cache
 * Call this after successful Google OAuth flow in frontend
 */
async function storeGoogleTokens(userId, googleTokens) {
    try {
        const response = await fetch('/api/auth/store-tokens', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: userId,
                tokens: {
                    access_token: googleTokens.access_token,
                    refresh_token: googleTokens.refresh_token,
                    token_expiry: googleTokens.expiry_date ? new Date(googleTokens.expiry_date).toISOString() : null,
                    scopes: googleTokens.scope ? googleTokens.scope.split(' ') : []
                },
                ttl_seconds: 3600 // Cache for 1 hour
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('✅ Tokens stored in backend cache:', result.message);
            return true;
        } else {
            console.error('❌ Failed to store tokens:', result.message);
            return false;
        }
    } catch (error) {
        console.error('❌ Error storing tokens:', error);
        return false;
    }
}

/**
 * Example Google OAuth flow integration
 */
function handleGoogleSignIn() {
    // Initialize Google OAuth
    gapi.load('auth2', () => {
        gapi.auth2.init({
            client_id: 'your-google-client-id.apps.googleusercontent.com'
        }).then(() => {
            const authInstance = gapi.auth2.getAuthInstance();
            
            authInstance.signIn({
                scope: [
                    'https://www.googleapis.com/auth/gmail.readonly',
                    'https://www.googleapis.com/auth/gmail.send',
                    'https://www.googleapis.com/auth/calendar',
                    'https://www.googleapis.com/auth/drive.readonly',
                    'https://www.googleapis.com/auth/tasks',
                    'https://www.googleapis.com/auth/analytics.readonly'
                ].join(' ')
            }).then(async (googleUser) => {
                const authResponse = googleUser.getAuthResponse();
                const profile = googleUser.getBasicProfile();
                
                // Get or create user in your system
                const userId = await getCurrentUserId(); // Your user management logic
                
                // Store tokens in backend auth proxy
                const stored = await storeGoogleTokens(userId, authResponse);
                
                if (stored) {
                    console.log('✅ Google authentication complete!');
                    // Now backend agents can access Google APIs seamlessly
                } else {
                    console.error('❌ Failed to complete authentication setup');
                }
            });
        });
    });
}

/**
 * Check authentication status
 */
async function checkGoogleAuthStatus(userId) {
    try {
        const response = await fetch(`/api/auth/get-tokens/${userId}`);
        const result = await response.json();
        
        return {
            isAuthenticated: result.success && result.tokens,
            source: result.source, // 'cache' or 'database'
            tokens: result.tokens
        };
    } catch (error) {
        console.error('Error checking auth status:', error);
        return { isAuthenticated: false };
    }
}

/**
 * Revoke Google authentication
 */
async function revokeGoogleAuth(userId) {
    try {
        const response = await fetch(`/api/auth/revoke-tokens/${userId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.success) {
            console.log('✅ Google authentication revoked');
            return true;
        } else {
            console.error('❌ Failed to revoke authentication:', result.message);
            return false;
        }
    } catch (error) {
        console.error('Error revoking auth:', error);
        return false;
    }
}

/**
 * Example usage in a React component
 */
const GoogleAuthComponent = () => {
    const [authStatus, setAuthStatus] = useState(null);
    const userId = getCurrentUserId(); // Your user management logic
    
    useEffect(() => {
        checkGoogleAuthStatus(userId).then(setAuthStatus);
    }, [userId]);
    
    const handleSignIn = () => {
        handleGoogleSignIn();
    };
    
    const handleSignOut = async () => {
        await revokeGoogleAuth(userId);
        setAuthStatus({ isAuthenticated: false });
    };
    
    return (
        <div>
            <h3>Google Workspace Integration</h3>
            {authStatus?.isAuthenticated ? (
                <div>
                    <p>✅ Connected to Google Workspace</p>
                    <p>Token source: {authStatus.source}</p>
                    <button onClick={handleSignOut}>Disconnect</button>
                </div>
            ) : (
                <div>
                    <p>❌ Not connected to Google Workspace</p>
                    <button onClick={handleSignIn}>Connect Google Account</button>
                </div>
            )}
        </div>
    );
};

// Helper function - implement based on your user management
async function getCurrentUserId() {
    // Return current user's ID from your auth system
    // This could come from JWT token, session, etc.
    return 1; // placeholder
}
