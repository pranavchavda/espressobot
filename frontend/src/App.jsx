// App: Root of the SPA, sets up layout and routing
import React, { useState, useEffect } from "react";
import { SidebarLayout } from "@common/sidebar-layout";
import { Button } from "@common/button";
import StreamingChatPage from "./features/chat/StreamingChatPage";
import LoginPage from "./features/auth/LoginPage"; // Import LoginPage
import ProfilePage from './pages/ProfilePage'; // Import ProfilePage
import AboutPage from './pages/AboutPage'; // Import AboutPage
import TasksPage from './pages/TasksPage'; // Import TasksPage
import { Routes, Route, Link, Outlet, NavLink } from "react-router-dom";
import { XIcon } from 'lucide-react'; // Import XIcon for the delete button
import logo from '../static/EspressoBotLogo.png';
import { PWAInstallPrompt } from './components/common/PWAInstallPrompt';

// const FLASK_API_BASE_URL = 'http://localhost:5000'; // Not strictly needed if using relative paths and proxy/same-origin

function App() {
  const [conversations, setConversations] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(true); // For conversations loading

  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authLoading, setAuthLoading] = useState(true); // Start with true for initial auth check
  const [authError, setAuthError] = useState(null);

  // Initial check for existing backend session
  useEffect(() => {
    const checkBackendAuth = async () => {
      try {
        const res = await fetch("/api/check_auth");
        if (res.ok) {
          const data = await res.json();
          if (data.isAuthenticated) {
            setIsAuthenticated(true);
          }
        }
        // If not res.ok or not data.isAuthenticated, user remains unauthenticated
      } catch (e) {
        console.error("Failed to check backend auth:", e);
        // User remains unauthenticated
      } finally {
        setAuthLoading(false); // Finished initial auth check
      }
    };
    checkBackendAuth();
  }, []);

  // Fetch conversations from Flask API
  const fetchConversations = async () => {
    setLoading(true);
    try {
      // Assuming '/conversations' will be proxied by Vite or is same-origin
      const res = await fetch("/conversations");
      const data = await res.json();
      setConversations(data); // Assumes data is the array of conversations
      // The previous code had 'data.conversations'. If Flask sends {conversations: []}, this should be data.conversations
      // For now, sticking to 'data' as per user-provided previous code.
      // Consider changing to setConversations(data.conversations || []) if Flask sends an object.
      const currentConversations = data.conversations || [];
      if (!selectedChat && currentConversations.length > 0) {
        setSelectedChat(currentConversations[0].id);
      }
    } catch (e) {
      console.error("Failed to fetch conversations (reverted):", e);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };

  // Call fetchConversations when component mounts or isAuthenticated changes
  useEffect(() => {
    if (isAuthenticated && !authLoading) { // Only fetch if authenticated and initial auth check is done
      fetchConversations();
    }
  }, [isAuthenticated, authLoading]);

  // Function to handle deleting a conversation
  const handleDeleteConversation = async (convIdToDelete) => {
    if (!convIdToDelete) return;

    // Optional: Add a confirmation dialog here
    // if (!window.confirm("Are you sure you want to delete this conversation?")) {
    //   return;
    // }

    try {
      const response = await fetch(`/conversations/${convIdToDelete}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Refresh the conversations list
        fetchConversations(); 
        // If the deleted chat was the selected one, clear selection
        if (selectedChat === convIdToDelete) {
          setSelectedChat(null);
        }
      } else {
        console.error("Failed to delete conversation:", response.statusText);
        // Optionally, show an error message to the user
        alert("Error deleting conversation. Please try again.");
      }
    } catch (error) {
      console.error("Error during delete request:", error);
      alert("An error occurred while trying to delete the conversation.");
    }
  };

  // handleLogin
  const handleLogin = async (email, password) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const response = await fetch("/api/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });
      const data = await response.json();
      if (response.ok) {
        setIsAuthenticated(true);
        // Optionally store user data from `data.user` into a currentUser state here
        // e.g., setCurrentUser(data.user);
        setSelectedChat(null); // Reset chat selection
      } else {
        setAuthError(data.error || "Login failed. Please try again.");
        setIsAuthenticated(false);
      }
    } catch (e) {
      console.error("Login API call failed:", e);
      setAuthError("Login failed due to a network or server error.");
      setIsAuthenticated(false);
    }
    setAuthLoading(false);
  };

  // handleRegister
  const handleRegister = async (email, password, name) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const response = await fetch("/api/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password, name }),
      });
      const data = await response.json();
      if (response.ok) {
        alert(data.message || "Registration successful! Please login."); 
      } else {
        setAuthError(data.error || "Registration failed. Please try again.");
      }
    } catch (e) {
      console.error("Register API call failed:", e);
      setAuthError("Registration failed due to a network or server error.");
    }
    setAuthLoading(false);
  };

  // handleLogout
  const handleLogout = async () => {
    try {
      await fetch("/api/logout", { method: "POST" });
    } catch (e) {
      console.error("Error during backend logout:", e);
      // Proceed with frontend logout anyway
    }
    setIsAuthenticated(false);
    setSelectedChat(null);
    setConversations([]);
    setAuthError(null);
    // Optionally, clear other states or redirect
  };

  // Conditional rendering based on authentication state
  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-zinc-100 dark:bg-zinc-900">
        <div className="text-xl text-zinc-700 dark:text-zinc-300">
          Loading...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <LoginPage
        onLogin={handleLogin}
        onRegister={handleRegister} // Pass the new handler
        error={authError}
        loading={authLoading} // This might need to be more granular (loginLoading, registerLoading)
                           // For now, a single `authLoading` covers both.
      />
    );
  }

  // User is authenticated, render the main app with sidebar layout
  return (
    <Routes>
      <Route element={
        <SidebarLayout
          className=""
          navbar={
            <div className="flex justify-between items-center w-full py-2">
              <div className="flex items-center">
              <NavLink to="/">
                <img 
                  src={logo}
                  alt="EspressoBot Logo" 
                  className="h-8 ml-2 mr-2"
                />
                </NavLink>
              </div>
              <div className="flex items-center space-x-4">
                <NavLink 
                  to="/profile" 
                  className={({ isActive }) => 
                    `px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      isActive 
                        ? 'text-indigo-600 dark:text-indigo-400' 
                        : 'text-zinc-700 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white'
                    }`
                  }
                >
                  Profile
                </NavLink>
                <NavLink 
                  to="/tasks" 
                  className={({ isActive }) => 
                    `px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      isActive 
                        ? 'text-indigo-600 dark:text-indigo-400' 
                        : 'text-zinc-700 hover:text-zinc-900 dark:text-zinc-300 dark:hover:text-white'
                    }`
                  }
                >
                  Tasks
                </NavLink>
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
                <Button
                  onClick={handleLogout}
                  variant="ghost"
                  className="px-3 py-1 text-sm"
                >
                  Logout
                </Button>
              </div>
            </div>
          }
          sidebar={
            <div className="flex flex-col h-full">
              <nav className="flex-1 overflow-y-auto">
                {loading ? (
                  <div className="text-zinc-400 px-4 py-2">Loading...</div>
                ) : (
                  <ul className="flex flex-col gap-1">
                    {conversations.map((chat) => (
                      <li key={chat.id} className="group relative pr-4">
                        <Link 
                          to="/" // Always link to home
                          className={`block w-full text-left px-4 py-3 rounded-lg transition-colors ${
                            selectedChat === chat.id 
                              ? "bg-zinc-200 dark:bg-zinc-800 font-semibold" 
                              : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
                          }`}
                          onClick={() => setSelectedChat(chat.id)}
                        >
                          <div className="truncate">{chat.title}</div>
                          <div className="text-xs text-zinc-500 truncate">
                            {chat.created_at
                              ? new Date(chat.created_at).toLocaleString()
                              : ""}
                          </div>
                        </Link>
                        <Button
                          variant="ghost"
                          size="iconSm"
                          className="absolute top-1/2 right-1 transform -translate-y-1/2 p-1 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            handleDeleteConversation(chat.id);
                          }}
                          aria-label="Delete conversation"
                        >
                          <XIcon className="h-4 w-4 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200" />
                        </Button>
                      </li>
                    ))}
                    {conversations.length === 0 && !loading && (
                      <li className="text-zinc-400 px-4 py-2">No conversations</li>
                    )}
                  </ul>
                )}
              </nav>
              <Link to="/" className="mb-4 mx-2">
                <Button 
                  className="w-full"
                  onClick={() => setSelectedChat(null)}
                >
                  + New Chat
                </Button>
              </Link>

            </div>
          }
        >
          <Outlet />
        </SidebarLayout>
      }>
        <Route
          path="/"
          element={
            <>
              <StreamingChatPage
                key={selectedChat === null ? "new_chat_instance_key" : selectedChat}
                convId={selectedChat}
                refreshConversations={fetchConversations}
              />
              <PWAInstallPrompt />
            </>
          }
        />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/about" element={<AboutPage />} />
      </Route>
    </Routes>
  );
}

export default App;