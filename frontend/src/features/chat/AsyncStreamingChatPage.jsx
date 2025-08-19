import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Textarea } from "@common/textarea";
import { Button } from "@common/button";
import { format } from "date-fns";
import { Loader2, Send, ImageIcon, X, Square, FileText, FileSpreadsheet, File, FileIcon, Edit2, Check, XCircle } from "lucide-react";
import { MarkdownRenderer } from "@components/chat/MarkdownRenderer";
import { Text, TextLink } from "@common/text";
import { Avatar } from "@common/avatar";
import logo from "../../../static/EspressoBotLogo.png";
import { useAsyncBackend } from "../../hooks/useAsyncBackend";

// Helper to merge server history with local UI state
const mergeServerAndLocalMessages = (serverMsgs = [], localMsgs = []) => {
  if (!Array.isArray(serverMsgs)) serverMsgs = [];
  if (!Array.isArray(localMsgs)) localMsgs = [];

  const byId = new Map();
  const result = [];

  // First, add all server messages (authoritative when IDs exist)
  for (const m of serverMsgs) {
    if (m && m.id) byId.set(m.id, true);
    result.push(m);
  }

  // Then, add any local messages that are not present on server
  for (const m of localMsgs) {
    if (m && m.id && byId.has(m.id)) continue;

    if (m && m.role === 'user' && !m.id) {
      const dupUser = result.some(x => x.role === 'user' && String(x.content || '') === String(m.content || ''));
      if (!dupUser) result.push(m);
      continue;
    }

    if (m && m.role === 'assistant') {
      const dupAssistant = result.some(x => x.role === 'assistant' && String(x.content || '') === String(m.content || ''));
      if (dupAssistant) continue;
    }

    if (m) result.push(m);
  }

  return result;
};

