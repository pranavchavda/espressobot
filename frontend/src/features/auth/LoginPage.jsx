import React from 'react';
import { Form, Link, useActionData, useNavigation } from '@remix-run/react';
import { Button } from '@common/button';
import { Text } from '@common/text';
import logo from '../../../static/EspressoBotLogo.png';

function LoginPage({ mode = 'login' }) {
  const actionData = useActionData();
  const navigation = useNavigation();
  const isLoading = navigation.state === 'submitting';
  const isRegisterMode = mode === 'register';

  return (
    <div className="flex items-center justify-center h-screen bg-zinc-100 dark:bg-zinc-900">
      <div className="p-8 bg-white dark:bg-zinc-800 rounded-lg shadow-xl w-full max-w-md">
        <img 
          src={logo}
          alt="EspressoBot Logo" 
          className="h-16 mx-auto"
        />
        <Text as="h2" className="text-2xl font-bold text-center text-zinc-900 dark:text-zinc-100 mb-6">
          {isRegisterMode ? 'EspressoBot Register' : 'EspressoBot Login'}
        </Text>
        <Form method="post" className="space-y-6">
          {!isRegisterMode && <input type="hidden" name="redirectTo" value="/" />}
          {/* The intent can be inferred from the route, but explicit `intent` can be useful for combined actions later */}
          {/* <input type="hidden" name="intent" value={mode} /> */}
          
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
                // required // Keep required if your action logic expects it for registration
                className="w-full px-4 py-3 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-shopify-purple dark:bg-zinc-700 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none transition-shadow duration-150 ease-in-out"
                placeholder="Your Name"
                disabled={isLoading}
              />
              {actionData?.errors?.name && (
                <Text className="text-red-500 dark:text-red-400 text-xs pt-1">
                  {actionData.errors.name}
                </Text>
              )}
            </div>
          )}

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
              className="w-full px-4 py-3 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-shopify-purple dark:bg-zinc-700 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none transition-shadow duration-150 ease-in-out"
              placeholder="you@example.com"
              disabled={isLoading}
            />
            {actionData?.errors?.email && (
              <Text className="text-red-500 dark:text-red-400 text-xs pt-1">
                {actionData.errors.email}
              </Text>
            )}
          </div>

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
              className="w-full px-4 py-3 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-shopify-purple dark:bg-zinc-700 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 focus:outline-none transition-shadow duration-150 ease-in-out"
              placeholder="••••••••"
              disabled={isLoading}
            />
            {actionData?.errors?.password && (
              <Text className="text-red-500 dark:text-red-400 text-xs pt-1">
                {actionData.errors.password}
              </Text>
            )}
          </div>
          
          {/* Display general error message (e.g. from login for non-whitelisted user) */}
          {actionData?.errors && typeof actionData.errors === 'string' && (
            <Text className="text-red-500 dark:text-red-400 text-sm text-center">
              {actionData.errors}
            </Text>
          )}
          {/* Display success message (e.g. from registration) */}
          {actionData?.message && (
            <Text className="text-green-500 dark:text-green-400 text-sm text-center">
              {actionData.message}
            </Text>
          )}

          <Button 
            type="submit" 
            className="w-full bg-shopify-purple hover:bg-shopify-purple-dark text-white font-semibold py-3 rounded-lg transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-shopify-purple focus:ring-offset-2 dark:focus:ring-offset-zinc-800 disabled:opacity-70"
            disabled={isLoading}
          >
            {isLoading ? (isRegisterMode ? 'Registering...' : 'Logging in...') : (isRegisterMode ? 'Register' : 'Login')}
          </Button>
        </Form>
        <Text className="mt-6 text-center text-sm">
          {isRegisterMode ? 'Already have an account?' : "Don't have an account?"}{" "}
          <Link 
            to={isRegisterMode ? '/login' : '/register'}
            className="font-medium text-shopify-purple hover:text-shopify-purple-dark focus:outline-none focus:underline"
          >
            {isRegisterMode ? 'Login' : 'Register'}
          </Link>
        </Text>
      </div>
    </div>
  );
}

export default LoginPage;
