// App: Root of the SPA, sets up layout and routing
import React, { useState, useEffect } from "react";
import { SidebarLayout } from "@common/sidebar-layout";
import { Button } from "@common/button";
import StreamingChatPage from "./features/chat/StreamingChatPage";
import AboutPage from './pages/AboutPage';
import { Routes, Route, Link, Outlet, NavLink } from "react-router-dom";
import { Loader2Icon, MessageSquarePlusIcon, XIcon } from 'lucide-react';
import logo from '../static/EspressoBotLogo.png';
import { PWAInstallPrompt } from './components/common/PWAInstallPrompt';

// const FLASK_API_BASE_URL = 'http://localhost:5000'; // Not strictly needed if using relative paths and proxy/same-origin

function App() {
  const [conversations, setConversations] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(true); // For conversations loading

  // Fetch conversations list on mount
  const fetchConversations = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/conversations");
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

  useEffect(() => {
    fetchConversations();
  }, []);

  // Function to handle deleting a conversation
  const handleDeleteConversation = async (convIdToDelete) => {
    if (!convIdToDelete) return;

    // Optional: Add a confirmation dialog here
    // if (!window.confirm("Are you sure you want to delete this conversation?")) {
    //   return;
    // }

    try {
      const response = await fetch(`/api/conversations/${convIdToDelete}`, {
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
                {/* Profile, Tasks, Logout removed, About remains */}
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
              </div>
            </div>
          }
          sidebar={
            <div className="flex flex-col h-[93vh] sm:h-full">
                  <Button 
                    className="w-fit cursor-pointer mt-10"
                    color="steel-blue"
                    outline
                    onClick={() => setSelectedChat(null)}
                  >
                    <MessageSquarePlusIcon className="h-4 w-4 mt-1" />
                  </Button>
              <nav className="flex-1 overflow-y-auto">
              {loading ? (
                  <div className="flex flex-col items-center justify-center py-2">
                    <Loader2Icon className="animate-spin h-16 w-16 text-zinc-400" />
                  </div>
                ) : (
                  <>

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
                  </>
                )}

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
  );
}

export default App;