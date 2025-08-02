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
import HomePage from './pages/HomePage';
import PriceMonitorLayout from './pages/price-monitor/PriceMonitorLayout';
import AgentManagementPage from './pages/AgentManagementPage';
import { Routes, Route, Link, Outlet, NavLink, Navigate, useNavigate, useLocation } from "react-router-dom";
import { Loader2Icon, MessageSquarePlusIcon, XIcon, LineChartIcon, FileTextIcon } from 'lucide-react';
import { PWAInstallPrompt } from './components/common/PWAInstallPrompt';
import { Divider } from "@common/divider";
import { MemoryManagementModal } from './components/memory/MemoryManagementModal';
import TopNavDropdown from './components/common/TopNavDropdown';
import TopBar from './components/common/TopBar';
import LogDrawer from './components/LogDrawer';
import { ScratchpadDialog } from './components/scratchpad/ScratchpadDialog';
import SidebarNav from './components/common/SidebarNav';

// const FLASK_API_BASE_URL = 'http://localhost:5000'; // Not strictly needed if using relative paths and proxy/same-origin

function App() {
  const navigate = useNavigate();
  const location = useLocation();
  const [conversations, setConversations] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(true); // For conversations loading
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [showMemoryModal, setShowMemoryModal] = useState(false);
  const [showLogDrawer, setShowLogDrawer] = useState(false);
  const [showScratchpadDialog, setShowScratchpadDialog] = useState(false);
  const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains('dark'));
  const [convSearch, setConvSearch] = useState('');
  // Sidebar UI state
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [sidebarMobileOpen, setSidebarMobileOpen] = useState(false);
  
  // Ensure selectedChat is null when at root path
  useEffect(() => {
    if (location.pathname === '/') {
      console.log('At root path, clearing selectedChat');
      setSelectedChat(null);
    }
  }, [location.pathname]);

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
      console.log('[App] checkAuth() called, current URL:', window.location.href);
      
      // Check for token in URL (from OAuth callback)
      const urlParams = new URLSearchParams(window.location.search);
      const token = urlParams.get('token');
      
      console.log('[App] Checking for OAuth token in URL:', {
        fullUrl: window.location.href,
        search: window.location.search,
        hasToken: !!token,
        tokenPreview: token ? token.substring(0, 20) + '...' : 'none'
      });
      
      if (token) {
        // Store token and remove from URL
        console.log('[App] Token received from OAuth, storing in localStorage');
        localStorage.setItem('authToken', token);
        // Navigate to homepage after OAuth login
        navigate('/');
        return; // Exit early to avoid duplicate auth check
      }
      
      // Check if user is authenticated
      const storedToken = localStorage.getItem('authToken');
      console.log('[App] Auth check - stored token:', storedToken ? 'present' : 'missing');
      
      if (storedToken) {
        try {
          console.log('[App] Making /api/auth/me request with token');
          const res = await fetch('/api/auth/me', {
            headers: {
              'Authorization': `Bearer ${storedToken}`
            }
          });
          
          console.log('[App] /api/auth/me response:', res.status, res.statusText);
          
          if (res.ok) {
            const userData = await res.json();
            console.log('[App] Auth check successful, user data:', userData);
            setUser(userData);
            // Don't auto-select last chat on login - let user start from homepage
            fetchConversations(storedToken, false);
          } else {
            // Invalid token, remove it
            console.error('[App] Auth check failed - invalid token:', res.status, res.statusText);
            const errorText = await res.text().catch(() => 'Unable to read error');
            console.error('[App] Error response body:', errorText);
            localStorage.removeItem('authToken');
          }
        } catch (error) {
          console.error('[App] Auth check network error:', error);
          localStorage.removeItem('authToken');
        }
      } else {
        console.log('[App] No stored token found, user not authenticated');
      }
      
      console.log('Auth check complete, user:', user);
      setAuthLoading(false);
    };
    
    checkAuth();
  }, []);

  // Fetch conversations list with auth token
  const fetchConversations = async (token = localStorage.getItem('authToken'), selectLastChat = true) => {
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
      // Keep current selection if still present; otherwise optionally default to the most recent conversation
      setSelectedChat((prevSelected) => {
        if (data && data.find((c) => c.id === prevSelected)) {
          return prevSelected;
        }
        return selectLastChat && data && data.length > 0 ? data[0].id : null;
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


  // Guarded content rendered via variables to avoid early returns that change hook order
  const LoadingScreen = (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-900">
      <Loader2Icon className="animate-spin h-16 w-16 text-zinc-400" />
    </div>
  );

  const Unauthenticated = (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );

  const Restricted = (
    <RestrictedPage user={user} onLogout={handleLogout} />
  );

  // For now show all conversations; search input removed per request
  const filteredConversations = conversations;

  const toggleTheme = () => {
    const root = document.documentElement;
    const next = !root.classList.contains('dark');
    root.classList.toggle('dark', next);
    setIsDark(next);
    // Persist preference
    try { localStorage.setItem('theme', next ? 'dark' : 'light'); } catch {}
  };

  useEffect(() => {
    const pref = localStorage.getItem('theme');
    if (pref === 'dark') {
      document.documentElement.classList.add('dark');
      setIsDark(true);
    } else if (pref === 'light') {
      document.documentElement.classList.remove('dark');
      setIsDark(false);
    }
  }, []);

  // Decide which view to show without breaking hooks order
  const shouldShowLoading = authLoading;
  const shouldShowUnauthed = !authLoading && !user;
  const shouldShowRestricted = !authLoading && user && !user.is_whitelisted;

  return (
    <>
      {shouldShowLoading ? LoadingScreen : shouldShowUnauthed ? Unauthenticated : shouldShowRestricted ? Restricted : (
        <>
      <Routes>
        <Route element={
        <SidebarLayout
          className=""
          navbar={
            <TopBar
              title={location.pathname === '/chat' ? 'Chat' : undefined}
              user={user}
              onLogout={handleLogout}
              onToggleLogs={() => setShowLogDrawer(prev => !prev)}
              // Add a hamburger action on small screens by reusing onToggleLogs slot if TopBar supports extra controls.
              // If TopBar exposes a prop like onToggleSidebar, wire it; otherwise sidebar remains always visible on desktop.
              onGlobalSearch={undefined}
              onToggleTheme={undefined}
              isDark={isDark}
            />
          }
          // navbar={
          //   <div className="flex justify-between items-center w-full py-2">
          //     <div className="flex items-center">
          //     <NavLink to="/">
          //       <img 
          //         src={logo}
          //         alt="EspressoBot Logo" 
          //         className="h-8 ml-2 mr-2"
          //       />
          //       </NavLink>
          //     </div>
          //     <div className="flex items-center space-x-4">
                
          //     </div>
          //   </div>
          // }
          sidebar={
            <SidebarNav
              user={user}
              onLogout={handleLogout}
              conversations={filteredConversations}
              selectedChat={selectedChat}
              loading={loading}
              onSelectConversation={(id) => {
                setSelectedChat(id);
                navigate("/chat");
              }}
              onDeleteConversation={handleDeleteConversation}
              onNewChat={() => {
                setSelectedChat(null);
                navigate("/");
              }}
              onOpenScratchpad={() => setShowScratchpadDialog(true)}
              isDark={isDark}
              onToggleTheme={toggleTheme}
              collapsible={true}
              collapsed={sidebarCollapsed}
              onToggleCollapsed={() => setSidebarCollapsed(prev => !prev)}
            />
          }
        >
          <div className="flex flex-col h-[86vh]">
          <Outlet />
          </div>
                </SidebarLayout>
      }>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/chat"
          element={
            <>
              <StreamingChatPage
                convId={selectedChat}
                onTopicUpdate={(conversationId, topicTitle, topicDetails) => {
                  // Instead of updating state, refetch to ensure consistency
                  fetchConversations();
                }}
                onNewConversation={() => setSelectedChat(null)}
              />
              <PWAInstallPrompt />
            </>
          }
        />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/price-monitor/*" element={<PriceMonitorLayout />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/prompt-library" element={<PromptLibraryManager />} />
        <Route path="/admin/memory" element={
          <div className="container mx-auto p-6">
            <Button onClick={() => setShowMemoryModal(true)}>
              Open Memory Management
            </Button>
          </div>
        } />
        <Route path="/agent-management" element={<AgentManagementPage />} />
      </Route>
    </Routes>
        </>
      )}
    
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