function AsyncStreamingChatPage({ convId, onTopicUpdate, onNewConversation }) {
  const location = useLocation();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [activeConv, setActiveConv] = useState(convId);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [imageAttachment, setImageAttachment] = useState(null);
  const [fileAttachment, setFileAttachment] = useState(null);
  const [imageUrl, setImageUrl] = useState("");
  const [showImageUrlInput, setShowImageUrlInput] = useState(false);
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editingContent, setEditingContent] = useState("");
  const [isEditSaving, setIsEditSaving] = useState(false);
  const [textareaRows, setTextareaRows] = useState(2);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const imageInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const hasProcessedInitialMessage = useRef(false);

  const {
    sendAsyncMessage,
    cancelTask,
    loading,
    taskStatus,
    taskResponse,
    taskProgress,
    error,
  } = useAsyncBackend();

  // Scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, taskResponse]);

  // Handle initial attachments from navigation state
  useEffect(() => {
    const initialAttachments = location.state?.imageAttachment || location.state?.fileAttachment;
    if (initialAttachments && !hasProcessedInitialMessage.current) {
      if (location.state.imageAttachment) {
        setImageAttachment(location.state.imageAttachment);
      }
      if (location.state.fileAttachment) {
        setFileAttachment(location.state.fileAttachment);
      }
    }
  }, [location.state]);

  // Fetch messages for selected conversation
  useEffect(() => {
    if (!convId) {
      if (activeConv) {
        console.log('AsyncChat: convId is null but activeConv exists, not clearing. activeConv:', activeConv);
        return;
      }
      setMessages([]);
      setActiveConv(null);
      hasProcessedInitialMessage.current = false;
      return;
    }

    if (convId === activeConv) {
      console.log('AsyncChat: convId unchanged, skipping fetch. convId:', convId);
      return;
    }

    console.log('AsyncChat: Fetching messages for conversation:', convId);
    setActiveConv(convId);
    fetchConversationMessages(convId);
  }, [convId]);

  // Fetch conversation messages from server
  const fetchConversationMessages = async (conversationId) => {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`/api/conversations/${conversationId}`, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('AsyncChat: Loaded conversation:', data);
        
        if (data.messages && Array.isArray(data.messages)) {
          const formattedMessages = data.messages.map(msg => ({
            id: msg.id,
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp || msg.created_at,
            agent: msg.agent,
          }));
          
          setMessages(formattedMessages);
          console.log('AsyncChat: Set messages from server:', formattedMessages.length);
        }
      }
    } catch (error) {
      console.error('AsyncChat: Error fetching conversation:', error);
      setMessages([]);
    }
  };

  // Handle sending messages
  const handleSendMessage = async () => {
    const textToSend = input.trim();
    if (!textToSend && !imageAttachment && !fileAttachment) return;

    const userMessage = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: textToSend,
      timestamp: new Date().toISOString(),
    };

    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setImageAttachment(null);
    setFileAttachment(null);

    try {
      // Send async message
      const result = await sendAsyncMessage(textToSend, activeConv);
      setCurrentTaskId(result.task_id);
      
      // Update conversation ID if this is a new conversation
      if (!activeConv && result.conversation_id) {
        setActiveConv(result.conversation_id);
        if (onNewConversation) {
          onNewConversation(result.conversation_id);
        }
      }
    } catch (err) {
      console.error('AsyncChat: Send message error:', err);
      // Add error message
      const errorMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `❌ Error sending message: ${err.message}`,
        timestamp: new Date().toISOString(),
        agent: "system",
      };
      setMessages(prev => [...prev, errorMessage]);
    }
  };

  // Add task response as assistant message when completed
  useEffect(() => {
    if (taskStatus === 'completed' && taskResponse && !loading) {
      const assistantMessage = {
        id: `response-${Date.now()}`,
        role: "assistant",
        content: taskResponse,
        timestamp: new Date().toISOString(),
        agent: "orchestrator",
      };
      
      setMessages(prev => {
        // Check if we already have this response
        const hasResponse = prev.some(m => 
          m.role === 'assistant' && m.content === taskResponse
        );
        if (hasResponse) return prev;
        
        return [...prev, assistantMessage];
      });

      // Update conversation title if this was a new conversation
      if (onTopicUpdate && activeConv) {
        onTopicUpdate(activeConv, "Chat", "Async conversation");
      }
    }
  }, [taskStatus, taskResponse, loading, activeConv, onTopicUpdate]);

  // Handle input changes and auto-resize
  const handleInputChange = (e) => {
    setInput(e.target.value);
    
    // Auto-resize textarea
    const lineHeight = 24;
    const padding = 16;
    const lines = e.target.value.split('\n').length;
    const newRows = Math.max(2, Math.min(6, lines));
    setTextareaRows(newRows);
  };

  // Handle key press
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // File upload handlers
  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        setImageAttachment({
          file,
          dataUrl: reader.result,
          name: file.name,
          size: file.size,
        });
      };
      reader.readAsDataURL(file);
    }
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        setFileAttachment({
          file,
          dataUrl: reader.result,
          name: file.name,
          size: file.size,
          type: file.type,
        });
      };
      reader.readAsDataURL(file);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'text-yellow-600';
      case 'running': return 'text-blue-600';
      case 'completed': return 'text-green-600';
      case 'failed': return 'text-red-600';
      case 'cancelled': return 'text-gray-600';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !loading && (
          <div className="text-center text-gray-500 mt-8">
            <h3 className="text-lg font-semibold mb-2">🚀 EspressoBot Async Chat</h3>
            <p>Start a conversation with instant responses and background processing!</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div key={message.id || index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-3xl ${message.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-100'} rounded-lg p-3`}>
              {message.role === 'assistant' && (
                <div className="flex items-center mb-2">
                  <Avatar src={logo} className="w-6 h-6 mr-2" />
                  <span className="text-sm font-semibold">
                    EspressoBot {message.agent && `(${message.agent})`}
                  </span>
                </div>
              )}
              
              <div className="prose prose-sm max-w-none">
                {message.role === 'assistant' ? (
                  <MarkdownRenderer content={message.content} />
                ) : (
                  <Text>{message.content}</Text>
                )}
              </div>
              
              {message.timestamp && (
                <div className="text-xs opacity-70 mt-2">
                  {format(new Date(message.timestamp), 'MMM d, h:mm a')}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Task Status Display */}
        {(loading || taskStatus) && (
          <div className="flex justify-start">
            <div className="max-w-3xl bg-blue-50 border border-blue-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center">
                  <Avatar src={logo} className="w-6 h-6 mr-2" />
                  <span className="font-semibold">EspressoBot</span>
                </div>
                
                <div className={`text-sm font-semibold ${getStatusColor(taskStatus)}`}>
                  {loading ? 'Starting...' : taskStatus?.toUpperCase()}
                </div>
              </div>

              {/* Progress Bar */}
              {taskStatus === 'running' && (
                <div className="mb-3">
                  <div className="flex justify-between text-sm text-gray-600 mb-1">
                    <span>Processing with real agents...</span>
                    <span>{Math.round(taskProgress * 100)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${taskProgress * 100}%` }}
                    ></div>
                  </div>
                </div>
              )}

              {/* Cancel Button */}
              {taskStatus === 'running' && currentTaskId && (
                <div className="flex justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => cancelTask(currentTaskId)}
                    className="text-red-600 border-red-200"
                  >
                    <X className="w-4 h-4 mr-1" />
                    Cancel
                  </Button>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="text-red-600 text-sm">
                  <strong>Error:</strong> {error}
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t bg-gray-50 p-4">
        {/* Attachments */}
        {(imageAttachment || fileAttachment) && (
          <div className="mb-3 p-2 bg-white rounded border">
            {imageAttachment && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">📷 {imageAttachment.name}</span>
                <Button variant="ghost" size="sm" onClick={() => setImageAttachment(null)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
            )}
            {fileAttachment && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">📄 {fileAttachment.name}</span>
                <Button variant="ghost" size="sm" onClick={() => setFileAttachment(null)}>
                  <X className="w-4 h-4" />
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Input Controls */}
        <div className="flex items-end space-x-2">
          <div className="flex-1">
            <Textarea
              ref={inputRef}
              value={input}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Message EspressoBot (async processing enabled)..."
              rows={textareaRows}
              className="resize-none"
            />
          </div>
          
          <div className="flex space-x-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => imageInputRef.current?.click()}
              disabled={loading}
            >
              <ImageIcon className="w-4 h-4" />
            </Button>
            
            <Button
              variant="ghost"
              size="sm" 
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
            >
              <FileIcon className="w-4 h-4" />
            </Button>
            
            <Button
              onClick={handleSendMessage}
              disabled={loading || (!input.trim() && !imageAttachment && !fileAttachment)}
              size="sm"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>

        {/* Hidden file inputs */}
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageUpload}
          className="hidden"
        />
        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileUpload}
          className="hidden"
        />
      </div>
    </div>
  );
}

export default AsyncStreamingChatPage;