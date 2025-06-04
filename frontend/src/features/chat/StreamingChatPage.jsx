import React, { useEffect, useRef, useState } from "react";
import { Textarea } from "@common/textarea";
import { Button } from "@common/button";
import { format } from "date-fns";
import { Loader2, Send, ImageIcon, X } from "lucide-react";
import { MarkdownRenderer } from "@components/chat/MarkdownRenderer";
import { TaskProgress } from "@components/chat/TaskProgress";
import { Text, TextLink } from "@common/text";
import { Avatar } from "@common/avatar";
import logo from "../../../static/EspressoBotLogo.png";
import { Form } from "react-router-dom";

// Helper hook for debouncing
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
}

function StreamingChatPage({ convId, refreshConversations }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [activeConv, setActiveConv] = useState(convId);
  const [suggestions, setSuggestions] = useState([]);
  const [streamingMessage, setStreamingMessage] = useState(null);
  const [toolCallStatus, setToolCallStatus] = useState("");
  const [currentTasks, setCurrentTasks] = useState([]);
  const [imageAttachment, setImageAttachment] = useState(null);
  const [imageUrl, setImageUrl] = useState("");
  const [showImageUrlInput, setShowImageUrlInput] = useState(false);
  const [useAgent, setUseAgent] = useState(false);
  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null);
  const readerRef = useRef(null);
  const inputRef = useRef(null);
  const imageInputRef = useRef(null);

  // Fetch messages for selected conversation
  useEffect(() => {
    if (!convId) {
      setMessages([]);
      setSuggestions([]);
      setActiveConv(null);
      return;
    }
    setLoading(true);
    fetch(`/api/conversations/${convId}`)
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

  // Interrupt function to stop ongoing agent tasks
  const handleInterrupt = async () => {
    if (readerRef.current) {
      try {
        await readerRef.current.cancel();
        readerRef.current = null;
      } catch (error) {
        console.log("Reader already closed");
      }
    }
    
    setIsSending(false);
    setStreamingMessage(null);
    setCurrentTasks([]);
    setToolCallStatus("");
    
    // Optionally send an interrupt signal to the backend
    try {
      await fetch('/api/interrupt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conv_id: activeConv })
      });
    } catch (error) {
      console.log("Failed to send interrupt signal:", error);
    }
  };

  // Clean up event source on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (readerRef.current) {
        readerRef.current.cancel();
      }
    };
  }, []);

  // Handle image paste from clipboard
  useEffect(() => {
    const handlePaste = (e) => {
      if (e.clipboardData && e.clipboardData.items) {
        const items = e.clipboardData.items;
        
        for (let i = 0; i < items.length; i++) {
          if (items[i].type.indexOf('image') !== -1) {
            const blob = items[i].getAsFile();
            handleImageAttachment(blob);
            e.preventDefault();
            break;
          }
        }
      }
    };

    document.addEventListener('paste', handlePaste);
    return () => {
      document.removeEventListener('paste', handlePaste);
    };
  }, []);

  // Function to handle image attachments
  const handleImageAttachment = (file) => {
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setImageAttachment({
          dataUrl: e.target.result,
          file: file
        });
        setShowImageUrlInput(false);
        setImageUrl("");
      };
      reader.readAsDataURL(file);
    }
  };

  // Handle image upload button click
  const handleImageUploadClick = () => {
    imageInputRef.current?.click();
  };

  // Remove image attachment
  const removeImageAttachment = () => {
    setImageAttachment(null);
  };

  // Toggle URL input visibility
  const toggleImageUrlInput = () => {
    setShowImageUrlInput(!showImageUrlInput);
    if (imageAttachment) {
      setImageAttachment(null);
    }
  };

  // Handle URL input change
  const handleImageUrlChange = (e) => {
    setImageUrl(e.target.value);
  };

  // Add URL as attachment
  const addImageUrl = () => {
    if (imageUrl.trim()) {
      setImageAttachment({
        url: imageUrl.trim()
      });
      setShowImageUrlInput(false);
    }
  };

  // const fetchSuggestions = async (currentInput) => {
  //   if (!currentInput.trim()) {
  //     setSuggestions([]);
  //     return;
  //   }

  //   const lastAgentMessageContent = messages
  //     .filter(msg => msg.role === 'assistant' && msg.content)
  //     .pop()?.content || "";

  //   // setSuggestionsLoading(true);
  //   try {
  //     const response = await fetch('/api/typeahead_suggestions', {
  //       method: 'POST',
  //       headers: {
  //         'Content-Type': 'application/json',
  //       },
  //       body: JSON.stringify({
  //         agent_previous_message: lastAgentMessageContent,
  //         user_current_input: currentInput,
  //       }),
  //     });
  //     if (!response.ok) {
  //       throw new Error(`HTTP error! status: ${response.status}`);
  //     }
  //     const data = await response.json();
  //     setSuggestions(data.suggestions || []);
  //   } catch (error) {
  //     console.error("Failed to fetch typeahead suggestions:", error);
  //     setSuggestions([]);
  //   } finally {
  //     // setSuggestionsLoading(false);
  //   }
  // };

  // const debouncedInput = useDebounce(input, 400);

  // useEffect(() => {
  //   if (debouncedInput.trim()) {
  //     fetchSuggestions(debouncedInput);
  //   } else {
  //     setSuggestions([]);
  //   }
  // }, [debouncedInput]);


  // Handle sending a message with streaming response
  const handleSend = async (messageContent = input) => {
    const textToSend =
      typeof messageContent === "string" ? messageContent.trim() : input.trim();

    if ((!textToSend && !imageAttachment) || isSending) return;

    // Before sending a new message, check if we have a completed streaming message
    // If so, move it to regular messages
    if (streamingMessage?.isComplete) {
      setMessages(prev => [
        ...prev,
        {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: streamingMessage.content,
          timestamp: streamingMessage.timestamp,
        }
      ]);
    }

    // Add user message to the conversation
    const userMessage = {
      role: "user",
      content: textToSend,
      timestamp: new Date().toISOString(),
      imageAttachment: imageAttachment,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    setInput('');
    setSuggestions([]);
    setCurrentTasks([]);

    // Initialize streaming message
    setStreamingMessage({
      role: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      isStreaming: true,
      isComplete: false, // Add this flag to track completion state
    });

    // Close any existing SSE connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      // Set up Server-Sent Events connection
      const fetchUrl = useAgent ? "/api/agent/run" : "/stream_chat";

      // Prepare request data
      const requestData = {
        conv_id: activeConv || undefined,
        message: textToSend,
      };

      // Add image data if present
      if (imageAttachment) {
        if (imageAttachment.dataUrl) {
          requestData.image = {
            type: "data_url",
            data: imageAttachment.dataUrl
          };
        } else if (imageAttachment.url) {
          requestData.image = {
            type: "url",
            url: imageAttachment.url
          };
        }
      }

      // Use fetch POST to start the stream
      const response = await fetch(fetchUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Get the response as a ReadableStream
      const reader = response.body.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();
      let eventData = "";
      let shouldStop = false;

      // Process the stream
      while (!shouldStop) {
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
            console.log("Received data:", data);
            // Handle title updates: refresh conversation list when title changes
            if (data.new_title) {
              refreshConversations && refreshConversations();
            }

            // Handle tool_call status updates
            if (data.tool_call) {
              const { name, status } = data.tool_call;
              let statusMessage = `Tool ${name}: ${status}`;
              if (status === "started") {
                statusMessage = `Running tool: ${name}...`;
              } else if (status === "finished" || status === "ended") {
                statusMessage = `Tool ${name} finished.`;
              } else if (status === "error") {
                statusMessage = `Error with tool: ${name}.`;
              }
              setToolCallStatus(statusMessage);
            } else if (data.content || data.delta) {
              // If new content (even if empty string from delta) arrives, clear specific tool status
              setToolCallStatus("");
            }

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

            // Handle task updates
            if (data.type === 'task_update' && data.tasks) {
              setCurrentTasks(data.tasks);
            }

            // Handle suggestions
            if (data.suggestions && Array.isArray(data.suggestions)) {
              setSuggestions(data.suggestions);
            }

            // Handle completion: mark streaming message complete and stop processing further events
            if (data.done) {
              setStreamingMessage(prev => {
                if (!prev) return null;
                return {
                  ...prev,
                  isComplete: true,
                  isStreaming: false,
                };
              });
              shouldStop = true;
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
      setToolCallStatus(""); // Clear tool status when streaming ends
      readerRef.current = null; // Clear reader reference
    }
  }

  // Handle clicking a suggestion
  const handleSuggestionClick = (suggestionText) => {
    handleSend(suggestionText);
  };

  return (
    <div className="flex flex-col h-[90vh] w-full max-w-full overflow-x-hidden bg-zinc-50 dark:bg-zinc-900">
      <div className="flex justify-end px-4 sm:px-6 py-2">
        <Button size="sm" variant={useAgent ? 'solid' : 'outline'} onClick={() => setUseAgent(!useAgent)}>
          {useAgent ? 'Agent Mode On' : 'Agent Mode Off'}
        </Button>
      </div>
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
              <Text>Start a new conversation by sending a message.
                 Visit the <TextLink href="/about">About</TextLink> page for more information and to learn how to use the bot.
              </Text>
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
                      {/* Show image attachment if present */}
                      {msg.imageAttachment && (
                        <div className="mb-3">
                          {msg.imageAttachment.dataUrl && (
                            <img 
                              src={msg.imageAttachment.dataUrl} 
                              alt="User uploaded" 
                              className="max-h-64 rounded-lg object-contain"
                            />
                          )}
                          {msg.imageAttachment.url && (
                            <img 
                              src={msg.imageAttachment.url} 
                              alt="From URL" 
                              className="max-h-64 rounded-lg object-contain"
                              onError={(e) => {
                                e.target.onerror = null;
                                e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMDAiIGZpbGw9IiNFRUVFRUUiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiM5OTk5OTkiPkltYWdlIGVycm9yPC90ZXh0Pjwvc3ZnPg==';
                              }}
                            />
                          )}
                        </div>
                      )}
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
                      {msg.timestamp && !msg.status && (
                        <span className="whitespace-nowrap">
                          {formatTimestamp(msg.timestamp)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* Task Progress Display */}
                <TaskProgress 
                  tasks={currentTasks} 
                  onInterrupt={handleInterrupt}
                  isStreaming={isSending}
                />


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

                  <div 
                    className="max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded-tl-none"
                    data-state={streamingMessage.isComplete ? "complete" : "streaming"}
                  >
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
                          {toolCallStatus ? toolCallStatus : "Generating..."}
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
          {messages.length > 0 && <div ref={messagesEndRef} className="h-4" />}
        </div>
      </div>

      {/* Input area + Suggestions, fixed at the bottom */}
      <div className="sticky bottom-0 w-full bg-zinc-50 dark:bg-zinc-900 py-3 border-t border-zinc-200 dark:border-zinc-700 z-10">
        {/* Suggestions Area */}
        {suggestions && suggestions.length > 0 && !isSending && (
          <div className="max-w-3xl w-full mx-auto px-4 mb-2 flex flex-wrap gap-2 justify-center sm:justify-start">
            {suggestions.map((suggestion, index) => (
              <Button
                outline
                key={index}
                size="sm"
                className="py-1 px-2.5 h-auto dark:bg-zinc-700 dark:hover:bg-zinc-600 border-zinc-300 dark:border-zinc-600 hover:bg-zinc-100 text-zinc-100 dark:text-zinc-200 rounded-lg text-xs cursor-alias"
                onClick={() => handleSuggestionClick(suggestion)}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        )}

        {/* Image Preview */}
        {imageAttachment && (
          <div className="max-w-3xl w-full mx-auto px-4 mb-2">
            <div className="relative inline-block">
              {imageAttachment.dataUrl && (
                <img 
                  src={imageAttachment.dataUrl} 
                  alt="Upload preview" 
                  className="h-20 rounded border dark:border-zinc-700"
                />
              )}
              {imageAttachment.url && (
                <div className="inline-flex items-center gap-2 p-2 rounded bg-zinc-100 dark:bg-zinc-800 border dark:border-zinc-700">
                  <ImageIcon className="h-4 w-4" />
                  <span className="text-xs truncate max-w-[200px]">{imageAttachment.url}</span>
                </div>
              )}
              <button 
                onClick={removeImageAttachment}
                className="absolute -top-2 -right-2 bg-zinc-200 dark:bg-zinc-700 rounded-full p-1"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          </div>
        )}

        {/* URL Input Area */}
        {showImageUrlInput && (
          <div className="max-w-3xl w-full mx-auto px-4 mb-2 flex gap-2">
            <input
              type="text"
              value={imageUrl}
              onChange={handleImageUrlChange}
              placeholder="Enter image URL"
              className="flex-1 py-1 px-2 text-sm rounded border border-zinc-300 dark:border-zinc-700 dark:bg-zinc-800"
            />
            <Button 
              size="sm" 
              outline
              onClick={addImageUrl}
              disabled={!imageUrl.trim()}
              className="py-1 px-2 h-auto"
            >
              Add
            </Button>
          </div>
        )}

        {/* Input Form */}
        <form
          className="flex max-w-3xl w-full mx-auto gap-2 px-4 items-center"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <Button
        type="button"
        plain
        onClick={imageAttachment || showImageUrlInput ? toggleImageUrlInput : handleImageUploadClick}
        className="h-9 w-9 rounded-full"
        title={imageAttachment ? "Add from URL instead" : "Add image"}
      >
        <ImageIcon />
      </Button>
      <input
              type="file"
              ref={imageInputRef}
              accept="image/*"
              onChange={(e) => handleImageAttachment(e.target.files[0])}
              className="hidden"
            />
          <Textarea
            ref={inputRef}
            value={input}
            autoCorrect="off"
            autoComplete="new-password"
            spellCheck={true}
            onChange={(e) => {
              setInput(e.target.value);
              if (e.target.value.trim() !== "" && suggestions.length > 0) {
                setSuggestions([]);
              }
            }}
            placeholder="Type a message..."
            rows={3}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <div className="flex flex-col gap-2">


            <Button
              type="submit"
              className="h-[44px] px-3.5 py-2 min-w-[44px] sm:min-w-[80px] flex items-center justify-center self-center my-auto"
              disabled={isSending || (!input.trim() && !imageAttachment)}
            >
              {isSending ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
              <span className="ml-2 hidden sm:inline">Send</span>
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default StreamingChatPage;