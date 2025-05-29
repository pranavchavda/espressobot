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

import { getCurrentUser } from './lib/auth.server';
import { prisma } from './lib/db.server'; // For fetching conversations
import { SidebarLayout } from '../src/components/common/sidebar-layout';
import UserProfileDropdown from '../src/components/common/UserProfileDropdown';
import { NavLink } from '@remix-run/react'; // Corrected import for NavLink in Remix context
import logo from '../src/static/EspressoBotLogo.png';
import { PWAInstallPrompt } from '../src/components/common/PWAInstallPrompt.jsx'; // Import PWAInstallPrompt
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
  if (user) {
    const conversations = await prisma.conversation.findMany({
      where: { userId: user.id },
      orderBy: { createdAt: 'desc' },
      select: { id: true, title: true, createdAt: true },
    });
    return json({ user, conversations });
  }
  return json({ user: null, conversations: [] }); 
}

export default function App() {
  const { user, conversations } = useLoaderData<typeof loader>();

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
    <div className="flex flex-col h-full"> {/* Use h-full for flex container */}
      <div className="p-4">
        <NavLink 
          to="/" 
          className="block w-full text-center px-4 py-2 text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 mb-4"
        >
          New Chat
        </NavLink>
      </div>
      <div className="flex-grow overflow-y-auto px-2 space-y-1"> {/* Scrollable conversation list */}
        {conversations.length === 0 ? (
          <p className="p-4 text-zinc-400 text-sm">No conversations yet.</p>
        ) : (
          conversations.map(chat => (
            <div key={chat.id} className="group flex items-center justify-between p-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800">
              <NavLink 
                to={`/c/${chat.id}`} 
                className={({ isActive }) => 
                  `flex-grow text-sm truncate ${isActive ? 'text-indigo-600 dark:text-indigo-400 font-semibold' : 'text-zinc-700 dark:text-zinc-300'}`
                }
                title={chat.title}
              >
                {chat.title}
                 {/* Optional: Display date in a subtle way */}
                 {/* <span className="text-xs text-zinc-400 ml-2">{new Date(chat.createdAt).toLocaleDateString()}</span> */}
              </NavLink>
              <Form method="delete" action={`/conversations/${chat.id}`} onSubmit={(event) => { if(!confirm('Are you sure you want to delete this conversation?')) event.preventDefault(); }}>
                <button 
                  type="submit" 
                  className="ml-2 p-1 text-zinc-400 hover:text-red-500 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                  title="Delete conversation"
                >
                  {/* Using a simple X for now, replace with an icon later */}
                  X 
                </button>
              </Form>
            </div>
          ))
        )}
      </div>
      <div className="mt-auto border-t border-zinc-200 dark:border-zinc-700"> {/* Pushes UserProfileDropdown and Logout to the bottom */}
        <div className="p-2"> {/* Reduced padding for UserProfileDropdown container */}
          <UserProfileDropdown user={user} onLogout={() => { /* Logout handled by Form */ }} />
        </div>
        <Form method="post" action="/logout" className="p-4 pt-0"> {/* Reduced top padding for logout form */}
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
        <PWAInstallPrompt /> {/* Add the component here */}
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
