// App: Root of the SPA, sets up layout and routing
import React, { useState, useEffect } from 'react';
import { SidebarLayout } from '@common/sidebar-layout';
import { Button } from '@common/button';
import ChatPage from './features/chat/ChatPage';
import LoginPage from './features/auth/LoginPage'; // Import LoginPage
import { Routes, Route } from 'react-router-dom';

// const FLASK_API_BASE_URL = 'http://localhost:5000'; // Not strictly needed if using relative paths and proxy/same-origin

function App() {
  const [conversations, setConversations] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(true); // Use 'loading' as per previous code

  // Authentication state (frontend-only) - KEPT
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authLoading, setAuthLoading] = useState(false); // No initial async auth check - KEPT
  const [authError, setAuthError] = useState(null); // KEPT

  // Fetch conversations from Flask API - REVERTED to previous structure
  const fetchConversations = async () => {
    setLoading(true);
    try {
      // Assuming '/conversations' will be proxied by Vite or is same-origin
      const res = await fetch('/conversations'); 
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
      console.error('Failed to fetch conversations (reverted):', e);
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };

  // Call fetchConversations when component mounts or isAuthenticated changes - MODIFIED TO INCLUDE AUTH CHECK
  useEffect(() => {
    if (isAuthenticated) {
      fetchConversations();
    }
  }, [isAuthenticated]); // Fetch when isAuthenticated becomes true

  // handleLogin - KEPT
  const handleLogin = (password) => {
    setAuthLoading(true);
    setAuthError(null);
    const appPassword = import.meta.env.VITE_APP_PASSWORD;
    if (!appPassword) {
      console.error('VITE_APP_PASSWORD is not set in the environment.');
      setAuthError('Application password configuration error.');
      setIsAuthenticated(false);
      setAuthLoading(false);
      return;
    }
    if (password === appPassword) {
      setIsAuthenticated(true);
      setSelectedChat(null); 
    } else {
      setAuthError('Incorrect password.');
      setIsAuthenticated(false);
    }
    setAuthLoading(false);
  };

  // handleLogout - KEPT
  const handleLogout = () => {
    setIsAuthenticated(false);
    setSelectedChat(null);
    setConversations([]);
    setAuthError(null);
  };

  // Conditional rendering based on authentication state - KEPT
  if (authLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-zinc-100 dark:bg-zinc-900">
        <div className="text-xl text-zinc-700 dark:text-zinc-300">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} error={authError} loading={authLoading} />;
  }

  // User is authenticated, render the main app - REVERTED TO PREVIOUS JSX STRUCTURE
  return (
    <SidebarLayout
      className=""
      navbar={<div className="flex justify-between items-center w-full">
          <div className="font-semibold text-lg px-4 py-2">Chat App</div>
          {/* Added Logout button to the reverted navbar structure */} 
          <Button onClick={handleLogout} variant="ghost" className="mr-2 px-3 py-1 text-sm">Logout</Button>
        </div>}
      sidebar={
        <div className="flex flex-col h-full">
          <Button className="mb-4 mx-2" onClick={() => setSelectedChat(null)}>+ New Chat</Button>
          <nav className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="text-zinc-400 px-4 py-2">Loading...</div>
            ) : (
              <ul className="flex flex-col gap-1">
                {conversations.map(chat => (
                  <li key={chat.id}>
                    <button
                      className={`w-full text-left px-4 py-3 rounded-lg transition-colors
                        ${selectedChat === chat.id ? 'bg-zinc-200 dark:bg-zinc-800 font-semibold' : 'hover:bg-zinc-100 dark:hover:bg-zinc-800'}`}
                      onClick={() => setSelectedChat(chat.id)}
                    >
                      <div className="truncate">{chat.title}</div>
                      <div className="text-xs text-zinc-500 truncate">{chat.created_at ? new Date(chat.created_at).toLocaleString() : ''}</div>
                    </button>
                  </li>
                ))}
                {conversations.length === 0 && !loading && (
                  <li className="text-zinc-400 px-4 py-2">No conversations</li>
                )}
              </ul>
            )}
          </nav>
        </div>
      }
    >
      <Routes>
        <Route path="/" element={<ChatPage key={selectedChat} convId={selectedChat} refreshConversations={fetchConversations} />} />
      </Routes>
    </SidebarLayout>
  );
}

export default App;
