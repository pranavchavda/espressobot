import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Button } from '@common/button';
import { Text } from '@common/text';
import { Badge } from '@common/badge';
import logo from '../../static/EspressoBotLogo.png';

function CLIAuthPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [cliToken, setCLIToken] = useState('');
  const [authComplete, setAuthComplete] = useState(false);
  const [user, setUser] = useState(null);

  const provider = searchParams.get('provider') || 'google';
  const isCLI = searchParams.get('cli') === 'true';

  useEffect(() => {
    if (!isCLI) {
      // Redirect to normal login if not CLI request
      navigate('/auth/login');
      return;
    }

    // Check if there's a token in the URL (from OAuth callback)
    const urlParams = new URLSearchParams(window.location.search);
    const tokenFromUrl = urlParams.get('token') || urlParams.get('access_token');
    
    if (tokenFromUrl) {
      // Token found in URL, display it
      setCLIToken(tokenFromUrl);
      setAuthComplete(true);
      
      // Try to extract user info from token
      try {
        const tokenPayload = JSON.parse(atob(tokenFromUrl.split('.')[1]));
        setUser({
          email: tokenPayload.email || 'Unknown',
          name: tokenPayload.name || 'User'
        });
      } catch (e) {
        console.log('Could not parse token payload');
      }
      
      return;
    }

    // Check if user is already authenticated
    checkAuthStatus();
  }, [isCLI, navigate]);

  const checkAuthStatus = async () => {
    try {
      // First, try to get token from localStorage immediately
      const authToken = localStorage.getItem('authToken');
      if (authToken) {
        setCLIToken(authToken);
        setAuthComplete(true);
        
        // Try to decode user info from JWT
        try {
          const tokenPayload = JSON.parse(atob(authToken.split('.')[1]));
          setUser({
            email: tokenPayload.email || 'Unknown',
            name: tokenPayload.name || 'User'
          });
        } catch (e) {
          console.log('Could not parse token payload, checking API...');
        }
        
        return; // Token found, we're done
      }

      // If no token in localStorage, check with API
      const response = await fetch('/api/auth/user', {
        credentials: 'include'
      });
      
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        // Try other token sources if localStorage didn't work
        await generateCLITokenFromAuth();
      }
    } catch (error) {
      console.log('Not authenticated yet');
    }
  };

  const generateCLITokenFromAuth = async () => {
    try {
      // Get the JWT token from localStorage (where the web app stores it)
      const authToken = localStorage.getItem('authToken');
      
      if (authToken) {
        // Use the existing JWT token as CLI token
        setCLIToken(authToken);
        setAuthComplete(true);
        console.log('Using existing JWT token for CLI authentication');
      } else {
        // Try other possible token storage locations
        const altToken = localStorage.getItem('access_token') || 
                        localStorage.getItem('token') ||
                        sessionStorage.getItem('authToken') ||
                        sessionStorage.getItem('access_token');
        
        if (altToken) {
          setCLIToken(altToken);
          setAuthComplete(true);
          console.log('Found token in alternative storage');
        } else {
          console.log('No stored token found, user needs to authenticate');
          // Don't automatically trigger login, let user click the button
        }
      }
    } catch (error) {
      console.error('Error generating CLI token:', error);
    }
  };

  const handleGoogleLogin = async () => {
    setLoading(true);
    setError('');

    try {
      // Initiate Google OAuth with CLI callback flag
      window.location.href = `/api/auth/google?cli=true&redirect=${encodeURIComponent(window.location.href)}`;
    } catch (error) {
      setError('Failed to initiate Google login');
      setLoading(false);
    }
  };

  const generateCLIToken = async () => {
    try {
      const response = await fetch('/api/auth/cli/generate-token', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setCLIToken(data.cli_token);
        setAuthComplete(true);
      } else {
        setError('Failed to generate CLI token');
      }
    } catch (error) {
      setError('Failed to generate CLI token');
    }
  };

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(cliToken);
      // Could add a toast notification here
    } catch (error) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = cliToken;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  };

  if (!isCLI) {
    return null; // Redirecting
  }

  return (
    <div className="flex items-center justify-center min-h-screen bg-zinc-100 dark:bg-zinc-900 p-4">
      <div className="p-8 bg-white dark:bg-zinc-800 rounded-lg shadow-xl w-full max-w-md">
        <img 
          src={logo}
          alt="EspressoBot Logo" 
          className="h-16 mx-auto mb-4"
        />
        
        <div className="text-center mb-6">
          <Text as="h2" className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
            CLI Authentication
          </Text>
          <Badge color="blue" className="mt-2">
            Command Line Interface
          </Badge>
        </div>

        {!authComplete ? (
          <div className="space-y-6">
            <Text className="text-zinc-600 dark:text-zinc-400 text-center">
              Authenticate with {provider.charAt(0).toUpperCase() + provider.slice(1)} to use EspressoBot CLI features like email, calendar, and analytics.
            </Text>

            {error && (
              <Text className="text-red-500 dark:text-red-400 text-sm text-center bg-red-50 dark:bg-red-900/20 p-3 rounded">
                {error}
              </Text>
            )}

            <Button 
              onClick={handleGoogleLogin}
              disabled={loading}
              className="w-full bg-shopify-purple hover:bg-shopify-purple-dark text-white font-semibold py-3 rounded-lg transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-shopify-purple focus:ring-offset-2 dark:focus:ring-offset-zinc-800 disabled:opacity-70"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Connecting to Google...
                </div>
              ) : (
                `Continue with ${provider.charAt(0).toUpperCase() + provider.slice(1)}`
              )}
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <Text as="h3" className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 mb-2">
                Authentication Successful!
              </Text>
              {user && (
                <Text className="text-zinc-600 dark:text-zinc-400 mb-4">
                  Logged in as {user.email}
                </Text>
              )}
            </div>

            <div className="bg-zinc-50 dark:bg-zinc-700 p-4 rounded-lg">
              <Text className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
                CLI Token:
              </Text>
              <div className="flex items-center space-x-2">
                <code className="flex-1 bg-zinc-100 dark:bg-zinc-600 text-zinc-800 dark:text-zinc-200 px-3 py-2 rounded text-sm font-mono break-all">
                  {cliToken}
                </code>
                <Button 
                  onClick={copyToClipboard}
                  size="sm"
                  className="bg-zinc-600 hover:bg-zinc-700 text-white"
                >
                  Copy
                </Button>
              </div>
            </div>

            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-4 rounded-lg">
              <Text className="text-blue-800 dark:text-blue-200 text-sm">
                <strong>Instructions:</strong><br/>
                1. Copy the CLI token above<br/>
                2. Return to your terminal<br/>
                3. Paste the token when prompted<br/>
                4. You can now use Google services in the CLI!
              </Text>
            </div>

            <Button 
              onClick={() => window.close()}
              className="w-full bg-zinc-600 hover:bg-zinc-700 text-white"
            >
              Close Window
            </Button>
          </div>
        )}

        <Text className="mt-6 text-center text-xs text-zinc-500 dark:text-zinc-400">
          This authentication is for CLI access only. Your credentials are stored securely.
        </Text>
      </div>
    </div>
  );
}

export default CLIAuthPage;