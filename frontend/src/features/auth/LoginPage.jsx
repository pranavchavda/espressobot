import React, { useState } from 'react';
import { Button } from '@common/button';
// import { Textarea } from '@common/textarea'; // Using a simpler input for password
import { Text } from '@common/text';

function LoginPage({ onLogin, error, loading }) {
  const [password, setPassword] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!loading) {
      onLogin(password);
    }
  };

  return (
    <div className="flex items-center justify-center h-screen bg-zinc-100 dark:bg-zinc-900">
      <div className="p-8 bg-white dark:bg-zinc-800 rounded-lg shadow-xl w-full max-w-md">
        <Text as="h2" className="text-2xl font-bold text-center text-zinc-900 dark:text-zinc-100 mb-6">
          Password Required
        </Text>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full px-4 py-3 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-shopify-purple dark:bg-zinc-700 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none transition-shadow duration-150 ease-in-out"
              autoFocus
              required
              disabled={loading}
            />
          </div>
          {error && (
            <Text className="text-red-500 dark:text-red-400 text-sm mb-4 text-center">
              {error}
            </Text>
          )}
          <Button 
            type="submit" 
            className="w-full bg-shopify-purple hover:bg-shopify-purple-dark text-white font-semibold py-3 rounded-lg transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-shopify-purple focus:ring-offset-2 dark:focus:ring-offset-zinc-800 disabled:opacity-70"
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
