import React from 'react';
import { Button } from '@common/button';
import logo from '../../static/EspressoBotLogo.png';

const LoginPage = () => {
  const handleGoogleLogin = () => {
    // Clear any stale auth data before login
    localStorage.removeItem('authToken');
    
    // For Vivaldi browser, use replace instead of href
    const isVivaldi = navigator.userAgent.includes('Vivaldi');
    if (isVivaldi) {
      window.location.replace('/api/auth/google');
    } else {
      window.location.href = '/api/auth/google';
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-900">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <img
            className="mx-auto h-24 w-auto"
            src={logo}
            alt="EspressoBot"
          />
          <h2 className="mt-6 text-3xl font-extrabold text-zinc-900 dark:text-zinc-100">
            Welcome to EspressoBot
          </h2>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            iDrinkCoffee.com's E-commerce Assistant
          </p>
        </div>
        <div className="mt-8 space-y-6">
          <div>
            <Button
              onClick={handleGoogleLogin}
              className="group relative w-full flex justify-center items-center cursor-pointer"
              
            >
              <svg
                className="w-5 h-5 mr-2"
                viewBox="0 0 24 24"
                fill="currentColor"
              >
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Sign in with Google
            </Button>
            <p className="mt-4 text-center text-xs text-zinc-500 dark:text-zinc-400">
              Sign in with your iDrinkCoffee.com Google Workspace account
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;