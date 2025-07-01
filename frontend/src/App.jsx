// App: Root of the SPA, sets up layout and routing
import React, { useState, useEffect } from "react";
import { SidebarLayout } from "@common/sidebar-layout";
import { Button } from "@common/button";
import StreamingChatPage from "./features/chat/StreamingChatPage";
import AboutPage from './pages/AboutPage';
import LoginPage from './pages/LoginPage';
import RestrictedPage from './pages/RestrictedPage';
import { Routes, Route, Link, Outlet, NavLink, Navigate } from "react-router-dom";
import { Loader2Icon, MessageSquarePlusIcon, XIcon, ShoppingBagIcon, BarChart3Icon, LineChartIcon, GlobeIcon, LinkIcon, LogOutIcon, UserIcon, Database } from 'lucide-react';
import logo from '../static/EspressoBotLogo.png';
import { PWAInstallPrompt } from './components/common/PWAInstallPrompt';
import { Divider } from "@common/divider";
import { Heading } from "@common/heading";
import { MemoryManagementModal } from './components/memory/MemoryManagementModal';

// const FLASK_API_BASE_URL = 'http://localhost:5000'; // Not strictly needed if using relative paths and proxy/same-origin

function App() {
  const [conversations, setConversations] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(true); // For conversations loading
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [showMemoryModal, setShowMemoryModal] = useState(false);

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      // Check for token in URL (from OAuth callback)
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      
      if (token) {
        // Store token and remove from URL
        localStorage.setItem('authToken', token);
        window.history.replaceState({}, document.title, window.location.pathname);
      }
      
      // Check if user is authenticated
      const storedToken = localStorage.getItem('authToken');
      if (storedToken) {
        try {
          const res = await fetch('/api/auth/me', {
            headers: {
              'Authorization': `Bearer ${storedToken}`
            }
          });
          
          if (res.ok) {
            const userData = await res.json();
            setUser(userData);
            fetchConversations(storedToken);
          } else {
            // Invalid token, remove it
            localStorage.removeItem('authToken');
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          localStorage.removeItem('authToken');
        }
      }
      
      setAuthLoading(false);
    };
    
    checkAuth();
  }, []);

  // Fetch conversations list with auth token
  const fetchConversations = async (token = localStorage.getItem('authToken')) => {
    setLoading(true);
    try {
      const res = await fetch("/api/conversations", {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      const data = await res.json();
      setConversations(data || []);
      // Keep current selection if still present; otherwise default to the most recent conversation (if any)
      setSelectedChat((prevSelected) => {
        if (data && data.find((c) => c.id === prevSelected)) {
          return prevSelected;
        }
        return data && data.length > 0 ? data[0].id : null;
      });
    } catch (e) {
      console.error("Failed to fetch conversations:", e);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };

  // Function to handle deleting a conversation
  const handleDeleteConversation = async (convIdToDelete) => {
    if (!convIdToDelete) return;

    const token = localStorage.getItem('authToken');
    try {
      const response = await fetch(`/api/conversations/${convIdToDelete}`, {
        method: 'DELETE',
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
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

  // Handle logout
  const handleLogout = async () => {
    const token = localStorage.getItem('authToken');
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
    } catch (error) {
      console.error('Logout error:', error);
    }
    
    // Clear local state
    localStorage.removeItem('authToken');
    setUser(null);
    setConversations([]);
    setSelectedChat(null);
  };


  // Show loading screen while checking auth
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-900">
        <Loader2Icon className="animate-spin h-16 w-16 text-zinc-400" />
      </div>
    );
  }

  // Show login page if not authenticated
  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // Show restricted page if user is not whitelisted
  if (!user.is_whitelisted) {
    return <RestrictedPage user={user} onLogout={handleLogout} />;
  }

  return (
    <>
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
                {/* User info */}
                <div className="flex items-center space-x-2 px-3 py-1 bg-zinc-100 dark:bg-zinc-800 rounded-md">
                  {user.profile_picture ? (
                    <img 
                      src={user.profile_picture} 
                      alt={user.name} 
                      className="h-6 w-6 rounded-full"
                    />
                  ) : (
                    <UserIcon className="h-5 w-5 text-zinc-600 dark:text-zinc-400" />
                  )}
                  <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                    {user.name || user.email}
                  </span>
                </div>
                
                {/* Memory Management - Admin Only */}
                {user.email === 'pranav@idrinkcoffee.com' && (
                  <Button
                    onClick={() => setShowMemoryModal(true)}
                    outline
                    small
                    className="flex items-center"
                  >
                    <Database className="h-4 w-4 mr-1" />
                    Memory
                  </Button>
                )}
                
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
                  outline
                  small
                  className="flex items-center"
                >
                  <LogOutIcon className="h-4 w-4 mr-1" />
                  Logout
                </Button>
              </div>
            </div>
          }
          sidebar={
            <div className="flex flex-col h-[93vh] sm:h-full">

              <nav className="flex-1 overflow-y-auto">
              <Button 
                    className="w-full cursor-pointer my-10 "
                    color="steel-blue"
                    outline
                    onClick={() => setSelectedChat(null)}
                  >
                    <MessageSquarePlusIcon className="h-4 w-4" /> New Chat
                  </Button>
              <Divider
              soft = "true"
              />
              {loading ? (
                  <div className="flex flex-col items-center justify-center py-2">
                    <Loader2Icon className="animate-spin h-16 w-16 text-zinc-400" />
                  </div>
                ) : (
                  <>

                  <ul className="flex flex-col max-h-[50vh] overflow-y-auto h-[50vh]">
                    {conversations.map((chat) => (
                      <li key={chat.id} className="group relative pr-4">                        
                      
                      <Button
                          outline
                          small
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
                        <Link 
                          to="/"
                          className={`block w-full text-left px-2 py-2 shadow-sm rounded-lg transition-colors ${
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

                      </li>
                    ))}

                    {conversations.length === 0 && !loading && (
                      <li className="text-zinc-400 px-4 py-2">No conversations</li>
                    )}
                  </ul>
                  </>
                )}
    <Divider
              soft = "true"
              />
              <div className="shadow mx-1 rounded-lg ">  
              <div className="flex items-center px-3 py-3">
                <LinkIcon className="h-5 w-5 mr-2 text-indigo-600 dark:text-indigo-400" />
                <Heading
                  level={3}
                  className="font-medium text-zinc-800 dark:text-zinc-200"
                >
                  Important Links
                </Heading>
              </div>
              <ul className="flex flex-col space-y-2 px-2 py-2">
                <li>
                  <a 
                    href="https://admin.shopify.com/store/idrinkcoffee" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center p-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-zinc-700 dark:text-zinc-300"
                  >
                    <ShoppingBagIcon className="h-5 w-5 mr-3 text-[#96bf48]" />
                    <span>Shopify</span>
                  </a>
                </li>
                <li>
                  <a 
                    href="https://ads.google.com/aw/campaigns" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center p-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-zinc-700 dark:text-zinc-300"
                  >
                    <BarChart3Icon className="h-5 w-5 mr-3 text-[#4285F4]" />
                    <span>Google Ads</span>
                  </a>
                </li>
                <li>
                  <a 
                    href="https://analytics.google.com/analytics/web" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center p-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-zinc-700 dark:text-zinc-300"
                  >
                    <LineChartIcon className="h-5 w-5 mr-3 text-[#E37400]" />
                    <span>Google Analytics</span>
                  </a>
                </li>
                <li>
                  <a 
                    href="https://webhook-listener-pranavchavda.replit.app/" 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="flex items-center p-2 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-zinc-700 dark:text-zinc-300"
                  >
                    <GlobeIcon className="h-5 w-5 mr-3 text-[#667eea]" />
                    <span>MCP Tool Manager</span>
                  </a>
                </li>
              </ul>
              </div>  
              </nav>
          

            </div>
          }
        >
          <div className="flex flex-col h-[86vh]">
          <Outlet />
          </div>
                </SidebarLayout>
      }>
        <Route
          path="/"
          element={
            <>
              <StreamingChatPage
                convId={selectedChat}
              />
              <PWAInstallPrompt />
            </>
          }
        />
        <Route path="/about" element={<AboutPage />} />
      </Route>
    </Routes>
    
    {/* Memory Management Modal */}
    <MemoryManagementModal 
      isOpen={showMemoryModal} 
      onClose={() => setShowMemoryModal(false)} 
    />
    </>
  );
}

export default App;