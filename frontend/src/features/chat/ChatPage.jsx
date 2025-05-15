import React, { useEffect, useState } from 'react';
import { Textarea } from '@common/textarea';
import { Button } from '@common/button';

// ChatPage: Main chat interface page
function ChatPage({ convId, refreshConversations }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [msgLoading, setMsgLoading] = useState(false);
  const [activeConv, setActiveConv] = useState(convId);

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

  async function handleSend() {
    if (!input.trim()) return;
    setMsgLoading(true);
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
        // New conversation started
        refreshConversations && refreshConversations();
        setActiveConv(data.conv_id);
      }
      // Fetch messages after sending
      fetch(`/conversations/${data.conv_id || activeConv}`)
        .then(res => res.json())
        .then(setMessages);
      setInput('');
    } catch (e) {
      // Optionally show error
    } finally {
      setMsgLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[100vh] w-full max-w-full overflow-x-hidden bg-zinc-50 dark:bg-zinc-900">
      {/* Chat messages area */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-0 sm:px-0 py-8 max-w-3xl w-full mx-auto">
        <div className="flex flex-col gap-2">
          {messages.map((msg, i) => (
            <div key={i} className="py-2 px-4 rounded-lg bg-white shadow border border-zinc-200 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100 dark:border-zinc-700">
              {msg.content}
            </div>
          ))}
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
          <Button type="submit" className="h-fit px-6 py-3">
            Send
          </Button>
        </form>
      </div>
    </div>
  );
}

export default ChatPage;
