import React, { useEffect, useRef, useState } from 'react';
import { Textarea } from '@common/textarea';
import { Button } from '@common/button';
import { format } from 'date-fns';
import { Loader2, Send, ShoppingBagIcon, UserIcon, BotIcon } from 'lucide-react';
import { MarkdownRenderer } from '@components/chat/MarkdownRenderer';
import { Text } from '@common/text';
import { Avatar } from '@common/avatar';
import Markdown, { MarkdownAsync } from 'react-markdown';

// ChatPage: Main chat interface page
function ChatPage({ convId, refreshConversations }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [activeConv, setActiveConv] = useState(convId);
  const messagesEndRef = useRef(null);

  // Fetch messages for selected conversation
  useEffect(() => {
    if (!convId) {
      setMessages([]);
      setActiveConv(null);
      return;
    }
    setLoading(true);
    fetch(`/conversations/${convId}`)
      .then(res => res.json())
      .then(data => {
        setMessages(data);
        setActiveConv(convId);
      })
      .catch(() => setMessages([]))
      .finally(() => setLoading(false));
  }, [convId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Format timestamp to readable format
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    try {
      return format(new Date(timestamp), 'h:mm a');
    } catch (e) {
      return '';
    }
  };

  async function handleSend() {
    if (!input.trim() || isSending) return;
    
    const userMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
      status: 'sending'
    };

    // Optimistically add user message
    setMessages(prev => [...prev, userMessage]);
    setIsSending(true);
    setInput('');

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conv_id: activeConv || undefined,
          message: input.trim(),
        })
      });
      
      const data = await res.json();
      
      if (data.conv_id && !activeConv) {
        refreshConversations && refreshConversations();
        setActiveConv(data.conv_id);
      }
      
      // Fetch updated messages
      const messagesRes = await fetch(`/conversations/${data.conv_id || activeConv}`);
      const updatedMessages = await messagesRes.json();
      setMessages(updatedMessages);
      
    } catch (e) {
      // Update message status to failed
      setMessages(prev => 
        prev.map(msg => 
          msg === userMessage 
            ? { ...msg, status: 'failed' } 
            : msg
        )
      );
    } finally {
      setIsSending(false);
    }
  }

  return (
    <div className="flex flex-col h-[100vh] w-full max-w-full overflow-x-hidden bg-zinc-50 dark:bg-zinc-900">
      {/* Chat messages area */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-6 py-4 max-w-3xl w-full mx-auto">
        <div className="flex flex-col gap-3">
          {loading ? (
            <div className="flex justify-center items-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-zinc-500"></div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center text-center text-zinc-500 mt-12">
              <img
                src="/static/shopify_assistant_logo.png"
                alt="Espresso Bot Logo"
                className="mx-auto mt-6 mb-2 h-96 w-96 object-contain drop-shadow-lg"
                draggable="false"
              />
              <Text>Start a new conversation by sending a message</Text>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div 
                key={i} 
                className={`flex items-start gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                {/* Avatar */}
                <div className="flex-shrink-0">
                  {msg.role === 'user' ? (
                    <Avatar
                      className="size-8 bg-gray-100 dark:bg-zinc-700"
                      initials="Me" 
                      alt="User" 
                    />
                  ) : (
                    <Avatar
                      className="size-8 bg-blue-100 dark:bg-blue-900/30"
                      alt="ShopifyBot"
                      initials="🤖"
                    />
                  )}
                </div>
                
                {/* Message bubble */}
                <div 
                  className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user' 
                      ? 'bg-gray-200 text-black rounded-tr-none' 
                      : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded-tl-none'
                  }`}
                >
                  <div className="w-full break-words">
                    <MarkdownRenderer isAgent={msg.role === 'assistant'}>{String(msg.content || '')}</MarkdownRenderer>
                  </div>
                  <div className={`text-xs mt-2 flex items-center justify-end gap-2 ${
                    msg.role === 'user' ? 'text-gray-400' : 'text-zinc-500 dark:text-zinc-400'
                  }`}>
                    {msg.status === 'sending' && (
                      <span className="flex items-center">
                        <span className="inline-block w-2 h-2 bg-current rounded-full mr-1"></span>
                        Sending
                      </span>
                    )}
                    {msg.status === 'failed' && 'Failed to send'}
                    {msg.timestamp && (
                      <span className="whitespace-nowrap">
                        {formatTimestamp(msg.timestamp)}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} className="h-4" />
        </div>
      </div>
      {/* Input area fixed at the bottom */}
      <div className="sticky bottom-0 w-full bg-zinc-50 dark:bg-zinc-900 py-4 border-t border-zinc-200 dark:border-zinc-700 z-10">
        <form
          className="flex max-w-3xl w-full mx-auto gap-2 px-4 overflow-x-hidden"
          onSubmit={e => { e.preventDefault(); handleSend(); }}
        >
          <Textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 min-h-[44px] max-h-32 resize-y"
            rows={1}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <Button 
            type="submit" 
            className="h-fit px-4 py-3 min-w-[80px] flex items-center justify-center"
            disabled={isSending || !input.trim()}
          >
            {isSending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
            <span className="ml-2">Send</span>
          </Button>
        </form>
      </div>
    </div>
  );
}

export default ChatPage;
