import React, { useState, useEffect } from 'react';
import { Button } from '@common/button';
import { Text } from '@common/text';

function LoginPage({ onLogin, onRegister, error, loading }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isRegisterMode, setIsRegisterMode] = useState(false);

  // Clear error when switching modes or when component loads with an error
  useEffect(() => {
    if (error) {
      // This is a simple way to clear error, App.jsx's setAuthError(null) in handlers is more robust
      // Consider if App.jsx should clear error more explicitly on mode switch via a callback if needed
    }
  }, [isRegisterMode, error]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (loading) return;

    if (isRegisterMode) {
      onRegister(email, password, name);
    } else {
      onLogin(email, password);
    }
  };

  const toggleMode = () => {
    setIsRegisterMode(!isRegisterMode);
    setEmail('');
    setPassword('');
    setName('');
    // Error is managed by App.jsx, it should clear it when a new action starts
  };

  return (
    <div className="flex items-center justify-center h-screen bg-zinc-100 dark:bg-zinc-900">
      <div className="p-8 bg-white dark:bg-zinc-800 rounded-lg shadow-xl w-full max-w-md">
        <Text as="h2" className="text-2xl font-bold text-center text-zinc-900 dark:text-zinc-100 mb-6">
          {isRegisterMode ? 'Create Account' : 'Welcome Back'}
        </Text>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Email address
            </label>
            <input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-3 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-shopify-purple dark:bg-zinc-700 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none transition-shadow duration-150 ease-in-out"
              placeholder="you@example.com"
              disabled={loading}
            />
          </div>

          {isRegisterMode && (
            <div>
              <label htmlFor="name" className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
                Full name
              </label>
              <input
                id="name"
                name="name"
                type="text"
                autoComplete="name"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-4 py-3 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-shopify-purple dark:bg-zinc-700 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none transition-shadow duration-150 ease-in-out"
                placeholder="Your Name"
                disabled={loading}
              />
            </div>
          )}

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1">
              Password
            </label>
            <input
              id="password"
              name="password"
              type="password"
              autoComplete={isRegisterMode ? "new-password" : "current-password"}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-shopify-purple dark:bg-zinc-700 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none transition-shadow duration-150 ease-in-out"
              placeholder="••••••••"
              disabled={loading}
            />
          </div>

          {error && (
            <Text className="text-red-500 dark:text-red-400 text-sm text-center">
              {error}
            </Text>
          )}

          <Button 
            type="submit" 
            className="w-full bg-shopify-purple hover:bg-shopify-purple-dark text-white font-semibold py-3 rounded-lg transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-shopify-purple focus:ring-offset-2 dark:focus:ring-offset-zinc-800 disabled:opacity-70"
            disabled={loading}
          >
            {loading ? (isRegisterMode ? 'Registering...' : 'Logging in...') : (isRegisterMode ? 'Register' : 'Login')}
          </Button>
        </form>
        <Text className="mt-6 text-center text-sm">
          {isRegisterMode ? 'Already have an account?' : "Don't have an account?"}{" "}
          <button 
            onClick={toggleMode} 
            className="font-medium text-shopify-purple hover:text-shopify-purple-dark focus:outline-none focus:underline"
            disabled={loading}
          >
            {isRegisterMode ? 'Login' : 'Register'}
          </button>
        </Text>
      </div>
    </div>
  );
}

export default LoginPage;
