import React, { useEffect, useRef, useState } from "react";
import { Textarea } from "@common/textarea";
import { Button } from "@common/button"; // Ensure Button component is correctly imported
import { format } from "date-fns";
import { Loader2, Send, UserIcon, BotIcon } from "lucide-react"; // Removed ShoppingBagIcon if not used
import { MarkdownRenderer } from "@components/chat/MarkdownRenderer"; // Assuming this path is correct
import { Text, TextLink } from "@common/text";
import { Avatar } from "@common/avatar";
import logo from "../../../static/EspressoBotLogo.png";

// Markdown import seems duplicated, MarkdownAsync might be what you intend to use if it's different
// import Markdown, { MarkdownAsync } from 'react-markdown';

// ChatPage: Main chat interface page
function ChatPage({ convId, refreshConversations }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [activeConv, setActiveConv] = useState(convId);
  const [suggestions, setSuggestions] = useState([]); // New state for suggestions
  const messagesEndRef = useRef(null);

  // Fetch messages for selected conversation
  useEffect(() => {
    if (!convId) {
      setMessages([]);
      setSuggestions([]); // Clear suggestions when conversation changes
      setActiveConv(null);
      return;
    }
    setLoading(true);
    fetch(`/api/conversations/${convId}`)
      .then((res) => res.json())
      .then((data) => {
        setMessages(data);
        setActiveConv(convId);
        // Check if the last message in fetched data has suggestions
        // This is a more robust way if suggestions persist with conversations
        const lastMessage = data[data.length - 1];
        if (
          lastMessage &&
          lastMessage.role === "assistant" &&
          lastMessage.suggestions
        ) {
          setSuggestions(lastMessage.suggestions);
        } else {
          setSuggestions([]); // Clear if no relevant suggestions
        }
      })
      .catch(() => {
        setMessages([]);
        setSuggestions([]);
      })
      .finally(() => setLoading(false));
  }, [convId]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Format timestamp to readable format
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "";
    try {
      return format(new Date(timestamp), "h:mm a");
    } catch (e) {
      return ""; // Invalid timestamp
    }
  };

  async function handleSend(messageContent) {
    const textToSend =
      typeof messageContent === "string" ? messageContent.trim() : input.trim();

    if (!textToSend || isSending) return;

    const userMessage = {
      role: "user",
      content: textToSend,
      timestamp: new Date().toISOString(),
      status: "sending",
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    setInput(""); // Clear the main input box
    setSuggestions([]); // Always clear suggestions when a message is being sent

    try {
      // Build the messages payload for context
      const payloadMessages = [...messages, userMessage]
        .filter((m) => m.role && m.content)
        .map((m) => ({ role: m.role, content: m.content }));
      const payload = { messages: payloadMessages };
      if (activeConv) payload.conv_id = activeConv;
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await res.json(); // Expect: { reply, conv_id, suggestions? }

      if (data.conv_id && !activeConv) {
        refreshConversations && refreshConversations();
        setActiveConv(data.conv_id);
      }

      // Set suggestions from the direct API response for the *new* bot message
      if (data.suggestions && Array.isArray(data.suggestions)) {
        setSuggestions(data.suggestions);
      } else {
        // Ensure suggestions are cleared if API doesn't provide new ones
        // (already done at the start of handleSend, but for clarity)
        setSuggestions([]);
      }

      // Fetch updated messages to get the new bot message and ensure UI consistency
      // This is crucial as the `data` from `/chat` might not contain the full message object
      // or if multiple messages (user + bot) are added in one go by the backend.
      const messagesRes = await fetch(
        `/api/conversations/${data.conv_id || activeConv}`,
      );
      const updatedMessages = await messagesRes.json();
      setMessages(updatedMessages);

      // If the backend directly returns the new bot message and suggestions,
      // and messages are only added one by one on the frontend,
      // you might be able to optimize by not re-fetching all messages.
      // However, re-fetching ensures data integrity.
    } catch (e) {
      console.error("Failed to send message or fetch updates:", e);
      setMessages((prev) =>
        prev.map((msg) =>
          // Find the optimistic message by content and original timestamp (or a unique ID if you add one)
          msg.content === userMessage.content &&
          msg.role === "user" &&
          msg.status === "sending"
            ? { ...msg, status: "failed" }
            : msg,
        ),
      );
      setSuggestions([]); // Clear suggestions on error
    } finally {
      setIsSending(false);
    }
  }

  // Handle clicking a suggestion
  const handleSuggestionClick = (suggestionText) => {
    handleSend(suggestionText); // Directly send the suggestion text
    // setSuggestions is now handled within handleSend
  };

  const inputRef = useRef(null); // Ref for the textarea

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
                src={logo}
                alt="Espresso Bot Logo"
                className="mx-auto mt-6 mb-2 h-96 w-96 object-contain drop-shadow-lg"
                draggable="false"
              />
              <Text>Start a new conversation by sending a message
                 visit the <TextLink to="/about">About</TextLink> page for more information and to learn how to use the bot.
              </Text>
            </div>
          ) : (
            messages.map((msg, i) => (
              <div
                key={msg.id || i} // Prefer a stable ID if available from backend
                className={`flex items-start gap-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <div className="flex-shrink-0">
                  {msg.role === "user" ? (
                    <Avatar
                      className="size-8 bg-gray-100 dark:bg-zinc-700"
                      initials="Me"
                      alt="User"
                    />
                  ) : (
                    <Avatar
                      className="size-8 bg-blue-100 dark:bg-blue-900/30"
                      alt="ShopifyBot"
                      initials="🤖" // Or use BotIcon if preferred and styled
                    />
                  )}
                </div>

                <div
                  className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm ${
                    msg.role === "user"
                      ? "bg-gray-200 text-black dark:bg-gray-700 dark:text-white rounded-tr-none"
                      : "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded-tl-none"
                  }`}
                >
                  <div className="w-full break-words prose dark:prose-invert prose-sm max-w-none">
                    <MarkdownRenderer isAgent={msg.role === "assistant"}>
                      {String(msg.content || "")}
                    </MarkdownRenderer>
                  </div>
                  <div
                    className={`text-xs mt-2 flex items-center justify-end gap-2 ${
                      msg.role === "user"
                        ? "text-gray-400 dark:text-gray-500"
                        : "text-zinc-500 dark:text-zinc-400"
                    }`}
                  >
                    {msg.status === "sending" && (
                      <span className="flex items-center">
                        <Loader2 className="h-3 w-3 animate-spin mr-1" />
                        Processing
                      </span>
                    )}
                    {msg.status === "failed" && (
                      <span className="text-red-500">Failed</span>
                    )}
                    {msg.timestamp &&
                      !msg.status && ( // Only show timestamp if not sending or failed
                        <span className="whitespace-nowrap">
                          {formatTimestamp(msg.timestamp)}
                        </span>
                      )}
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} className="h-4" /> {/* Scroll anchor */}
        </div>
      </div>

      {/* Input area + Suggestions, fixed at the bottom */}
      <div className="sticky bottom-0 w-full bg-zinc-50 dark:bg-zinc-900 py-3 border-t border-zinc-200 dark:border-zinc-700 z-10">
        {/* Suggestions Area */}
        {suggestions && suggestions.length > 0 && !isSending && (
          <div className="max-w-3xl w-full mx-auto px-4 mb-2 flex flex-wrap gap-2 justify-center sm:justify-start">
            {suggestions.map((suggestion, index) => (
              <Button
                key={index}
                variant="outline" // Ensure this variant is defined in your Button component
                size="sm" // Assuming 'sm' is a valid size for smaller buttons
                className="py-1 px-2.5 h-auto dark:bg-zinc-700 dark:hover:bg-zinc-600 border-zinc-300 dark:border-zinc-600 hover:bg-zinc-100 text-zinc-100 dark:text-zinc-200 rounded-lg text-xs"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        )}

        {/* Input Form */}
        <form
          className="flex max-w-3xl w-full mx-auto gap-2 px-4 items-end"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <Textarea
            ref={inputRef} // Assign ref
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              if (e.target.value.trim() !== "" && suggestions.length > 0) {
                setSuggestions([]); // Clear suggestions if user starts typing
              }
            }}
            placeholder="Type a message..."
            className="flex-1 min-h-[60px] max-h-36 resize-y leading-tight py-2.5" // Adjusted padding & max-height
            rows={1}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <Button
            type="submit"
            className="h-[44px] px-3.5 py-2 min-w-[44px] sm:min-w-[80px] flex items-center justify-center" // Adjusted for icon only on small screens
            disabled={isSending || !input.trim()}
          >
            {isSending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
            <span className="ml-2 hidden sm:inline">Send</span>{" "}
            {/* Hide "Send" text on small screens */}
          </Button>
        </form>
      </div>
    </div>
  );
}

export default ChatPage;
