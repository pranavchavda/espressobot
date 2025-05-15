// App: Root of the SPA, sets up layout and routing
import React, { useState } from 'react';
import { SidebarLayout } from '@common/sidebar-layout';
import { Button } from '@common/button';
import ChatPage from './features/chat/ChatPage';
import { Routes, Route } from 'react-router-dom';

import { useEffect } from 'react';

function App() {
  const [conversations, setConversations] = useState([]);
  const [selectedChat, setSelectedChat] = useState(null);
  const [loading, setLoading] = useState(true);

  // Fetch conversations from Flask API
  const fetchConversations = async () => {
    setLoading(true);
    try {
      const res = await fetch('/conversations');
      const data = await res.json();
      setConversations(data);
      if (!selectedChat && data.length > 0) setSelectedChat(data[0].id);
    } catch (e) {
      setConversations([]);
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { fetchConversations(); }, []);

  return (
    <SidebarLayout
      className=""
      navbar={<div className="font-semibold text-lg px-4 py-2">Chat App</div>}
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
                {conversations.length === 0 && (
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
