// App: Root of the SPA, sets up layout and routing
import React, { useState, useEffect } from "react";
import { SidebarLayout } from "@common/sidebar-layout";
import { Button } from "@common/button";
import StreamingChatPage from "./features/chat/StreamingChatPage";
import AboutPage from './pages/AboutPage';
import LoginPage from './pages/LoginPage';
import RestrictedPage from './pages/RestrictedPage';
import AdminPage from './pages/AdminPage';
import ProfilePage from './pages/ProfilePage';
import TasksPage from './pages/TasksPage';
import PromptLibraryManager from './features/prompt-library/PromptLibraryManager';
import DashboardPage from './pages/DashboardPage';
import { Routes, Route, Link, Outlet, NavLink, Navigate } from "react-router-dom";
import { Loader2Icon, MessageSquarePlusIcon, XIcon, ShoppingBagIcon, BarChart3Icon, LineChartIcon, GlobeIcon, LinkIcon, FileTextIcon } from 'lucide-react';
import logo from '../static/EspressoBotLogo.png';
import { PWAInstallPrompt } from './components/common/PWAInstallPrompt';
import { Divider } from "@common/divider";
import { Heading } from "@common/heading";
import { MemoryManagementModal } from './components/memory/MemoryManagementModal';
import TopNavDropdown from './components/common/TopNavDropdown';
import LogDrawer from './components/LogDrawer';
import { ScratchpadDialog } from './components/scratchpad/ScratchpadDialog';

// const FLASK_API_BASE_URL = 'http://localhost:5000'; // Not strictly needed if using relative paths and proxy/same-origin

function App() {
  const [conversations, setConversations] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(true); // For conversations loading
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [showMemoryModal, setShowMemoryModal] = useState(false);
  const [showLogDrawer, setShowLogDrawer] = useState(false);
  const [showScratchpadDialog, setShowScratchpadDialog] = useState(false);
  
  // Keyboard shortcut for log drawer (Ctrl/Cmd + Shift + L)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'L') {
        e.preventDefault();
        setShowLogDrawer(prev => !prev);
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Check authentication on mount
  useEffect(() => {
    const checkAuth = async () => {
      // Check for token in URL (from OAuth callback)
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      
      if (token) {
        // Store token and remove from URL
        console.log('Token received from OAuth:', token.substring(0, 20) + '...');
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
            console.log('Auth check successful:', userData);
            setUser(userData);
            fetchConversations(storedToken);
          } else {
            // Invalid token, remove it
            console.error('Auth check failed:', res.status, res.statusText);
            localStorage.removeItem('authToken');
          }
        } catch (error) {
          console.error('Auth check failed:', error);
          localStorage.removeItem('authToken');
        }
      }
      
      console.log('Auth check complete, user:', user);
      setAuthLoading(false);
    };
    
    checkAuth();
  }, []);

  // Fetch conversations list with auth token
  const fetchConversations = async (token = localStorage.getItem('authToken')) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/conversations?t=${Date.now()}`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      const data = await res.json();
      // Force complete re-render by clearing then setting
      setConversations([]);
      setTimeout(() => {
        setConversations(data || []);
      }, 0);
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
              
              <Button 
                    className="w-full cursor-pointer mb-4"
                    color="zinc"
                    outline
                    onClick={() => setShowScratchpadDialog(true)}
                  >
                    <FileTextIcon className="h-4 w-4" /> Scratchpad
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
                          className="absolute top-1/2 right-1 transform -translate-y-1/2 p-1 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity text-xs"
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
                          <div className="truncate">
                            {chat.topic_title ? (
                              <span>{chat.topic_title}</span>
                            ) : (
                              <span style={{opacity: 0.7}}>{chat.title}</span>
                            )}
                          </div>
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
              <TopNavDropdown user={user} onLogout={handleLogout} />  
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
                onTopicUpdate={(conversationId, topicTitle, topicDetails) => {
                  // Instead of updating state, refetch to ensure consistency
                  fetchConversations();
                }}
              />
              <PWAInstallPrompt />
            </>
          }
        />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/prompt-library" element={<PromptLibraryManager />} />
        <Route path="/admin/memory" element={
          <div className="container mx-auto p-6">
            <Button onClick={() => setShowMemoryModal(true)}>
              Open Memory Management
            </Button>
          </div>
        } />
      </Route>
    </Routes>
    
    {/* Memory Management Modal */}
    <MemoryManagementModal 
      isOpen={showMemoryModal} 
      onClose={() => setShowMemoryModal(false)} 
    />
    
    {/* Log Drawer */}
    <LogDrawer 
      isOpen={showLogDrawer}
      onToggle={() => setShowLogDrawer(prev => !prev)}
      token={localStorage.getItem('authToken')}
    />
    
    {/* Scratchpad Dialog */}
    <ScratchpadDialog 
      isOpen={showScratchpadDialog}
      onClose={() => setShowScratchpadDialog(false)}
    />
    </>
  );
}

export default App;