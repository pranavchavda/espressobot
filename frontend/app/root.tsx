import { json, LoaderFunctionArgs, MetaFunction } from '@remix-run/node';
import {
  Links,
  LiveReload,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
  useLoaderData,
  Form // For logout
} from '@remix-run/react';

import { getCurrentUser } from './lib/auth.server'; // Assuming auth.server.ts is in app/lib/
import { SidebarLayout } from '../src/components/common/sidebar-layout'; // Path to existing component
import UserProfileDropdown from '../src/components/common/UserProfileDropdown'; // Path to existing component
import { NavLink } from 'react-router-dom'; // For navbar links
import logo from '../src/static/EspressoBotLogo.png'; // Path to logo
// Import global styles if you have them, e.g., from index.css
// For Vite, styles are usually imported in main.jsx, ensure they are applied globally.
// For Remix, you might link them in the Links function or import directly in root.
// For now, assume index.css from src/ is handled by Vite's setup.

export const meta: MetaFunction = () => ([ // Updated syntax for Remix v2+
  { charset: 'utf-8' },
  { title: 'EspressoBot Remix' },
  { name: 'viewport', content: 'width=device-width,initial-scale=1' },
]);

export async function loader({ request }: LoaderFunctionArgs) {
  const user = await getCurrentUser(request);
  // Return user and ENV vars needed by client (if any, carefully chosen)
  return json({ user }); 
}

export default function App() {
  const { user } = useLoaderData<typeof loader>();

  // Simplified navbar for now
  const navbarContent = (
    <div className="flex justify-between items-center w-full py-2">
      <div className="flex items-center">
        <NavLink to="/">
          <img 
            src={logo} // Make sure this path is resolvable or import correctly
            alt="EspressoBot Logo" 
            className="h-8 ml-2 mr-2"
          />
        </NavLink>
      </div>
      <div className="flex items-center space-x-4">
        <NavLink 
          to="/about" 
          className={({ isActive }) => 
            `px-3 py-2 text-sm font-medium rounded-md transition-colors ${
              isActive 
                ? 'text-indigo-600 dark:text-indigo-400' 
                : 'text-zinc-700 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white'
            }`
          }
        >
          About
        </NavLink>
        {/* Add other nav links like /profile, /tasks if user is logged in */}
        {user && (
          <>
            <NavLink to="/profile" className={({ isActive }) => `px-3 py-2 text-sm font-medium rounded-md transition-colors ${isActive ? 'text-indigo-600 dark:text-indigo-400' : 'text-zinc-700 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white'}`}>Profile</NavLink>
            <NavLink to="/tasks" className={({ isActive }) => `px-3 py-2 text-sm font-medium rounded-md transition-colors ${isActive ? 'text-indigo-600 dark:text-indigo-400' : 'text-zinc-700 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white'}`}>Tasks</NavLink>
          </>
        )}
      </div>
    </div>
  );

  // Simplified sidebar content for now
  // Conversation list and "new chat" button will be added back progressively
  const sidebarContent = user ? (
    <div className="flex flex-col h-[93vh] sm:h-full">
      <p className="p-4 text-zinc-400">Conversations (coming soon)</p>
      <div className="mt-auto"> {/* Pushes UserProfileDropdown to the bottom */}
        <UserProfileDropdown user={user} onLogout={() => { /* Logout handled by Form */ }} />
         {/* Actual logout will be a Remix Form pointing to /logout action */}
        <Form method="post" action="/logout" className="p-4">
          <button type="submit" className="w-full text-left px-3 py-2 text-sm font-medium rounded-md text-zinc-700 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white hover:bg-zinc-100 dark:hover:bg-zinc-800">
            Logout
          </button>
        </Form>
      </div>
    </div>
  ) : (
    <div className="p-4 text-zinc-400">Please log in to see conversations.</div>
  );


  return (
    <html lang="en" className={user ? 'h-full' : 'h-full'}> {/* Ensure html and body take full height */}
      <head>
        <Meta />
        <Links />
      </head>
      <body className={user ? 'h-full bg-white dark:bg-zinc-900' : 'h-full bg-zinc-100 dark:bg-zinc-900'}>
        {user ? (
          <SidebarLayout
            className="" // Add any necessary global classes
            navbar={navbarContent}
            sidebar={sidebarContent}
          >
            <Outlet /> {/* Child routes will render here */}
          </SidebarLayout>
        ) : (
          // If no user, render a simpler layout or just Outlet for login/register pages
          // This ensures login/register pages don't try to render SidebarLayout
          <div className="flex flex-col items-center justify-center min-h-screen bg-zinc-100 dark:bg-zinc-900">
            <Outlet /> {/* For /login, /register routes */}
          </div>
        )}
        <ScrollRestoration />
        <Scripts />
        <LiveReload />
      </body>
    </html>
  );
}

// ErrorBoundary (optional but good practice for root)
export function ErrorBoundary() { // Updated: remove ({ error })
  // const error = useRouteError(); // Use this hook to get the error
  // console.error(error);
  // For now, a simple error message. Can be more sophisticated.
  // Need to import useRouteError from '@remix-run/react'
  return (
    <html>
      <head>
        <title>Oh no!</title>
        <Meta />
        <Links />
      </head>
      <body>
        <h1>App Error</h1>
        <p>Something went wrong.</p>
        {/* <pre>{error.message || JSON.stringify(error)}</pre> */}
        <Scripts />
      </body>
    </html>
  );
}
