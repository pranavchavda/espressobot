import React, { useEffect, useRef, useState } from "react";
import { Textarea } from "@common/textarea";
import { Button } from "@common/button";
import { format } from "date-fns";
import { Loader2, Send, UserIcon, BotIcon } from "lucide-react";
import { MarkdownRenderer } from "@components/chat/MarkdownRenderer";
import { Text } from "@common/text";
import { Avatar } from "@common/avatar";
import logo from "../../../static/shopify_assistant_logo.png";

function StreamingChatPage({ convId, refreshConversations }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [activeConv, setActiveConv] = useState(convId);
  const [suggestions, setSuggestions] = useState([]);
  const [streamingMessage, setStreamingMessage] = useState(null);
  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  // Fetch messages for selected conversation
  useEffect(() => {
    if (!convId) {
      setMessages([]);
      setSuggestions([]);
      setActiveConv(null);
      return;
    }
    setLoading(true);
    fetch(`/conversations/${convId}`)
      .then((res) => res.json())
      .then((data) => {
        setMessages(data);
        setActiveConv(convId);
        const lastMessage = data[data.length - 1];
        if (
          lastMessage &&
          lastMessage.role === "assistant" &&
          lastMessage.suggestions
        ) {
          setSuggestions(lastMessage.suggestions);
        } else {
          setSuggestions([]);
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
  }, [messages, streamingMessage]);

  // Format timestamp to readable format
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "";
    try {
      return format(new Date(timestamp), "h:mm a");
    } catch (e) {
      return "";
    }
  };

  // Clean up event source on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Handle sending a message with streaming response
  async function handleSend(messageContent) {
    const textToSend =
      typeof messageContent === "string" ? messageContent.trim() : input.trim();

    if (!textToSend || isSending) return;

    // Add user message to the conversation
    const userMessage = {
      role: "user",
      content: textToSend,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    setInput("");
    setSuggestions([]);

    // Initialize streaming message
    setStreamingMessage({
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      isStreaming: true,
    });

    // Close any existing SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      // Set up Server-Sent Events connection
      const fetchUrl = "/stream_chat";

      // Use fetch POST to start the stream
      const response = await fetch(fetchUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conv_id: activeConv || undefined,
          message: textToSend,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Get the response as a ReadableStream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let eventData = "";

      // Process the stream
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        eventData += chunk;

        // Process any complete SSE messages
        const messages = eventData.split(/\n\n/);
        eventData = messages.pop() || ""; // Keep the last incomplete chunk for next iteration

        for (const message of messages) {
          if (!message.trim() || !message.startsWith("data:")) continue;

          try {
            // Extract and parse the JSON data
            const jsonString = message.split(/\n/)
              .filter(line => line.startsWith("data:"))
              .map(line => line.slice(5).trim())
              .join("");

            const data = JSON.parse(jsonString);

            // Handle initial connection with conversation ID
            if (data.conv_id && !activeConv) {
              setActiveConv(data.conv_id);
              refreshConversations && refreshConversations();
            }

            // Handle content updates
            if (data.delta || data.content) {
              setStreamingMessage(prev => ({
                ...prev,
                content: data.content || (prev?.content + (data.delta || "")),
              }));
            }

            // Handle suggestions
            if (data.suggestions && Array.isArray(data.suggestions)) {
              setSuggestions(data.suggestions);
            }

            // Handle completion
            if (data.done) {
              // First, capture the final content
              const finalContent = streamingMessage?.content || "";
              const timestamp = new Date().toISOString();
              
              // Add to messages array first, with a unique ID to ensure it's stable
              const messageId = `msg-${Date.now()}`;
              setMessages(prev => [
                ...prev, 
                { 
                  id: messageId,
                  role: "assistant", 
                  content: finalContent, 
                  timestamp: timestamp,
                }
              ]);
              
              // Ensure the new message is in the state before clearing streaming
              // Use a longer timeout and only clear if content matches
              setTimeout(() => {
                setMessages(prevMsgs => {
                  // Verify the message was actually added before clearing streaming
                  const messageExists = prevMsgs.some(msg => 
                    msg.id === messageId && msg.content === finalContent);
                  
                  if (messageExists) {
                    // Only now clear the streaming message
                    setStreamingMessage(null);
                  }
                  return prevMsgs;
                });
              }, 250);
              
              break;
            }

            // Handle errors
            if (data.error) {
              console.error("Stream error:", data.error);
              setStreamingMessage(prev => ({
                ...prev,
                content: `Error: ${data.error}`,
                isError: true,
              }));
            }
          } catch (e) {
            console.error("Error parsing SSE message:", e, message);
          }
        }
      }
    } catch (e) {
      console.error("Failed to send message or process stream:", e);

      // Update streaming message with error
      setStreamingMessage(prev => 
        prev ? { ...prev, content: `Error: ${e.message}`, isError: true } : null
      );
    } finally {
      setIsSending(false);
    }
  }

  // Handle clicking a suggestion
  const handleSuggestionClick = (suggestionText) => {
    handleSend(suggestionText);
  };

  const inputRef = useRef(null);

  return (
    <div className="flex flex-col h-[100vh] w-full max-w-full overflow-x-hidden bg-zinc-50 dark:bg-zinc-900">
      {/* Chat messages area */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-6 py-4 max-w-3xl w-full mx-auto">
        <div className="flex flex-col gap-3">
          {loading ? (
            <div className="flex justify-center items-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-zinc-500"></div>
            </div>
          ) : messages.length === 0 && !streamingMessage ? (
            <div className="flex flex-col items-center justify-center text-center text-zinc-500 mt-12">
              <img
                src={logo}
                alt="Espresso Bot Logo"
                className="mx-auto mt-6 mb-2 h-96 w-96 object-contain drop-shadow-lg"
                draggable="false"
              />
              <Text>Start a new conversation by sending a message</Text>
            </div>
          ) : (
            <>
              {/* Render all messages */}
              {messages.map((msg, i) => (
                <div
                  key={msg.id || i}
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
                        initials="🤖"
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
                      {msg.timestamp && !msg.status && (
                        <span className="whitespace-nowrap">
                          {formatTimestamp(msg.timestamp)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Render streaming message if present */}
              {streamingMessage && (
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0">
                    <Avatar
                      className="size-8 bg-blue-100 dark:bg-blue-900/30"
                      alt="ShopifyBot"
                      initials="🤖"
                    />
                  </div>

                  <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded-tl-none">
                    <div className="w-full break-words prose dark:prose-invert prose-sm max-w-none">
                      <MarkdownRenderer isAgent={true}>
                        {streamingMessage.content || ""}
                      </MarkdownRenderer>
                      {streamingMessage.isStreaming && !streamingMessage.isError && (
                        <span className="inline-block ml-1 w-2 h-4 bg-current animate-pulse" />
                      )}
                    </div>
                    <div className="text-xs mt-2 flex items-center justify-end gap-2 text-zinc-500 dark:text-zinc-400">
                      {streamingMessage.isStreaming && !streamingMessage.isError && (
                        <span className="flex items-center">
                          <Loader2 className="h-3 w-3 animate-spin mr-1" />
                          Generating...
                        </span>
                      )}
                      {streamingMessage.timestamp && (
                        <span className="whitespace-nowrap">
                          {formatTimestamp(streamingMessage.timestamp)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} className="h-4" />
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
                variant="outline"
                size="sm"
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
            ref={inputRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              if (e.target.value.trim() !== "" && suggestions.length > 0) {
                setSuggestions([]);
              }
            }}
            placeholder="Type a message..."
            className="flex-1 min-h-[60px] max-h-36 resize-y leading-tight py-2.5"
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
            className="h-[44px] px-3.5 py-2 min-w-[44px] sm:min-w-[80px] flex items-center justify-center"
            disabled={isSending || !input.trim()}
          >
            {isSending ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
            <span className="ml-2 hidden sm:inline">Send</span>
          </Button>
        </form>
      </div>
    </div>
  );
}

export default StreamingChatPage;