import React, { useEffect, useRef, useState } from "react";
import { useFetcher, useNavigate } from '@remix-run/react'; // Added useNavigate
import { Textarea } from "@common/textarea";
import { Button } from "@common/button";
import { format } from "date-fns";
import { Loader2, Send, ImageIcon, X } from "lucide-react";
import { MarkdownRenderer } from "@components/chat/MarkdownRenderer";
import { TaskProgress } from "@components/chat/TaskProgress";
import { Text, TextLink } from "@common/text";
import { Avatar } from "@common/avatar";
import logo from "../../../static/EspressoBotLogo.png";
// Form from react-router-dom is not needed for Remix fetcher based submission
// import { Form } from "react-router-dom"; 

// Helper hook for debouncing (can be kept if typeahead suggestions are re-enabled later)
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

// refreshConversations prop has been removed from here as per previous steps.
function StreamingChatPage({ convId, initialMessages = [] }) { 
  const fetcher = useFetcher();
  const navigate = useNavigate(); 
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  // const [loading, setLoading] = useState(false); // Old loading state, fetcher handles its own
  const [activeConv, setActiveConv] = useState(convId); // Can be null for new chats
  const [suggestions, setSuggestions] = useState([]);
  const [streamingMessage, setStreamingMessage] = useState(null); // Restored for actual streaming
  const [toolCallStatus, setToolCallStatus] = useState("");
  const [currentTasks, setCurrentTasks] = useState([]);
  const [imageAttachment, setImageAttachment] = useState(null);
  const [imageUrl, setImageUrl] = useState("");
  const [showImageUrlInput, setShowImageUrlInput] = useState(false);
  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null); // For EventSource streaming
  const inputRef = useRef(null);
  const imageInputRef = useRef(null); // For file input dialog

  // Update messages and activeConv when props change (e.g., new conversation selected)
  useEffect(() => {
    setMessages(initialMessages || []);
    setActiveConv(convId);
    // Reset suggestions or load them if they are part of initialMessages
    const lastMessage = initialMessages?.[initialMessages.length - 1];
    if (lastMessage?.role === 'assistant' && lastMessage.suggestions) {
      setSuggestions(lastMessage.suggestions);
    } else {
      setSuggestions([]);
    }
  }, [convId, initialMessages]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]); // Removed streamingMessage from deps for now

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
    // This function might need to be adapted if fetcher supports cancellation,
    // or if a separate interrupt mechanism is implemented for Remix actions.
    // For now, it might primarily clear local UI state.
    // if (readerRef.current) { // Old stream reader
    //   try {
    //     await readerRef.current.cancel();
    //     readerRef.current = null;
    //   } catch (error) {
    //     console.log("Reader already closed");
    //   }
    // }
    
    // setIsSending(false); // Now derived from fetcher.state
    setStreamingMessage(null); // Clear any residual streaming UI
    setCurrentTasks([]);
    setToolCallStatus("");
    
    // Optionally send an interrupt signal to the backend (if backend supports it for non-streaming actions)
    // This part is less relevant for non-streaming actions.
    // try {
    //   await fetch('/api/interrupt', { // This endpoint would need to exist in Remix
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({ conv_id: activeConv })
    //   });
    // } catch (error) {
    //   console.log("Failed to send interrupt signal:", error);
    // }
    console.warn("Interrupt for non-streaming actions needs review.");
  };

  // Clean up event source on unmount or when conversation changes
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [activeConv]); // Also close if activeConv changes, to prevent streaming to wrong convo

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


  // Handle sending a message (initiates non-streaming POST to /api/chat, then potentially streaming)
  const handleSend = async (messageContent = input) => {
    const textToSend = typeof messageContent === "string" ? messageContent.trim() : input.trim();

    if (!textToSend && !imageAttachment) return;
    if (fetcher.state !== 'idle') return;

    // Finalize any previous streaming message before sending a new one
    if (streamingMessage) {
      setMessages(prev => [...prev, { ...streamingMessage, isStreaming: false, id: streamingMessage.id || `streaming-complete-${Date.now()}`}]);
      setStreamingMessage(null);
    }
    // Close any active EventSource connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    // Optimistically add user's message
    const userMessage = {
      id: `temp-user-${Date.now()}`,
      role: "user",
      content: textToSend,
      createdAt: new Date().toISOString(),
      // imageAttachment: imageAttachment, // Image handling deferred for now
    };
    setMessages((prev) => [...prev, userMessage]);

    // Prepare FormData for fetcher to submit to /api/chat
    const formData = new FormData();
    formData.append('message', textToSend);
    if (activeConv) { // activeConv here is the convId from prop
      formData.append('conv_id', activeConv.toString());
    }

    if (imageAttachment) {
      console.warn("Image attachment sending via /api/chat is deferred.");
    }
    
    if (imageAttachment) {
      if (imageAttachment.file) { // Prioritize file if both somehow exist
        formData.append('image_file', imageAttachment.file, imageAttachment.file.name);
        console.log("Image file prepared for FormData:", imageAttachment.file.name);
      } else if (imageAttachment.url) {
        formData.append('image_url', imageAttachment.url);
        console.log("Image URL prepared for FormData:", imageAttachment.url);
      }
      // Clearing imageAttachment is handled in the useEffect for fetcher.data
    }
    
    // Submit to /api/chat. This action will save the user message and
    // return conv_id, which then triggers the EventSource connection.
    fetcher.submit(formData, { method: 'post', action: '/api/chat', encType: 'multipart/form-data' });

    setInput('');
    setSuggestions([]);
    // Image state can be cleared here or after fetcher.data confirms processing.
    // Let's clear it after fetcher.data in the effect below.
  };

  // Effect to handle fetcher data (response from /api/chat) AND initiate streaming
  useEffect(() => {
    if (fetcher.data && fetcher.state === 'idle') {
      const { conv_id: returnedConvId, suggestions: newSuggestions } = fetcher.data;
      // Note: We IGNORE `fetcher.data.response` from /api/chat because streaming will provide it.
      
      const wasNewChatInitiation = !activeConv; // Was this component loaded for a new chat?
      let navigatedToNewChat = false;

      if (returnedConvId && returnedConvId !== activeConv) {
        setActiveConv(returnedConvId); // Update activeConv state immediately
        if (wasNewChatInitiation) {
          navigate(`/c/${returnedConvId}`);
          navigatedToNewChat = true; // Flag that navigation has occurred for a new chat
        }
      }
      
      const currentConvIdForStream = returnedConvId || activeConv;

      if (newSuggestions) {
        setSuggestions(newSuggestions);
      }
      
      setImageAttachment(null);
      setImageUrl("");
      setShowImageUrlInput(false);
      
      // Only start EventSource if we haven't just navigated away for a new chat,
      // or if the stream is for the ID we are now on (even if navigated).
      // If navigatedToNewChat is true, this component instance might be about to unmount
      // or its props will re-align. The EventSource should ideally be for the *new* page context.
      // However, the current logic will set up EventSource using currentConvIdForStream,
      // which should be correct even after navigation, as activeConv is updated.
      // The main concern is starting an EventSource for a component instance that's being replaced.
      // If navigation is quick, this instance might not even finish setting up the stream.
      // For simplicity, we proceed if currentConvIdForStream is valid.
      // The cleanup effect for activeConv changing should handle stale EventSources.

      if (currentConvIdForStream) {
        const lastUserMessage = messages.filter(m => m.role === 'user').pop();
        const userMessageContentForStream = lastUserMessage?.content || '';

        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }
        
        const streamUrl = `/api/chat.stream?conv_id=${currentConvIdForStream}&message=${encodeURIComponent(userMessageContentForStream)}`;
        eventSourceRef.current = new EventSource(streamUrl);
        
        setStreamingMessage({ 
          id: 'streaming-msg-' + Date.now(), 
          role: 'assistant', 
          content: '', 
          createdAt: new Date().toISOString(), 
          isStreaming: true, 
          isError: false 
        });

        eventSourceRef.current.onopen = () => {
          console.log("EventSource connected for streaming.");
        };

        eventSourceRef.current.onmessage = (event) => {
          setStreamingMessage(prev => {
            if (!prev || !prev.isStreaming) return prev; 
            return { ...prev, content: prev.content + event.data };
          });
        };

        eventSourceRef.current.onerror = () => {
          console.error("EventSource error.");
          setStreamingMessage(prev => {
            if (!prev) return null;
            return { ...prev, isStreaming: false, isError: true, content: prev.content + "\n\nError: Could not stream full response." };
          });
          if (eventSourceRef.current) eventSourceRef.current.close();
        };
      }
    }
  }, [fetcher.data, fetcher.state, activeConv, messages, navigate]);

  // isSending should reflect both fetcher activity AND active streaming
  const isSending = fetcher.state === 'submitting' || fetcher.state === 'loading' || (streamingMessage?.isStreaming || false);

  // Handle clicking a suggestion
  const handleSuggestionClick = (suggestionText) => {
    setInput(suggestionText); // Set input to suggestion
    handleSend(suggestionText); // Send immediately
  };


  return (
    <div className="flex flex-col h-[90vh] w-full max-w-full overflow-x-hidden bg-zinc-50 dark:bg-zinc-900">
      {/* Chat messages area */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-4 sm:px-6 py-4 max-w-3xl w-full mx-auto">
        <div className="flex flex-col gap-3">
          {/* Old loading spinner is removed. UI reflects `isSending` for input disabling. */}
          {messages.length === 0 && !streamingMessage && !isSending ? (
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
            messages.map((msg, i) => (
              <div
                key={msg.id || i} // Use msg.id if available (from DB), else index for optimistic
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
                      alt="EspressoBot" // Consistent naming
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
                    {/* Image display logic can remain for optimistic user messages */}
                    {msg.imageAttachment && (
                      <div className="mb-3">
                        {msg.imageAttachment.dataUrl && (
                          <img 
                            src={msg.imageAttachment.dataUrl} 
                            alt="User uploaded" 
                            className="max-h-64 rounded-lg object-contain"
                          />
                        )}
                        {/* URL image display can also remain if needed */}
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
                    {/* msg.status is not used with fetcher, optimistic updates are immediate */}
                    {msg.createdAt && ( 
                      <span className="whitespace-nowrap">
                        {formatTimestamp(msg.createdAt)} 
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
          {/* Task Progress Display can be kept if non-streaming response might include tasks */}
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
                  alt="EspressoBot"
                  initials="🤖"
                />
              </div>
              <div 
                className="max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 rounded-tl-none"
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
                  {streamingMessage.createdAt && (
                    <span className="whitespace-nowrap">
                      {formatTimestamp(streamingMessage.createdAt)}
                    </span>
                  )}
                </div>
              </div>
            </div>
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
                disabled={isSending} // Disable suggestions while sending
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