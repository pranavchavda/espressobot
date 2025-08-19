import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { flushSync } from "react-dom";
import { Textarea } from "@common/textarea";
import { Button } from "@common/button";
import { format } from "date-fns";
import { Loader2, Send, ImageIcon, X, Square, FileText, FileSpreadsheet, File, FileIcon, Edit2, Check, XCircle } from "lucide-react";
import { MarkdownRenderer } from "@components/chat/MarkdownRenderer";
import { UnifiedTaskDisplay } from "@components/chat/UnifiedTaskDisplay";
import { Text, TextLink } from "@common/text";
import { Avatar } from "@common/avatar";
import logo from "../../../static/EspressoBotLogo.png";
import { ApprovalRequest } from "@components/chat/ApprovalRequest";


  // Helper to merge server history with local UI state while avoiding duplicates
  // - Prefers server messages when IDs exist
  // - Keeps locally injected user messages that server may not yet have persisted
  // - Dedupes assistant messages by identical content
  const mergeServerAndLocalMessages = (serverMsgs = [], localMsgs = []) => {
    if (!Array.isArray(serverMsgs)) serverMsgs = [];
    if (!Array.isArray(localMsgs)) localMsgs = [];

    // Build maps for quick lookup
    const byId = new Map();
    const result = [];

    // First, add all server messages (authoritative when IDs exist)
    for (const m of serverMsgs) {
      if (m && m.id) byId.set(m.id, true);
      result.push(m);
    }

    // Then, add any local messages that are not present on server
    for (const m of localMsgs) {
      // If server already has this id, skip
      if (m && m.id && byId.has(m.id)) continue;

      // If message is a locally injected user message without id, keep it if not clearly duplicated
      if (m && m.role === 'user' && !m.id) {
        const dupUser = result.some(x => x.role === 'user' && String(x.content || '') === String(m.content || ''));
        if (!dupUser) result.push(m);
        continue;
      }

      // Avoid duplicating assistant messages by same content (common during streaming vs persisted)
      // Respect debug flag via URL/localStorage to disable dedup when investigating rendering issues
      if (m && m.role === 'assistant') {
        const noDedup = (typeof window !== 'undefined' && (new URLSearchParams(window.location.search)).get('noDedup') === '1') ||
                        (typeof localStorage !== 'undefined' && localStorage.getItem('noDedup') === '1');
        if (!noDedup) {
          const dupAssistant = result.some(x => x.role === 'assistant' && String(x.content || '') === String(m.content || ''));
          if (dupAssistant) continue;
        }
      }

      // Fallback: add message
      if (m) result.push(m);
    }

    return result;
  };

function StreamingChatPage({ convId, onTopicUpdate, onNewConversation }) {
  const location = useLocation();
  // Debug flag: disable deduplication via ?noDedup=1 or localStorage.setItem('noDedup','1')
  const debugNoDedup = (new URLSearchParams(location.search)).get('noDedup') === '1' || localStorage.getItem('noDedup') === '1';
  // Feature flag: orchestrator SSE
  const orchestratorEnabled = (new URLSearchParams(location.search)).get('orchestrator') === '1' || localStorage.getItem('orchestrator') === '1';
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [activeConv, setActiveConv] = useState(convId);
  const [suggestions, setSuggestions] = useState([]);
  const [streamingMessage, setStreamingMessageState] = useState(null);
  const streamingMessageRef = useRef(null); // Track streaming message in a ref
  const messageFinalizedRef = useRef(false); // Track if message was already finalized
  const pendingServerHistoryRef = useRef(null); // buffer server history while streaming
  const lastFinalizedContentRef = useRef(null); // Track last finalized content to prevent duplicates
  const messageIdsRef = useRef(new Set()); // Track all message IDs to prevent duplicates
  const processingResponseRef = useRef(false); // Track if we're processing a response
  const lastProcessedMessageRef = useRef(null); // Track the last processed message
  const messageQueueRef = useRef([]); // Queue for messages to be added
  const isProcessingQueueRef = useRef(false); // Track if we're processing the queue
  
  // Custom setter that updates both state and ref
  const setStreamingMessage = (value) => {
    if (typeof value === 'function') {
      setStreamingMessageState(prev => {
        const newValue = value(prev);
        streamingMessageRef.current = newValue;
        return newValue;
      });
    } else {
      streamingMessageRef.current = value;
      setStreamingMessageState(value);
    }
  };
  
  // Process message queue to ensure messages are added sequentially
  const processMessageQueue = () => {
    if (isProcessingQueueRef.current || messageQueueRef.current.length === 0) {
      return;
    }
    
    isProcessingQueueRef.current = true;
    const message = messageQueueRef.current.shift();
    
    setMessages(prev => {
      // Check for duplicates
      const isDuplicate = !debugNoDedup && prev.some(m => 
        m.id === message.id || 
        (m.role === 'assistant' && message.role === 'assistant' && 
         (m.content || '').trim() === (message.content || '').trim())
      );
      
      if (isDuplicate) {
        console.log('[DEBUG] Queue: Duplicate message detected, skipping');
        isProcessingQueueRef.current = false;
        // Process next message in queue
        setTimeout(processMessageQueue, 0);
        return prev;
      }
      
      console.log('[DEBUG] Queue: Adding message to state');
      isProcessingQueueRef.current = false;
      // Process next message in queue
      setTimeout(processMessageQueue, 0);
      return [...prev, message];
    });
  };
  
  // Helper to add message to queue
  const queueMessage = (message) => {
    messageQueueRef.current.push(message);
    processMessageQueue();
  };
  
  const [toolCallStatus, setToolCallStatus] = useState(""); // Can be repurposed or used for general status
  const [currentTasks, setCurrentTasks] = useState([]);
  const [imageAttachment, setImageAttachment] = useState(null);
  const [fileAttachment, setFileAttachment] = useState(null);
  const [plannerStatus, setPlannerStatus] = useState("");
  const [dispatcherStatus, setDispatcherStatus] = useState("");
  const [synthesizerStatus, setSynthesizerStatus] = useState("");
  const [currentPlan, setCurrentPlan] = useState(null);
  const [imageUrl, setImageUrl] = useState("");
  const [showImageUrlInput, setShowImageUrlInput] = useState(false);
  // Check if we're in multi-agent mode from the build environment
  const isMultiAgentMode = import.meta.env.VITE_USE_MULTI_AGENT === 'true';
  const [useBasicAgent, setUseBasicAgent] = useState(!isMultiAgentMode);
  const [hasShownTasks, setHasShownTasks] = useState(false);
  const [taskMarkdown, setTaskMarkdown] = useState(null);
  const [agentProcessingStatus, setAgentProcessingStatus] = useState("");
  const [pendingApproval, setPendingApproval] = useState(null);
  const [approvalHistory, setApprovalHistory] = useState([]);
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editingContent, setEditingContent] = useState("");
  const [isEditSaving, setIsEditSaving] = useState(false);
  const [textareaRows, setTextareaRows] = useState(2);
  const messagesEndRef = useRef(null);
  const eventSourceRef = useRef(null);
  const readerRef = useRef(null);
  const inputRef = useRef(null);
  const imageInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const hasProcessedInitialMessage = useRef(false);

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
      // Don't clear messages if we have an active conversation
      // This happens when we create a new conversation and the parent hasn't updated yet
      if (activeConv) {
        console.log('FRONTEND: convId is null but activeConv exists, not clearing. activeConv:', activeConv);
        return;
      }
      setMessages([]);
      setSuggestions([]);
      console.warn('FRONTEND: convId is null in useEffect[convId]. Clearing messages/suggestions. convId:', convId);
      setCurrentTasks([]); // convId null means switching out, safe clear
      setHasShownTasks(false);
      setTaskMarkdown(null);
      setActiveConv(null);
      hasProcessedInitialMessage.current = false; // Reset flag for new conversations
      return;
    }
    // Clear task markdown when switching conversations
    setTaskMarkdown(null);
    // Also clear any stale task markdown that doesn't match the new conversation
    setTaskMarkdown(prev => {
      if (prev && String(prev.conversation_id) !== String(convId)) {
        console.log('FRONTEND: Clearing stale task markdown from conversation:', prev.conversation_id);
        return null;
      }
      return prev;
    });
    // Update activeConv when convId changes
    setActiveConv(convId);
    hasProcessedInitialMessage.current = false; // Reset flag for new conversations
    setLoading(true);
    const token = localStorage.getItem('authToken');
    
    const fetchConversationWithRetry = async (retryCount = 0) => {
      try {
        const res = await fetch(`/api/conversations/${convId}`, {
          headers: {
            'Authorization': token ? `Bearer ${token}` : '',
            'User-ID': '1'  // TODO: Get from authenticated user
          }
        });
        console.log('[DEBUG] Conversation fetch response status:', res.status, 'retry:', retryCount);
        const data = await res.json();
        const { messages: fetchedMessages, tasks: persistedTasks, taskMarkdown: fetchedTaskMarkdown } = data;
        console.log('[DEBUG] Conversation data received. Messages:', fetchedMessages?.length || 0, 'Tasks:', persistedTasks?.length || 0);
        
        // If conversation exists but has no messages and this is a retry, wait and try again
        if (res.ok && (!fetchedMessages || fetchedMessages.length === 0) && retryCount < 2) {
          console.log('[DEBUG] Empty conversation detected, retrying in 300ms... attempt:', retryCount + 1);
          return new Promise(resolve => {
            setTimeout(() => {
              fetchConversationWithRetry(retryCount + 1).then(resolve);
            }, 300);
          });
        }
        
        return { fetchedMessages, persistedTasks, fetchedTaskMarkdown };
      } catch (error) {
        if (retryCount < 2) {
          console.log('[DEBUG] Fetch error, retrying in 300ms... attempt:', retryCount + 1, 'error:', error.message);
          return new Promise(resolve => {
            setTimeout(() => {
              fetchConversationWithRetry(retryCount + 1).then(resolve);
            }, 300);
          });
        }
        throw error;
      }
    };
    
    fetchConversationWithRetry()
      .then((result) => {
        if (!result) {
          return; // Retry in progress
        }
        const { fetchedMessages, persistedTasks, fetchedTaskMarkdown } = result;
        console.log('[DEBUG] Using conversation data. Messages:', fetchedMessages?.length || 0, 'Tasks:', persistedTasks?.length || 0);
        // If we are in the middle of streaming, stash the server history for merge after 'done'
        const isCurrentlyStreaming = !!streamingMessageRef.current?.isStreaming;
        if (isCurrentlyStreaming) {
          console.log('FRONTEND: Stashing server history during streaming for later merge. Count:', fetchedMessages?.length || 0);
          pendingServerHistoryRef.current = fetchedMessages || [];
        } else {
          // Merge immediately with local UI to avoid flicker/duplication
          setMessages(prev => mergeServerAndLocalMessages(fetchedMessages || [], prev));
        }
        setCurrentTasks(persistedTasks);
        setHasShownTasks(persistedTasks && persistedTasks.length > 0); // Set based on existing tasks
        setActiveConv(convId);
        
        // Set task markdown if it exists
        if (fetchedTaskMarkdown) {
          console.log('FRONTEND: Setting task markdown for conversation:', convId, 'markdown length:', fetchedTaskMarkdown.markdown?.length);
          setTaskMarkdown(fetchedTaskMarkdown);
        } else {
          console.log('FRONTEND: No task markdown fetched for conversation:', convId);
        }
        
        const lastMessage = fetchedMessages[fetchedMessages.length - 1];
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
        // do not clear tasks on fetch error to preserve sticky UI
        // setCurrentTasks([]);
        setHasShownTasks(false);
        console.error('FRONTEND: Error fetching conversation in useEffect[convId]. Clearing messages/suggestions. convId:', convId);
      })
      .finally(() => setLoading(false));
  }, [convId]);


  //console.log("FRONTEND RENDER: useAgent:", useAgent, "currentPlan:", currentPlan, "currentTasks:", currentTasks, "streamingMessage:", streamingMessage); // DEBUG

    console.log("FRONTEND RENDER: useBasicAgent:", useBasicAgent, "currentPlan:", currentPlan, "currentTasks:", currentTasks,
    "streamingMessage:", streamingMessage); // DEBUG
    
          // Legacy direct-plan fallback no longer used in agentic-only mode.
          // Agentic mode handles planning phases via 'planner_status' SSE events.
          useEffect(() => {}, []);


  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingMessage]);

  // Clear stale task markdown if it doesn't match current conversation
  useEffect(() => {
    if (taskMarkdown && activeConv && String(taskMarkdown.conversation_id) !== String(activeConv)) {
      console.log('FRONTEND: Detected stale task markdown, clearing. Task conv:', taskMarkdown.conversation_id, 'Active conv:', activeConv);
      setTaskMarkdown(null);
    }
  }, [taskMarkdown, activeConv]);

  // Format timestamp to readable format
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "";
    try {
      return format(new Date(timestamp), "h:mm a");
    } catch (e) {
      return "";
    }
  };

  // Handle approval request
  const handleApprove = async () => {
    if (!pendingApproval) return;
    
    const token = localStorage.getItem('authToken');
    try {
      const response = await fetch('/api/agent/approve', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({ 
          conv_id: activeConv,
          approval_id: pendingApproval.id 
        })
      });
      
      if (response.ok) {
        setApprovalHistory(prev => [...prev, { 
          ...pendingApproval, 
          approved: true, 
          timestamp: new Date().toISOString() 
        }]);
        setPendingApproval(null);
      }
    } catch (error) {
      console.error('Failed to approve operation:', error);
    }
  };

  // Handle rejection request
  const handleReject = async () => {
    if (!pendingApproval) return;
    
    const token = localStorage.getItem('authToken');
    try {
      const response = await fetch('/api/agent/reject', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({ 
          conv_id: activeConv,
          approval_id: pendingApproval.id 
        })
      });
      
      if (response.ok) {
        setApprovalHistory(prev => [...prev, { 
          ...pendingApproval, 
          approved: false, 
          timestamp: new Date().toISOString() 
        }]);
        setPendingApproval(null);
      }
    } catch (error) {
      console.error('Failed to reject operation:', error);
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
    console.error('FRONTEND: Clearing tasks inside handleInterrupt. Conversation ID:', activeConv);
    setCurrentTasks([]);
    setToolCallStatus("");
    
    // Send an interrupt signal to the backend
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/agent/interrupt', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({ conv_id: activeConv })
      });
      
      const result = await response.json();
      console.log('Interrupt response:', result);
      
      if (result.success) {
        console.log('Successfully sent interrupt signal');
      } else {
        console.log('Interrupt signal failed:', result.message);
      }
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

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 640) { // sm breakpoint
        setTextareaRows(5);
      } else {
        setTextareaRows(2);
      }
    };

    handleResize(); // Set initial value
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // NOTE: Message completion is now handled directly in the 'done' event to prevent duplicate display

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
  // Detect file type based on extension and MIME type
  const getFileType = (file) => {
    const extension = file.name.split('.').pop().toLowerCase();
    const mimeType = file.type;
    
    // Image files
    if (mimeType.startsWith('image/')) {
      return 'image';
    }
    
    // PDF files
    if (mimeType === 'application/pdf' || extension === 'pdf') {
      return 'pdf';
    }
    
    // Excel files
    if (mimeType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' || 
        mimeType === 'application/vnd.ms-excel' ||
        extension === 'xlsx' || extension === 'xls') {
      return 'excel';
    }
    
    // CSV files
    if (mimeType === 'text/csv' || extension === 'csv') {
      return 'csv';
    }
    
    // Text files
    if (mimeType.startsWith('text/') || 
        ['txt', 'md', 'markdown', 'log'].includes(extension)) {
      return 'text';
    }
    
    // Default to generic file
    return 'file';
  };

  const handleFileAttachment = (file) => {
    if (!file) return;
    
    const fileType = getFileType(file);
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB max for non-image files
    const MAX_IMAGE_SIZE = 375 * 1024; // 375KB for images
    const WARN_IMAGE_SIZE = 150 * 1024; // 150KB warning for images
    
    // Check file size based on type
    if (fileType === 'image') {
      if (file.size > MAX_IMAGE_SIZE) {
        setStreamingMessage({
          role: "system",
          content: `⚠️ Image too large (${(file.size / 1024).toFixed(0)}KB). Maximum supported size is 375KB.\n\n**Alternatives:**\n1. Use the image URL option (recommended)\n2. Compress your image to under 375KB`,
          isStreaming: false,
          isComplete: true,
          timestamp: new Date().toISOString()
        });
        return;
      } else if (file.size > WARN_IMAGE_SIZE) {
        setStreamingMessage({
          role: "system", 
          content: `⚠️ Large image (${(file.size / 1024).toFixed(0)}KB) detected. Consider using smaller images for better performance.`,
          isStreaming: false,
          isComplete: true,
          timestamp: new Date().toISOString()
        });
      }
    } else if (file.size > MAX_FILE_SIZE) {
      setStreamingMessage({
        role: "system",
        content: `⚠️ File too large (${(file.size / 1024 / 1024).toFixed(1)}MB). Maximum supported size is 10MB.`,
        isStreaming: false,
        isComplete: true,
        timestamp: new Date().toISOString()
      });
      return;
    }
    
    // Handle different file types
    if (fileType === 'image') {
      const reader = new FileReader();
      reader.onload = (e) => {
        setImageAttachment({
          dataUrl: e.target.result,
          file: file
        });
        setFileAttachment(null);
        setShowImageUrlInput(false);
        setImageUrl("");
      };
      reader.readAsDataURL(file);
    } else {
      // For non-image files, we'll read as text or base64 depending on type
      const reader = new FileReader();
      
      if (['text', 'csv'].includes(fileType)) {
        // Read text files as text
        reader.onload = (e) => {
          setFileAttachment({
            content: e.target.result,
            file: file,
            type: fileType,
            encoding: 'text'
          });
          setImageAttachment(null);
        };
        reader.readAsText(file);
      } else {
        // Read binary files as base64
        reader.onload = (e) => {
          setFileAttachment({
            dataUrl: e.target.result,
            file: file,
            type: fileType,
            encoding: 'base64'
          });
          setImageAttachment(null);
        };
        reader.readAsDataURL(file);
      }
    }
  };

  // Legacy function for backward compatibility
  const handleImageAttachment = (file) => {
    handleFileAttachment(file);
  };

  // Handle image upload button click
  const handleImageUploadClick = () => {
    imageInputRef.current?.click();
  };

  // Handle file upload button click
  const handleFileUploadClick = () => {
    fileInputRef.current?.click();
  };

  // Remove attachments
  const removeImageAttachment = () => {
    setImageAttachment(null);
  };

  const removeFileAttachment = () => {
    setFileAttachment(null);
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

  // Edit message handlers
  const handleEditMessage = (messageId, content) => {
    setEditingMessageId(messageId);
    setEditingContent(content);
  };

  const handleCancelEdit = () => {
    setEditingMessageId(null);
    setEditingContent("");
  };

  const handleSaveEdit = async () => {
    if (!editingContent.trim() || isEditSaving) return;

    setIsEditSaving(true);
    const token = localStorage.getItem('authToken');

    try {
      const response = await fetch(`/api/conversations/${convId}/messages/${editingMessageId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({
          content: editingContent.trim(),
          reprocess: true
        })
      });

      if (!response.ok) {
        throw new Error('Failed to update message');
      }

      const result = await response.json();

      if (result.success) {
        // Update the message in local state
        setMessages(prev => prev.map(msg => 
          msg.id === editingMessageId 
            ? { ...msg, content: editingContent.trim(), edited_at: new Date().toISOString() }
            : msg
        ));

        // If reprocessed, refresh the entire conversation
        if (result.reprocessed) {
          window.location.reload(); // Simple reload to refetch conversation
        }

        setEditingMessageId(null);
        setEditingContent("");
      }
    } catch (error) {
      console.error('Error editing message:', error);
      // Could show error toast here
    } finally {
      setIsEditSaving(false);
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
  //     if (!response.ok) {setCurrentTasks
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


  // Handle injecting a message during agent execution
  const handleInjectMessage = async (messageContent = input) => {
    const textToSend =
      typeof messageContent === "string" ? messageContent.trim() : input.trim();

    console.log('[DEBUG] handleInjectMessage called:', {
      textToSend,
      hasStreamingMessage: !!streamingMessage,
      streamingMessageState: streamingMessage ? {
        isStreaming: streamingMessage.isStreaming,
        isComplete: streamingMessage.isComplete,
        content: streamingMessage.content?.substring(0, 50) + '...'
      } : null,
      convId,
      activeConv
    });

    if (!textToSend || !streamingMessage || !convId) {
      console.log('[DEBUG] handleInjectMessage early return:', {
        noText: !textToSend,
        noStreamingMessage: !streamingMessage,
        noConvId: !convId
      });
      return;
    }

    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch('/api/inject-message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({
          conversationId: convId,
          message: textToSend,
          priority: 'normal'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to inject message');
      }

      const result = await response.json();
      
      if (result.success) {
        // Add message to chat immediately (marked as injected)
        const injectedMessage = {
          role: "user",
          content: textToSend,
          timestamp: new Date().toISOString(),
          status: "injected"
        };
        setMessages((prev) => [...prev, injectedMessage]);
        setInput('');
        
        // Show status message
        console.log(`Message queued for injection (${result.queueLength} pending)`);
      }
    } catch (error) {
      console.error('Error injecting message:', error);
    }
  };

  // Interrupt running tasks in the current conversation
  const interruptCurrentTasks = async () => {
    try {
      const threadId = convId || activeConv;
      if (!threadId) {
        console.log('[DEBUG] No thread ID available for interruption');
        return { cancelled_tasks: 0 };
      }

      console.log('[DEBUG] Interrupting tasks for thread:', threadId);
      const response = await fetch(`/api/agent/async/interrupt/${threadId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        throw new Error(`Failed to interrupt tasks: ${response.status}`);
      }

      const result = await response.json();
      console.log('[DEBUG] Interrupt result:', result);

      // If there were partial results, add them to the conversation
      if (result.partial_results && result.partial_results.length > 0) {
        for (const partialResult of result.partial_results) {
          if (partialResult.partial_response) {
            const interruptedMessage = {
              id: `interrupted-${Date.now()}`,
              role: "assistant", 
              content: `⚠️ **Task Interrupted** (${Math.round(partialResult.progress * 100)}% complete)\n\n${partialResult.partial_response}`,
              timestamp: new Date().toISOString(),
              agent: "interrupted",
              isInterrupted: true
            };
            setMessages(prev => [...prev, interruptedMessage]);
          }
        }
      }

      // Clear any streaming message and reset sending state
      setStreamingMessage(null);
      setIsSending(false);

      return result;
    } catch (error) {
      console.error('[DEBUG] Failed to interrupt tasks:', error);
      // Still reset the sending state even if interruption failed
      setStreamingMessage(null);
      setIsSending(false);
      return { cancelled_tasks: 0 };
    }
  };

  // Async task polling function
  const pollAsyncTask = async (taskId, conversationId) => {
    try {
      // Set conversation ID if this is a new conversation
      if (conversationId && (!convId && !activeConv)) {
        console.log('[DEBUG] Setting activeConv from async response:', conversationId);
        setActiveConv(conversationId);
        
        // Notify parent component immediately to navigate to new conversation
        if (onNewConversation && !convId) {
          console.log('[DEBUG] Calling onNewConversation with:', conversationId);
          // Don't navigate immediately - let the polling complete first
          // onNewConversation(conversationId);
        }
      }

      // Update status message
      setStreamingMessage({
        role: "assistant",
        content: "⚡ Processing with async agents... Getting real-time updates",
        timestamp: new Date().toISOString(),
        agent: "async-orchestrator",
        isStreaming: true,
        isComplete: false,
      });

      // Poll for task completion
      let completed = false;
      let attempts = 0;
      const maxAttempts = 120; // 2 minutes max
      
      while (!completed && attempts < maxAttempts) {
        try {
          const response = await fetch(`/api/agent/async/task/${taskId}`);
          if (response.status === 404) {
            // Task not found - probably backend restarted
            throw new Error('Task not found - it may have been lost due to server restart');
          }
          if (!response.ok) throw new Error(`Task polling failed: ${response.status}`);
          
          const taskData = await response.json();
          
          // Update progress
          if (taskData.status === 'running') {
            const progress = Math.round((taskData.progress || 0) * 100);
            setStreamingMessage({
              role: "assistant",
              content: `⚡ Processing: ${taskData.message || 'Working...'} (${progress}%)`,
              timestamp: new Date().toISOString(),
              agent: "async-orchestrator",
              isStreaming: true,
              isComplete: false,
            });
          } else if (taskData.status === 'completed') {
            completed = true;
            
            // Add final response as message
            const uniqueId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
            const assistantMessage = {
              id: uniqueId,
              role: "assistant",
              content: taskData.response || "Task completed successfully",
              timestamp: new Date().toISOString(),
              agent: "async-orchestrator"
            };
            
            // Clear streaming message and add final response
            setStreamingMessage(null);
            setMessages(prev => [...prev, assistantMessage]);
            
            console.log('[DEBUG] Async task completed, added final message');
            
            // Now navigate to the new conversation if needed
            if (conversationId && !convId && onNewConversation) {
              console.log('[DEBUG] Navigation after completion to:', conversationId);
              setTimeout(() => {
                onNewConversation(conversationId);
              }, 500);
            }
            break;
          } else if (taskData.status === 'failed') {
            throw new Error(taskData.error || 'Task failed');
          }
          
          attempts++;
          if (!completed) {
            await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
          }
        } catch (error) {
          console.error('[DEBUG] Polling error:', error);
          attempts++;
          await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds on error
        }
      }
      
      if (!completed) {
        throw new Error('Task polling timeout');
      }
      
    } catch (error) {
      console.error('[DEBUG] Async task error:', error);
      
      // Show error message
      const errorMessage = {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `❌ Error: ${error.message}`,
        timestamp: new Date().toISOString(),
        agent: "system"
      };
      
      setStreamingMessage(null);
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsSending(false);
    }
  };

  // Handle sending a message with streaming response
  const handleSend = async (messageContent = input) => {
    const textToSend =
      typeof messageContent === "string" ? messageContent.trim() : input.trim();

    console.log('[DEBUG] handleSend called:', {
      textToSend,
      streamingState: streamingMessage ? {
        isStreaming: streamingMessage.isStreaming,
        isComplete: streamingMessage.isComplete,
        hasContent: !!streamingMessage.content
      } : null,
      shouldInject: streamingMessage && streamingMessage.isStreaming && !streamingMessage.isComplete
    });

    // If agent is running, interrupt it and continue with new message
    if (streamingMessage && streamingMessage.isStreaming && !streamingMessage.isComplete) {
      console.log('[DEBUG] Agent is running - interrupting before sending new message');
      const interruptResult = await interruptCurrentTasks();
      
      // Add a brief message about the interruption
      if (interruptResult.cancelled_tasks > 0) {
        const interruptNotice = {
          id: `interrupt-notice-${Date.now()}`,
          role: "system",
          content: `🛑 Interrupted ${interruptResult.cancelled_tasks} running task(s) to process your new request.`,
          timestamp: new Date().toISOString(),
          isInterruptNotice: true
        };
        setMessages(prev => [...prev, interruptNotice]);
      }
    }

    if ((!textToSend && !imageAttachment && !fileAttachment) || isSending) return;

    // Safety: if previous assistant draft exists and is NOT streaming (e.g. backend didn't emit 'done'),
    // finalize it into messages before starting a new send so it doesn't disappear.
    // BUT skip if it's just the thinking message
    const prevDraft = streamingMessageRef.current;
    const isThinkingMessage = prevDraft?.content?.includes('GPT-5 is thinking');
    if (prevDraft && prevDraft.content && !prevDraft.isStreaming && !isThinkingMessage) {
      const messageId = `msg-${Date.now()}`;
      const timestamp = prevDraft.timestamp || new Date().toISOString();
      const currentTaskMarkdownRef = taskMarkdown && 
        String(taskMarkdown.conversation_id) === String(activeConv || convId) 
        ? taskMarkdown 
        : null;
      setStreamingMessage(null);
      setMessages(prev => [...prev, {
        id: messageId,
        role: "assistant",
        content: prevDraft.content,
        timestamp,
        taskMarkdown: currentTaskMarkdownRef
      }]);
    }

    const userMessage = {
      role: "user",
      content: textToSend,
      timestamp: new Date().toISOString(),
      imageAttachment: imageAttachment,
      fileAttachment: fileAttachment,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsSending(true);
    setInput('');
    setSuggestions([]);
    setCurrentPlan(null);
    setImageAttachment(null); // Clear attachment after sending
    setFileAttachment(null); // Clear file attachment after sending
    setImageUrl("");
    setShowImageUrlInput(false);
    setAgentProcessingStatus(""); // Clear previous agent status
    setTaskMarkdown(null); // Clear previous task markdown
    messageFinalizedRef.current = false; // Reset finalization flag for new message
    lastFinalizedContentRef.current = null; // Reset last finalized content
    lastProcessedMessageRef.current = null; // Reset last processed message
    processingResponseRef.current = false; // Reset processing flag

    // Show a loading indicator for non-streaming mode
    setStreamingMessage({
      role: "assistant",
      content: "",  // Empty content will show the animated dots
      timestamp: new Date().toISOString(),
      isStreaming: true,
      isComplete: false,
    });

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      // Use async orchestrator by default, with fallback options
      const useAsync = true; // Always use async for better performance
      const useSSE = orchestratorEnabled === true;
      const fetchUrl = useAsync ? "/api/agent/async/message" : (useSSE ? "/api/agent/sse" : "/api/agent/message");
      console.log(useAsync ? "Using async orchestrator endpoint" : useSSE ? "Using SSE orchestrator endpoint" : "Using non-streaming master agent orchestrator endpoint");

      if (useBasicAgent) {
        setPlannerStatus("Initializing...");
        setDispatcherStatus("");
        setSynthesizerStatus("Initializing...");
        // Preserve existing task list so progress UI stays sticky
        setToolCallStatus("");
      }

      const conversationId = convId || activeConv || undefined;
      console.log('[DEBUG] Sending message with conversation_id:', conversationId, 'convId:', convId, 'activeConv:', activeConv);
      const requestData = useAsync ? {
        message: textToSend,
        conv_id: conversationId,  // Async endpoint uses conv_id
      } : {
        conversation_id: conversationId,  // Sync endpoint uses conversation_id
        thread_id: conversationId,  // Also send as thread_id for compatibility
        message: textToSend,
      };

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

      if (fileAttachment) {
        requestData.file = {
          type: fileAttachment.type,
          name: fileAttachment.file.name,
          size: fileAttachment.file.size,
          encoding: fileAttachment.encoding
        };
        
        if (fileAttachment.encoding === 'text') {
          requestData.file.content = fileAttachment.content;
        } else {
          requestData.file.data = fileAttachment.dataUrl;
        }
      }

      const token = localStorage.getItem('authToken');
      
      console.log('[DEBUG] About to fetch from:', fetchUrl, 'with conversation_id:', conversationId);
      
      // Show thinking indicator for GPT-5 with isStreaming flag
      setStreamingMessage({
        role: "assistant",
        content: "🤔 GPT-5 is thinking... This may take 30-60 seconds for complex queries.",
        timestamp: new Date().toISOString(),
        agent: "orchestrator",
        isStreaming: true,  // Important: This makes the message visible
        isComplete: false
      });
      
      // Create AbortController for timeout (600 seconds / 10 minutes for complex operations)
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 minutes timeout
      
      const response = await fetch(fetchUrl, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Accept": useSSE ? "text/event-stream" : "application/json",
          "Authorization": token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify(requestData),
        signal: controller.signal
      }).finally(() => clearTimeout(timeoutId));

      if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`HTTP error! status: ${response.status}, body: ${errorBody}`);
      }

      // Handle async endpoint response
      if (useAsync) {
        const result = await response.json();
        console.log('[DEBUG] Async response received:', result);
        
        // Start polling for task completion
        if (result.task_id) {
          await pollAsyncTask(result.task_id, result.conversation_id);
        }
        return;
      }

      // Non-streaming path (legacy)
      if (!useSSE) {
        const result = await response.json();
        console.log('[DEBUG] Non-streaming response received at:', new Date().toISOString());
        console.log('[DEBUG] Response content:', result.response?.substring(0, 100) || result.message?.substring(0, 100) || 'No content');
        
        // Set the conversation ID if returned
        if (result.conversation_id) {
          const newConvId = result.conversation_id;
          console.log('[DEBUG] Setting activeConv to:', newConvId);
          setActiveConv(newConvId);
          
          // If this is a new conversation, notify parent with delay to allow backend to save
          // TEMPORARY: Disable auto-navigation for debugging
          const DISABLE_AUTO_NAVIGATION = true;
          if (onNewConversation && !convId && !DISABLE_AUTO_NAVIGATION) {
            console.log('[DEBUG] Scheduling navigation to new conversation:', newConvId);
            setTimeout(() => {
              onNewConversation(newConvId);
            }, 500);
          } else {
            console.log('[DEBUG] Auto-navigation disabled for debugging');
          }
        }
        
        // Add the assistant message with a truly unique ID
        const uniqueId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const assistantMessage = {
          id: uniqueId,
          role: "assistant",
          content: result.response || result.message || result.content || "",
          timestamp: new Date().toISOString(),
          agent: result.agent || "orchestrator"
        };
        
        // Clear the streaming message state AND ref FIRST to prevent duplicates
        setStreamingMessage(null);
        streamingMessageRef.current = null; // Important: clear the ref too
        
        // Then add the message to the list (check for duplicates first)
        console.log('[DEBUG] About to add message. Current messages count:', messages.length);
        console.log('[DEBUG] Last finalized content:', lastFinalizedContentRef.current);
        
        // Check if we already finalized this content
        const normalizedContent = (assistantMessage.content || '').trim();
        if (!debugNoDedup && lastFinalizedContentRef.current === normalizedContent) {
          console.log('[DEBUG] BLOCKING DUPLICATE - Already finalized this exact content');
          setIsSending(false);
          return; // Don't add the message
        }
        
        // Use a unique message ID to prevent duplicates
        const messageId = assistantMessage.id;
        
        // CRITICAL FIX: Use flushSync to ensure state updates happen synchronously
        // This prevents React StrictMode from running the function twice with the same state
        
        // Check if message ID is already processed
        if (!debugNoDedup && messageIdsRef.current.has(messageId)) {
          console.log('[DEBUG] Message ID already processed, skipping:', messageId);
          return;
        }
        
        // Add to set immediately
        messageIdsRef.current.add(messageId);
        console.log('[DEBUG] Added message ID to tracking set:', messageId);
        
        // Mark content as finalized
        lastFinalizedContentRef.current = normalizedContent;
        
        // Use flushSync to force synchronous state update
        // This ensures the first invocation completes before the second one runs
        try {
          flushSync(() => {
            setMessages(prev => {
              console.log('[DEBUG] Inside setMessages. Prev length:', prev.length, 'MessageID:', messageId);
              
              // Final safety check inside setMessages
              const idExists = prev.some(msg => msg.id === messageId);
              if (!debugNoDedup && idExists) {
                console.log('[DEBUG] Message already in state, skipping');
                return prev;
              }
              
              const contentExists = prev.some(msg => 
                msg.role === 'assistant' && 
                (msg.content || '').trim() === normalizedContent
              );
              if (!debugNoDedup && contentExists) {
                console.log('[DEBUG] Duplicate content detected, skipping');
                return prev;
              }
              
              console.log('[DEBUG] Adding assistant message with ID:', messageId);
              return [...prev, assistantMessage];
            });
          });
        } catch (e) {
          // If flushSync fails (not available or other issue), fall back to regular setState
          console.log('[DEBUG] flushSync failed, using regular setState');
          setMessages(prev => {
            const idExists = prev.some(msg => msg.id === messageId);
            if (!debugNoDedup && idExists) return prev;
            
            const contentExists = prev.some(msg => 
              msg.role === 'assistant' && 
              (msg.content || '').trim() === normalizedContent
            );
            if (!debugNoDedup && contentExists) return prev;
            
            return [...prev, assistantMessage];
          });
        }
        
        setIsSending(false);
        
        // Clear all status indicators
        setSynthesizerStatus("");
        setAgentProcessingStatus("");
        setPlannerStatus("");
        setDispatcherStatus("");
        setToolCallStatus("");
        
        return; // End non-streaming path
      }
      
      const reader = response.body.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();
      let eventDataBuffer = "";
      let shouldStop = false;

      while (!shouldStop) {
        try {
          const { done, value } = await reader.read();
          
          // Breaking condition - either explicit shouldStop flag or reader signals done
          if (done || shouldStop) {
            console.log("FRONTEND: Stream reader loop breaking, done=", done, "shouldStop=", shouldStop);
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          eventDataBuffer += chunk;

          const eventMessages = eventDataBuffer.split(/\n\n/);
          eventDataBuffer = eventMessages.pop() || ""; 
          
          // Process all complete event messages in this chunk
          for (const singleEventString of eventMessages) {
            if (!singleEventString.trim()) continue;

            let eventName = null;
            let rawJsonDataString = "";
            const sseLines = singleEventString.split('\n');

            for (const line of sseLines) {
              // Prioritize explicit event: line if present
              if (line.startsWith('event:')) {
                eventName = line.substring(6).trim();
              } 
              // Always accumulate data: lines
              if (line.startsWith('data:')) { 
                rawJsonDataString += line.substring(5).trim();
              }
            }

            try {
              let parsedData = rawJsonDataString ? JSON.parse(rawJsonDataString) : {};
              let actualEventPayload = parsedData;
              
              // Debug log conversation events
              if (eventName === 'conversation_id' || eventName === 'conv_id') {
                console.log('[DEBUG] Got conversation event:', eventName, actualEventPayload);
              }

              // Debug: Log parsed event
              console.log("FRONTEND: Parsed NDJSON event:", eventName, "Payload:", actualEventPayload);

              // Handle 'done' event for basic agent mode ONLY
              if (eventName === 'done') {
                console.log("FRONTEND: Done event detected. useBasicAgent:", useBasicAgent, "messageFinalizedRef:", messageFinalizedRef.current);
                if (!useBasicAgent) {
                  console.log("FRONTEND: Skipping done - not basic agent mode");
                  // Let multi-agent handler deal with it
                } else if (messageFinalizedRef.current) {
                  console.log("FRONTEND: SKIPPING DONE - ALREADY FINALIZED!");
                  setStreamingMessage(null);
                  setIsSending(false);
                  shouldStop = true;
                  break;
                } else {
                  console.log("FRONTEND: Processing done event for basic agent");
                // If this is a NEW conversation (no convId yet), skip local append and rely on
                // the upcoming fetch(/api/conversations/:id) to hydrate messages to prevent duplicates.
                if (!convId) {
                    setStreamingMessage(null);
                    setIsSending(false);
                    shouldStop = true;
                    if (readerRef.current) {
                      try {
                        console.log("FRONTEND: Attempting to cancel reader");
                        readerRef.current.cancel("Stream completed");
                      } catch (e) {
                        console.error("Error cancelling reader:", e);
                      }
                    }
                    break;
                  }
                  const currentTaskMarkdownRef = taskMarkdown && 
                    String(taskMarkdown.conversation_id) === String(activeConv || convId) 
                    ? taskMarkdown 
                    : null;
                  const messageId = `msg-${Date.now()}`;
                  const timestamp = new Date().toISOString();
                  const streamingContent = streamingMessageRef.current?.content;
                  if (streamingContent && !messageFinalizedRef.current) {
                    const normalizedContent = (streamingContent || '').trim();
                    
                    // Check if this exact content was already finalized
                    if (lastFinalizedContentRef.current === normalizedContent) {
                      console.log('FRONTEND: DUPLICATE BLOCKED - already finalized this content:', normalizedContent.substring(0, 50));
                      setStreamingMessage(null);
                      setIsSending(false);
                      shouldStop = true;
                      break; // Exit immediately
                    }
                    
                    console.log('FRONTEND: FINALIZING MESSAGE (basic agent):', normalizedContent.substring(0, 50));
                    messageFinalizedRef.current = true; // Mark as finalized
                    lastFinalizedContentRef.current = normalizedContent; // Store finalized content
                    setStreamingMessage(null);
                    
                    setMessages(prev => {
                      // More aggressive duplicate check - normalize and compare
                      const normalizedNew = normalizedContent.replace(/\s+/g, ' ');
                      
                      // Check if ANY recent assistant message matches
                      for (let i = prev.length - 1; i >= Math.max(0, prev.length - 5); i--) {
                        if (prev[i].role === 'assistant') {
                          const normalizedExisting = (prev[i].content || '').trim().replace(/\s+/g, ' ');
                          if (normalizedExisting === normalizedNew || 
                              normalizedExisting.includes(normalizedNew) || 
                              normalizedNew.includes(normalizedExisting)) {
                            console.log('FRONTEND: Prevented duplicate - content already exists');
                            return prev;
                          }
                        }
                      }
                      
                      if (!normalizedContent) {
                        console.log('FRONTEND: Prevented empty message');
                        return prev;
                      }
                      
                      return [...prev, {
                        id: messageId,
                        role: "assistant",
                        content: streamingContent,
                        timestamp: timestamp,
                        taskMarkdown: currentTaskMarkdownRef
                      }];
                    });
                  } else {
                    setStreamingMessage(null);
                  }
                  setIsSending(false);
                  shouldStop = true;
                  if (readerRef.current) {
                    try {
                      console.log("FRONTEND: Attempting to cancel reader");
                      readerRef.current.cancel("Stream completed");
                    } catch (e) {
                      console.error("Error cancelling reader:", e);
                    }
                  }
                  console.log("FRONTEND: Basic agent done handled, breaking loop");
                  break; // Exit the while loop completely
                }
              }
            
              // Handle conversation ID events regardless of agent mode
              if (eventName === 'conv_id') {
                if (actualEventPayload.conversationId && activeConv !== actualEventPayload.conversationId) {
                  setActiveConv(actualEventPayload.conversationId);
                }
              } else if (eventName === 'conversation_id') {
                console.log('[DEBUG] Received conversation_id event:', actualEventPayload);
                if (actualEventPayload.conv_id) {
                  console.log('[DEBUG] Setting activeConv to:', actualEventPayload.conv_id);
                  setActiveConv(actualEventPayload.conv_id);
                  // Also update onNewConversation callback if provided
                  if (onNewConversation && !convId) {
                    onNewConversation(actualEventPayload.conv_id);
                  }
                  
                  // Auto-generate title after first message
                  if (!convId && messages.length === 1) {
                    console.log('[DEBUG] Generating title for new conversation:', actualEventPayload.conv_id);
                    fetch(`/api/conversations/${actualEventPayload.conv_id}/generate-title`, {
                      method: 'POST',
                      headers: {
                        'Authorization': localStorage.getItem('authToken') ? `Bearer ${localStorage.getItem('authToken')}` : '',
                        'Content-Type': 'application/json'
                      }
                    })
                    .then(res => res.json())
                    .then(data => {
                      if (data.title) {
                        console.log('[DEBUG] Generated title:', data.title);
                        // Update the conversation list will happen automatically on next fetch
                      }
                    })
                    .catch(err => console.error('[DEBUG] Failed to generate title:', err));
                  }
                }
              }
              
              // Handle agent_message event for both basic and multi-agent modes
              if (eventName === 'agent_message') {
                console.log("FRONTEND: Agent message", actualEventPayload);
                // During streaming, handle both full content and incremental tokens
                if (actualEventPayload.tokens && actualEventPayload.tokens.length > 0) {
                  // Incremental token streaming
                  const newTokens = actualEventPayload.tokens.join('');
                  setStreamingMessage(prev => ({ 
                    role: 'assistant',
                    content: (prev?.content || '') + newTokens,  // Append tokens incrementally
                    isStreaming: true,
                    isComplete: false,
                    timestamp: prev?.timestamp || new Date().toISOString()
                  }));
                } else if (actualEventPayload.message !== undefined) {
                  // Full message update (backward compatibility)
                  setStreamingMessage(prev => ({ 
                    role: 'assistant',
                    content: actualEventPayload.message,  // Use the full message
                    isStreaming: true,
                    isComplete: false,
                    timestamp: prev?.timestamp || new Date().toISOString()
                  }));
                }
              }
              
              // Handle agent_complete event
              if (eventName === 'agent_complete') {
                console.log("FRONTEND: Agent complete", actualEventPayload);
                // Just mark streaming as done, don't set complete yet
                // The 'done' event will handle completion
                setStreamingMessage(prev => {
                  if (!prev) return null;
                  return { 
                    ...prev,
                    content: actualEventPayload.message || prev?.content || "",
                    isStreaming: false,  // Stop showing streaming indicator
                    isComplete: false,   // Don't mark complete yet - wait for 'done'
                    timestamp: prev?.timestamp || new Date().toISOString()
                  };
                });
              }
              
              // Handle start event for all modes
              if (eventName === 'start') {
                console.log("FRONTEND: System started", actualEventPayload);
                setStreamingMessage(prev => ({ 
                  ...prev, 
                  content: prev?.content || "", 
                  isStreaming: true, 
                  isComplete: false 
                }));
                // Clear previous status
                setAgentProcessingStatus("");
                setToolCallStatus("");
              }
              
              // Handle agent_processing event for all modes
              if (eventName === 'agent_processing') {
                console.log("FRONTEND: Agent processing", actualEventPayload);
                setAgentProcessingStatus(actualEventPayload.message || `${actualEventPayload.agent} is processing...`);
                setToolCallStatus(""); // Clear tool status when agent message is shown
                // Ensure streaming state is active to show the status
                if (!streamingMessage || !streamingMessage.isStreaming) {
                  setStreamingMessage(prev => ({ 
                    ...prev, 
                    isStreaming: true, 
                    isComplete: false 
                  }));
                }
              }
              
              // Handle multi-agent specific events
              if (!useBasicAgent) {
                switch (eventName) {
                case 'handoff':
                  console.log("FRONTEND: Agent handoff", actualEventPayload);
                  setStreamingMessage(prev => ({ 
                    ...prev, 
                    content: prev.content + `\n[Handoff: ${actualEventPayload.from} → ${actualEventPayload.to}]`, 
                    isStreaming: true, 
                    isComplete: false 
                  }));
                  break;
                case 'assistant_delta':
                  // Multi-agent token streaming support (match basic agent behavior)
                  if (plannerStatus) setPlannerStatus("");
                  if (dispatcherStatus) setDispatcherStatus("");
                  setSynthesizerStatus("Synthesizer: streaming...");
                  setToolCallStatus("");
                  setCurrentTasks(prev => prev.map(t => (t.status === 'running' ? { ...t, status: 'completed_implicit' } : t)));
                  console.log("FRONTEND: [multi-agent] Received 'assistant_delta' event payload:", JSON.stringify(actualEventPayload));
                  setStreamingMessage(prev => {
                    const newContent = (prev?.content || "") + (actualEventPayload.delta || "");
                    console.log("FRONTEND: [multi-agent] Updating streamingMessage, new content length:", newContent.length);
                    const newState = { ...prev, content: newContent, isStreaming: true, isComplete: false };
                    return newState;
                  });
                  break;
                case 'tool_call':
                  console.log("FRONTEND: Tool call by agent", actualEventPayload);
                  setToolCallStatus(`${actualEventPayload.agent}: ${actualEventPayload.tool} (${actualEventPayload.status})`);
                  break;
                case 'task_summary':
                  console.log("FRONTEND: Task summary", actualEventPayload);
                  if (actualEventPayload.tasks && actualEventPayload.tasks.length > 0) {
                    setCurrentTasks(prevTasks => {
                      // If we have no tasks, initialize with the incoming tasks
                      if (prevTasks.length === 0) {
                        console.log('FRONTEND: Initial task load from task_summary (multi-agent)');
                        return actualEventPayload.tasks.map(task => ({
                          ...task,
                          conversation_id: actualEventPayload.conversation_id || activeConv || convId
                        }));
                      }
                      
                      // Create a map of existing tasks by ID for easier lookup
                      const existingTasksMap = new Map(prevTasks.map(t => [t.id, t]));
                      
                      // Update existing tasks and add new ones
                      const updatedTasks = actualEventPayload.tasks.map(newTask => {
                        const taskWithConvId = {
                          ...newTask,
                          conversation_id: actualEventPayload.conversation_id || activeConv || convId
                        };
                        const existingTask = existingTasksMap.get(newTask.id);
                        if (existingTask) {
                          // Update status if it changed
                          if (existingTask.status !== newTask.status) {
                            console.log(`FRONTEND: Updating task ${newTask.id} status from ${existingTask.status} to ${newTask.status} (multi-agent)`);
                            return { ...existingTask, ...taskWithConvId };
                          }
                          return existingTask;
                        }
                        // This is a new task
                        console.log('FRONTEND: Adding new task (multi-agent):', newTask.id);
                        return taskWithConvId;
                      });
                      
                      return updatedTasks;
                    });
                    setHasShownTasks(true);
                  }
                  break;
                case 'memory_summary':
                  console.log("FRONTEND: Memory summary", actualEventPayload);
                  // Could display memory count in UI if desired
                  break;
                case 'task_plan_creating':
                  console.log("FRONTEND: Task plan being created", actualEventPayload);
                  setToolCallStatus('Task Planner is creating a structured plan...');
                  break;
                case 'task_plan_created':
                  console.log("FRONTEND: Task plan created", actualEventPayload);
                  console.log("FRONTEND: Current activeConv:", activeConv, "convId:", convId);
                  console.log("FRONTEND: Task conversation_id:", actualEventPayload.conversation_id);
                  setTaskMarkdown({
                    markdown: actualEventPayload.markdown,
                    filename: actualEventPayload.filename,
                    taskCount: actualEventPayload.taskCount,
                    conversation_id: actualEventPayload.conversation_id
                  });
                  setToolCallStatus(`Task plan created with ${actualEventPayload.taskCount || 'multiple'} tasks`);
                  break;
                case 'agent_message_partial':
                  console.log("FRONTEND: Agent partial message", actualEventPayload);
                  // For partial messages during streaming
                  setStreamingMessage(prev => ({ 
                    ...prev, 
                    content: (prev?.content || "") + actualEventPayload.content,
                    isStreaming: true, 
                    isComplete: false 
                  }));
                  break;
                case 'error':
                  const errorMessage = actualEventPayload.message || 
                                     actualEventPayload.description || 
                                     (typeof actualEventPayload === 'string' ? actualEventPayload : 'An error occurred');
                  setToolCallStatus(`Error: ${errorMessage}`);
                  console.error("Multi-agent Error:", actualEventPayload);
                  setStreamingMessage(prev => ({ 
                    ...prev, 
                    content: (prev?.content || "") + `\n\n**Error:** ${errorMessage}`, 
                    isStreaming: false, 
                    isComplete: true 
                  }));
                  setIsSending(false);
                  shouldStop = true;
                  break;
                default:
                  console.log("Unknown multi-agent SSE event type:", eventName, "Payload:", actualEventPayload);
                }
              } else if (useBasicAgent) {
                switch (eventName) {
                case 'topic_updated':
                  console.log("FRONTEND: Topic updated (basic agent)", actualEventPayload);
                  // Call the parent callback to update the sidebar
                  if (onTopicUpdate && actualEventPayload.conversation_id) {
                    // Ensure conversation_id is a number to match the state
                    const convId = typeof actualEventPayload.conversation_id === 'string' 
                      ? parseInt(actualEventPayload.conversation_id) 
                      : actualEventPayload.conversation_id;
                    console.log("FRONTEND: Calling onTopicUpdate with convId:", convId, "type:", typeof convId);
                    onTopicUpdate(
                      convId,
                      actualEventPayload.topic_title,
                      actualEventPayload.topic_details
                    );
                  }
                  break;
                case 'agent_status':
                  const { status, tool } = actualEventPayload;
                  console.log('FRONTEND: agent_status event, status:', status, 'tool:', tool);
                  if (status === 'analyzing') {
                    setPlannerStatus("Agent: analyzing request...");
                  } else if (status === 'creating_task') {
                    setPlannerStatus("Agent: creating task...");
                  } else if (status === 'updating_task') {
                    setDispatcherStatus("Agent: updating task...");
                  } else if (status === 'searching') {
                    setDispatcherStatus("Agent: searching...");
                  } else if (status === 'processing') {
                    setDispatcherStatus(`Agent: ${tool || 'processing'}...`);
                  } else if (status === 'responding') {
                    setSynthesizerStatus("Agent: responding...");
                  }
                  break;
                case 'task_created':
                  console.log('FRONTEND: task_created event:', actualEventPayload);
                  const newTask = {
                    id: `task-${actualEventPayload.taskId}`,
                    content: `Task ${actualEventPayload.taskId}`,
                    status: 'pending',
                    conversation_id: actualEventPayload.conversation_id,
                    toolName: 'todo_task'
                  };
                  setCurrentTasks(prevTasks => [...prevTasks, newTask]);
                  break;
                case 'task_updated':
                  console.log('FRONTEND: task_updated event:', actualEventPayload);
                  setCurrentTasks(prevTasks => {
                    const taskIndex = prevTasks.findIndex(t => t.id === `task-${actualEventPayload.taskId}`);
                    if (taskIndex !== -1) {
                      const updatedTasks = [...prevTasks];
                      updatedTasks[taskIndex] = {
                        ...updatedTasks[taskIndex],
                        status: actualEventPayload.status
                      };
                      return updatedTasks;
                    }
                    return prevTasks;
                  });
                  break;
                case 'task_plan_created':
                  console.log("FRONTEND: Task plan created (basic agent)", actualEventPayload);
                  console.log("FRONTEND: Current activeConv:", activeConv, "convId:", convId);
                  console.log("FRONTEND: Task conversation_id:", actualEventPayload.conversation_id);
                  setTaskMarkdown({
                    markdown: actualEventPayload.markdown,
                    filename: actualEventPayload.filename,
                    taskCount: actualEventPayload.taskCount,
                    conversation_id: actualEventPayload.conversation_id
                  });
                  setToolCallStatus(`Task plan created with ${actualEventPayload.taskCount || 'multiple'} tasks`);
                  break;
                case 'task_summary':
                  console.log('FRONTEND: task_summary event:', actualEventPayload);
                  if (
                    actualEventPayload.tasks &&
                    Array.isArray(actualEventPayload.tasks) &&
                    actualEventPayload.tasks.length > 0
                  ) {
                    setCurrentTasks(prevTasks => {
                      // If we have no tasks, initialize with the incoming tasks
                      if (prevTasks.length === 0) {
                        console.log('FRONTEND: Initial task load from task_summary');
                        return actualEventPayload.tasks;
                      }
                      
                      // Create a map of existing tasks by ID for easier lookup
                      const existingTasksMap = new Map(prevTasks.map(t => [t.id, t]));
                      
                      // Update existing tasks and add new ones
                      const updatedTasks = actualEventPayload.tasks.map(newTask => {
                        const existingTask = existingTasksMap.get(newTask.id);
                        if (existingTask) {
                          // Update status if it changed
                          if (existingTask.status !== newTask.status) {
                            console.log(`FRONTEND: Updating task ${newTask.id} status from ${existingTask.status} to ${newTask.status}`);
                            return { ...existingTask, ...newTask };
                          }
                          return existingTask;
                        }
                        // This is a new task
                        console.log('FRONTEND: Adding new task:', newTask.id);
                        return newTask;
                      });
                      
                      return updatedTasks;
                    });
                    setHasShownTasks(true);
                  }
                  break;
                case 'task_markdown':
                  console.log('FRONTEND: task_markdown event:', actualEventPayload);
                  console.log('FRONTEND: activeConv:', activeConv, 'event conv_id:', actualEventPayload.conversation_id);
                  if (actualEventPayload.markdown) {
                    console.log('FRONTEND: Setting task markdown:', actualEventPayload.markdown);
                    setTaskMarkdown(actualEventPayload.markdown);
                    setHasShownTasks(true);
                  }
                  break;
                case 'task_status_update':
                  console.log('FRONTEND: task_status_update event:', actualEventPayload);
                  if (actualEventPayload.taskId && actualEventPayload.status) {
                    setCurrentTasks(prevTasks => {
                      const updatedTasks = prevTasks.map(task => {
                        if (task.id === actualEventPayload.taskId || task.id === `task-${actualEventPayload.taskId}`) {
                          console.log(`FRONTEND: Updating task ${task.id} status from ${task.status} to ${actualEventPayload.status}`);
                          return { ...task, status: actualEventPayload.status };
                        }
                        return task;
                      });
                      return updatedTasks;
                    });
                  }
                  break;
                case 'planner_status': {
                  const { state, plan } = actualEventPayload;
                  console.log('FRONTEND: planner_status event, state:', state, 'raw plan:', plan);
                  setPlannerStatus(state === 'completed' ? `Plan: ${state}` : `Planner: ${state}`);
                  if (state === 'completed' && Array.isArray(plan)) {
                    console.log('FRONTEND: updating currentPlan with', plan.length, 'items');
                    setCurrentPlan(plan);
                    const cid = activeConv || convId;
                    const taskProgressItems = plan.map(task => {
                      const id = task.id;
                      const content = task.content ?? task.title ?? task.description ?? task.name ?? '';
                      const statusInit = task.status ?? 'pending';
                      const toolName = task.toolName ?? task.agent_tool_name ?? '';
                      const action = task.action ?? (task.args && typeof task.args === 'object' && task.args.action) ?? '';
                      const argsObj = task.args && typeof task.args === 'object' ? task.args : undefined;
                      return { id, content, status: statusInit, conversation_id: cid, toolName, action, args: argsObj };
                    });
                    console.log('FRONTEND: setCurrentTasks from planner_status:', taskProgressItems);
                    setCurrentTasks(taskProgressItems);
                  }
                  break;
                }
                case 'task_progress':
                  if (actualEventPayload.taskId && actualEventPayload.status) {
                    setCurrentTasks(prevTasks => {
                      const existingTaskIndex = prevTasks.findIndex(t => t.id === actualEventPayload.taskId);
                      
                      if (existingTaskIndex !== -1) {
                        // Update existing task
                        const updatedTasks = [...prevTasks];
                        updatedTasks[existingTaskIndex] = {
                          ...prevTasks[existingTaskIndex],
                          status: actualEventPayload.status,
                          content: actualEventPayload.description || updatedTasks[existingTaskIndex].content,
                          result: actualEventPayload.result,
                          error: actualEventPayload.error,
                          conversation_id: activeConv || convId
                        };
                        console.log('Updated task:', actualEventPayload.taskId, 'to status:', actualEventPayload.status);
                        return updatedTasks;
                      } else if (actualEventPayload.status === 'pending') {
                        // Add new pending task
                        const newTask = {
                          id: actualEventPayload.taskId,
                          status: actualEventPayload.status,
                          content: actualEventPayload.description || `Task ${actualEventPayload.taskId}`,
                          toolName: actualEventPayload.toolName,
                          action: actualEventPayload.action,
                          args: actualEventPayload.args,
                          conversation_id: activeConv || convId
                        };
                        console.log('Adding new pending task:', newTask);
                        return [...prevTasks, newTask];
                      }
                      return prevTasks;
                    });
                  } else if (actualEventPayload.status === 'executing_tasks') {
                    setDispatcherStatus("Dispatcher: executing tasks...");
                  }
                  break;
                case 'dispatcher_done':
                  if (actualEventPayload.results && Array.isArray(actualEventPayload.results)) {
                    // Update tasks with final results
                    setCurrentTasks(prevTasks => {
                      const updatedTasks = [...prevTasks];
                      actualEventPayload.results.forEach(result => {
                        const taskIndex = updatedTasks.findIndex(t => t.id === result.taskId);
                        if (taskIndex !== -1) {
                          updatedTasks[taskIndex] = {
                            ...updatedTasks[taskIndex],
                            status: result.error ? 'error' : 'completed',
                            result: result.output || result.error,
                            error: result.error
                          };
                        }
                      });
                      return updatedTasks;
                    });
                  }
                  setDispatcherStatus("Dispatcher: completed");
                  break;
                case 'dispatcher_event':
                  setDispatcherStatus("Dispatcher: running task...");
                  console.log("FRONTEND: Received dispatcher_event, payload:", actualEventPayload); // DEBUG
                  setCurrentTasks(prevTasks => {
                    console.log("FRONTEND: setCurrentTasks - START - prevTasks:", JSON.parse(JSON.stringify(prevTasks)), "Incoming event payload:", actualEventPayload); // Deep copy for logging
                    
                    // Defensive check
                    if (!actualEventPayload || typeof actualEventPayload.status === 'undefined') {
                      console.error('FRONTEND: setCurrentTasks updater. Critical: actualEventPayload or its status is undefined for dispatcher_event. Payload:', JSON.stringify(actualEventPayload), '. Returning prevTasks.');
                      return prevTasks;
                    }

                    const existingTaskIndex = prevTasks.findIndex(t => t.id === actualEventPayload.tool_call_id);
                    
                    if (actualEventPayload.status === 'started') {
                      const newTask = { 
                        id: actualEventPayload.tool_call_id || `${actualEventPayload.tool_name}-${Date.now()}`, 
                        name: actualEventPayload.tool_name, 
                        content: actualEventPayload.tool_name, // For TaskProgress display
                        input: typeof actualEventPayload.tool_input === 'string' ? actualEventPayload.tool_input : JSON.stringify(actualEventPayload.tool_input, null, 2),
                        status: 'in_progress', // Mapped 'started' to 'in_progress' for TaskProgress component 
                        conversation_id: activeConv || convId // For TaskProgress filtering
                      };
                      if (existingTaskIndex !== -1) {
                         const newTasks = [...prevTasks];
                         newTasks[existingTaskIndex] = newTask;
                         console.log("FRONTEND: setCurrentTasks - returning updated newTasks (existing task modified)", JSON.parse(JSON.stringify(newTasks)));
                         return newTasks;
                      } else {
                         const updatedList = [...prevTasks, newTask];
                         console.log("FRONTEND: setCurrentTasks - returning new task added to list", JSON.parse(JSON.stringify(updatedList)));
                         return updatedList;
                      }
                    } else if (actualEventPayload.status === 'completed' || actualEventPayload.status === 'error') {
                      if (existingTaskIndex !== -1) {
                        const updatedTasks = [...prevTasks];
                        updatedTasks[existingTaskIndex] = {
                          ...prevTasks[existingTaskIndex],
                          status: actualEventPayload.status,
                          output: typeof actualEventPayload.output === 'string' ? actualEventPayload.output : JSON.stringify(actualEventPayload.output, null, 2),
                          error: actualEventPayload.error ? (typeof actualEventPayload.error === 'string' ? actualEventPayload.error : JSON.stringify(actualEventPayload.error, null, 2)) : undefined,
                          // Ensure conversation_id is preserved if it was set
                          conversation_id: prevTasks[existingTaskIndex].conversation_id || activeConv || convId 
                        };
                        console.log("FRONTEND: setCurrentTasks - returning updatedTasks (task status change)", JSON.parse(JSON.stringify(updatedTasks)));
                        return updatedTasks;
                      }
                    }
                    console.log("FRONTEND: setCurrentTasks - returning prevTasks (no change or unmatched condition)", JSON.parse(JSON.stringify(prevTasks)));
                    return prevTasks;
                  });
                  break;
                case 'synthesizer_status':
                  console.log("FRONTEND: Received 'synthesizer_status' event", JSON.stringify(actualEventPayload)); // DEBUG
                  setSynthesizerStatus(`Synthesizer: ${actualEventPayload.status}`);
                  if(actualEventPayload.status === 'started') setDispatcherStatus("Dispatcher: completed, awaiting synthesis.");
                  break;
                case 'assistant_delta':
                  if (plannerStatus) setPlannerStatus(""); 
                  if (dispatcherStatus) setDispatcherStatus("");
                  setSynthesizerStatus("Synthesizer: streaming...");
                  setToolCallStatus("");
                  setCurrentTasks(prev => prev.map(t => (t.status === 'running' ? {...t, status:'completed_implicit'} : t) ));
                  console.log("FRONTEND: Received 'assistant_delta' event payload:", JSON.stringify(actualEventPayload)); // DEBUG
                  setStreamingMessage(prev => {
                    const newContent = (prev?.content || "") + actualEventPayload.delta;
                    console.log("FRONTEND: Updating streamingMessage, new content length:", newContent.length);
                    console.log("FRONTEND: streamingMessage state before update:", prev);
                    const newState = { 
                      ...prev, 
                      content: newContent, 
                      isStreaming: true, 
                      isComplete: false,
                      id: prev?.id || `streaming-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
                    };
                    console.log("FRONTEND: streamingMessage state after update:", newState);
                    return newState;
                  });
                  break;
                case 'interrupted':
                  console.log("FRONTEND: Received 'interrupted' event", JSON.stringify(actualEventPayload));
                  setToolCallStatus("Agent execution interrupted");
                  setStreamingMessage(prev => ({ 
                    ...prev, 
                    content: (prev?.content || "") + "\n\n*Agent execution was interrupted by user*", 
                    isStreaming: false, 
                    isComplete: true 
                  }));
                  setPlannerStatus("");
                  setDispatcherStatus("");
                  setSynthesizerStatus("");
                  setIsSending(false);
                  break;
                
                case 'bulk_retry':
                  console.log("FRONTEND: Received 'bulk_retry' event", JSON.stringify(actualEventPayload));
                  setToolCallStatus(actualEventPayload.message || "Bulk operation continuing...");
                  // Keep streaming state active during bulk operation retry
                  setStreamingMessage(prev => ({ 
                    ...prev, 
                    content: (prev?.content || "") + (actualEventPayload.injectedMessages > 0 ? 
                      `\n\n*Continuing with ${actualEventPayload.injectedMessages} user update(s)...*` : 
                      "\n\n*Continuing bulk operation...*"), 
                    isStreaming: true, 
                    isComplete: false 
                  }));
                  break;
                case 'approval_required':
                  console.log("FRONTEND: Approval required", actualEventPayload);
                  setPendingApproval({
                    id: actualEventPayload.id || Date.now().toString(),
                    type: actualEventPayload.operation_type || 'Operation',
                    description: actualEventPayload.description,
                    impact: actualEventPayload.impact,
                    details: actualEventPayload.details,
                    riskLevel: actualEventPayload.risk_level || 'medium'
                  });
                  // Pause streaming while waiting for approval
                  setStreamingMessage(prev => ({ 
                    ...prev, 
                    isStreaming: false
                  }));
                  break;
                case 'approval_status':
                  console.log("FRONTEND: Approval status update", actualEventPayload);
                  if (actualEventPayload.status === 'approved' || actualEventPayload.status === 'rejected') {
                    setPendingApproval(null);
                    // Resume streaming
                    setStreamingMessage(prev => ({ 
                      ...prev, 
                      isStreaming: true
                    }));
                  } 
                  shouldStop = true; 
                  break;
                case 'error':
                  const errorMsg = actualEventPayload.message || 
                                  actualEventPayload.description || 
                                  (typeof actualEventPayload === 'string' ? actualEventPayload : 'An error occurred');
                  setToolCallStatus(`Error: ${errorMsg}`);
                  console.error("SSE Orchestrator Error:", actualEventPayload);
                  setStreamingMessage(prev => ({ ...prev, content: (prev?.content || "") + `\n\n**Error:** ${errorMsg}`, isStreaming: false, isComplete: true }));
                  setIsSending(false); shouldStop = true; break;
                case 'title_generated':
                  console.log("FRONTEND: Title generated event", actualEventPayload);
                  // Update the conversation title in the UI
                  if (actualEventPayload.title && actualEventPayload.thread_id) {
                    console.log(`New title for thread ${actualEventPayload.thread_id}: ${actualEventPayload.title}`);
                    
                    // Try multiple times to ensure the title is updated
                    const attemptRefresh = (attempt = 1) => {
                      if (onTopicUpdate) {
                        console.log(`FRONTEND: Triggering conversation refresh after title generation (attempt ${attempt})`);
                        // The onTopicUpdate expects (conversationId, topicTitle, topicDetails)
                        // For LangGraph backend, we need to trigger a refresh since it handles titles differently
                        onTopicUpdate(null, null, null); // This will trigger fetchConversations() in App.jsx
                        
                        // Try again after a longer delay if this is the first attempt
                        if (attempt === 1) {
                          setTimeout(() => attemptRefresh(2), 2000);
                        }
                      } else {
                        console.warn("FRONTEND: onTopicUpdate callback not available");
                      }
                    };
                    
                    // First attempt after 1 second
                    setTimeout(() => attemptRefresh(1), 1000);
                  }
                  break;
                  
                case 'done':
                  console.log("FRONTEND: Multi-agent 'done' event", JSON.stringify(actualEventPayload)); // DEBUG
                  
                  // Skip if we're in basic agent mode (already handled above)
                  if (useBasicAgent) {
                    console.log("FRONTEND: Skipping multi-agent done handler (basic agent mode)");
                    break;
                  }
                  
                  // Move streaming message to messages array and clear streaming state in one batch
                  const currentTaskMarkdownRef = taskMarkdown && 
                    String(taskMarkdown.conversation_id) === String(activeConv || convId) 
                    ? taskMarkdown 
                    : null;
                  
                  // Use React 18's automatic batching by performing all state updates together
                  const messageId = `msg-${Date.now()}`;
                  const timestamp = new Date().toISOString();
                  
                  // Capture streaming message content before clearing
                  const streamingContent = streamingMessageRef.current?.content;
                  
                  // Always finalize local streaming message; server history merge below prevents duplicates

                  if (streamingContent && !messageFinalizedRef.current) {
                    // Clear streaming first, then add to messages (dedup if identical content already exists)
                    messageFinalizedRef.current = true; // Mark as finalized
                    
                    // Store the finalized content for duplicate prevention
                    const normalizedContent = (streamingContent || '').trim();
                    
                    // Clear streaming message immediately
                    setStreamingMessage(null);
                    
                    // Use setTimeout to break out of StrictMode's double invocation
                    setTimeout(() => {
                      // Check if we already have this exact content in lastProcessedMessageRef
                      if (lastProcessedMessageRef.current === normalizedContent) {
                        console.log('FRONTEND: Duplicate message detected via lastProcessedMessageRef, skipping');
                        return;
                      }
                      
                      // Update last processed message
                      lastProcessedMessageRef.current = normalizedContent;
                      
                      setMessages(prev => {
                        // Enhanced duplicate check - check last few assistant messages
                        const lastFewMessages = prev.slice(-3);
                        const alreadyExists = lastFewMessages.some(m => 
                          m.role === 'assistant' && 
                          (m.content || '').trim() === normalizedContent
                        );
                        
                        if (alreadyExists) {
                          console.log('FRONTEND: Prevented duplicate message (multi-agent done)');
                          return prev;
                        }
                        
                        console.log('FRONTEND: Adding finalized streaming message');
                        return [...prev, {
                          id: messageId,
                          role: "assistant",
                          content: streamingContent,
                          timestamp: timestamp,
                          taskMarkdown: currentTaskMarkdownRef
                        }];
                      });
                    }, 0);
                  } else {
                    // No content, just clear streaming
                    setStreamingMessage(null);
                  }
                  
                  // Merge any pending server history now that streaming has ended
                  if (Array.isArray(pendingServerHistoryRef.current)) {
                    setMessages(prev => mergeServerAndLocalMessages(pendingServerHistoryRef.current || [], prev));
                    pendingServerHistoryRef.current = null;
                  }

                  setIsSending(false);
                  
                  // CRITICAL: Force shouldStop to true to end the reader loop
                  shouldStop = true;
                  console.log("FRONTEND: Force setting shouldStop=true to terminate stream reader loop");
                  
                  // If there's an active reader, attempt to release/cancel it
                  if (readerRef.current) {
                    try {
                      console.log("FRONTEND: Attempting to cancel reader");
                      readerRef.current.cancel("Stream completed");
                    } catch (e) {
                      console.error("Error cancelling reader:", e);
                    }
                  }
                  
                  setSynthesizerStatus("Synthesizer: completed.");
                  setAgentProcessingStatus(""); // Clear agent status
                  console.log("FRONTEND: 'done' event fully processed");
                  break;
                default:
                  console.log("Unknown agent SSE event type:", eventName, "Payload:", actualEventPayload);
              }
            } else { // Legacy /stream_chat handling
              const data = actualEventPayload; // Use actualEventPayload for legacy too
              if (data.tool_call) {
                const { name, status } = data.tool_call;
                let statusMessage = `Tool ${name}: ${status}`;
                if (status === "started") statusMessage = `Running tool: ${name}...`;
                else if (status === "finished" || status === "ended") statusMessage = `Tool ${name} finished.`;
                else if (status === "error") statusMessage = `Error with tool: ${name}.`;
                setToolCallStatus(statusMessage);
              } else if (data.content || data.delta) {
                setToolCallStatus("");
              }
              if (data.delta) {
                setStreamingMessage(prev => ({ ...prev, content: (prev?.content || "") + data.delta, isStreaming: true, isComplete: false }));
              } else if (data.content) {
                setStreamingMessage(prev => ({ ...prev, content: (prev?.content || "") + data.content, isStreaming: true, isComplete: false }));
              }
              if (data.suggestions) setSuggestions(data.suggestions);
              if (data.tasks) {
                setCurrentTasks(prevTasks => {
                  const newTasks = data.tasks.filter(task => !prevTasks.some(pt => pt.id === task.id || pt.name === task.name));
                  const updatedTasks = prevTasks.map(pt => {
                    const updatedTask = data.tasks.find(t => t.id === pt.id || t.name === pt.name);
                    return updatedTask ? { ...pt, ...updatedTask } : pt;
                  });
                  return [...updatedTasks, ...newTasks];
                });
              }
              // Also check for data.done = true pattern (older style)
              if (data.done === true) {
                console.log("FRONTEND: Received data.done=true");
                // Always finalize local streaming message; server merge prevents duplicates
                // Move streaming content into messages and clear streaming state (legacy)
                const messageId = `msg-${Date.now()}`;
                const timestamp = new Date().toISOString();
                const streamingContent = streamingMessageRef.current?.content;
                if (streamingContent) {
                  setStreamingMessage(null);
                  setMessages(prev => {
                    // Enhanced duplicate check - check last few assistant messages
                    const lastFewMessages = prev.slice(-3);
                    const normalizedContent = (streamingContent || '').trim();
                    const alreadyExists = lastFewMessages.some(m => 
                      m.role === 'assistant' && 
                      (m.content || '').trim() === normalizedContent
                    );
                    
                    if (alreadyExists) {
                      console.log('FRONTEND: Prevented duplicate message (legacy done)');
                      return prev;
                    }
                    
                    return [...prev, {
                      id: messageId,
                      role: "assistant",
                      content: streamingContent,
                      timestamp
                    }];
                  });
                } else {
                  setStreamingMessage(null);
                }
                setIsSending(false); 
                shouldStop = true;
                break;
              }
            }
            } catch (e) {
              console.error("Failed to parse SSE JSON or handle event:", e, "Event Name:", eventName, "JSON String:", rawJsonDataString);
            }
          }
        } catch (e) {
          console.error("Failed to read stream chunk:", e);
          shouldStop = true;
        }
      }
    } catch (e) {
      // Handle timeout specifically for complex operations
      if (e.name === 'AbortError') {
        console.error("Request timed out after 10 minutes");
        
        // Clear the thinking message
        setStreamingMessage(null);
        
        // Add a timeout error message
        const errorMessage = {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: "⏱️ Request timed out after 10 minutes. The operation may still be processing in the background. Please check back later or try a simpler request.",
          timestamp: new Date().toISOString(),
          agent: "system"
        };
        setMessages(prev => [...prev, errorMessage]);
      } else {
        console.error("Failed to send message or process stream:", e);
      }
      
      // Remove the user message that was added optimistically since the request failed
      setMessages(prev => {
        // Remove the last message if it's the user message we just added
        const lastMessage = prev[prev.length - 1];
        if (lastMessage && lastMessage.role === 'user' && lastMessage.content === textToSend) {
          console.log("Removing failed user message from UI");
          return prev.slice(0, -1);
        }
        return prev;
      });
      
      // Show error message instead of echoing user input
      const errorMessage = e.message || "Unable to connect to server";
      setStreamingMessage({
        role: "system",
        content: `⚠️ **Connection Error**\n\n${errorMessage}\n\nPlease check your connection and try again.`,
        timestamp: new Date().toISOString(),
        isStreaming: false,
        isComplete: true,
        isError: true  // Add flag to style error messages differently
      });
      
      // Clean up UI state
      setAgentProcessingStatus("");
      setToolCallStatus("");
    } finally {
      setIsSending(false);
      // setToolCallStatus(""); // Keep agent specific statuses for review
      readerRef.current = null;
    }
  }
  const handleSuggestionClick = (suggestionText) => {
    handleSend(suggestionText);
  };

  // Copy-to-clipboard helper for code blocks (used by MarkdownRenderer via window hook)
  useEffect(() => {
    const copyHandler = async (e) => {
      const target = e.target;
      if (!(target && target.matches && (target.matches('.eb-copy') || target.closest('.eb-copy')))) return;
      const pre = target.closest('pre');
      if (!pre) return;
      const code = pre.querySelector('code');
      if (!code) return;
      try {
        await navigator.clipboard.writeText(code.innerText);
        // Provide quick visual feedback
        target.setAttribute('data-copied', 'true');
        setTimeout(() => target.removeAttribute('data-copied'), 1200);
      } catch (err) {
        console.error('Copy failed', err);
      }
    };
    document.addEventListener('click', copyHandler);
    return () => document.removeEventListener('click', copyHandler);
  }, []);

  // Handle initial message from HomePage
  useEffect(() => {
    const { initialMessage, newConversation, imageAttachment, fileAttachment } = location.state || {};
    
    if ((initialMessage || imageAttachment || fileAttachment) && !messages.length && !loading && !hasProcessedInitialMessage.current) {
      hasProcessedInitialMessage.current = true;
      
      if (newConversation && onNewConversation) {
        onNewConversation();
      }
      
      setInput(initialMessage || '');
      if (imageAttachment) setImageAttachment(imageAttachment);
      if (fileAttachment) setFileAttachment(fileAttachment);

      const timeoutId = setTimeout(() => {
        handleSend(initialMessage || '');
      }, 500);
      
      window.history.replaceState({}, document.title, window.location.pathname);
      
      return () => clearTimeout(timeoutId);
    }
  }, [location.state, messages.length, loading, onNewConversation]);

  return (
    <div className="flex flex-col h-[90vh] w-full max-w-full overflow-x-hidden bg-gradient-to-b from-transparent to-zinc-50 dark:bg-zinc-900">
      {/* Chat messages area */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden px-3 sm:px-6 py-3 sm:py-4 max-w-7xl w-full mx-auto">
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
                className="mx-auto mt-6 mb-2 h-48 w-48 object-contain drop-shadow-lg"
                draggable="false"
              />
              <Text>Start a new conversation by sending a message.
                 Visit the <TextLink href="/about">About</TextLink> page for more information and to learn how to use the bot.
              </Text>
            </div>
          ) : (
            <>
              {/* Show unified task display if tasks are available */}
              {console.log('FRONTEND: Render - taskMarkdown:', taskMarkdown?.conversation_id, 'activeConv:', activeConv, 'convId:', convId)}
              
              {/* Render all messages */}
              {messages.map((msg, i) => {
                // Ensure unique key even if IDs are duplicated
                const uniqueKey = msg.id ? `${msg.id}-${i}` : `msg-${i}`;
                return (
                  <React.Fragment key={uniqueKey}>
                    <div
                      className={`group flex items-start gap-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
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
                      className={`max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm border ${
                          msg.role === "user"
                            ? "bg-white/90 dark:bg-zinc-700/80 text-zinc-900 dark:text-zinc-50 border-zinc-200 dark:border-zinc-700 rounded-tr-none"
                            : "bg-zinc-50/90 dark:bg-zinc-800/80 text-zinc-900 dark:text-zinc-100 border-zinc-200 dark:border-zinc-700 rounded-tl-none"
                        }`}
                      >
                        <div className="w-full break-words max-w-none">
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
                                    e.target.src =
                                      'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgdmlld0JveD0iMCAwIDEwMCAxMDAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjEwMCIgaGVpZ2h0PSIxMDAiIGZpbGw9IiNFRUVFRUUiLz48dGV4dCB4PSI1MCUiIHk9IjUwJSIgZG9taW5hbnQtYmFzZWxpbmU9Im1pZGRsZSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTYiIGZpbGw9IiM5OTk5OTkiPkltYWdlIGVycm9yPC90ZXh0Pjwvc3ZnPg==';
                                  }}
                                />
                              )}
                            </div>
                          )}
                          {msg.fileAttachment && (
                            <div className="mb-3">
                              <div className="inline-flex items-center gap-2 p-2 rounded bg-zinc-100 dark:bg-zinc-800 border dark:border-zinc-700">
                                {msg.fileAttachment.type === 'pdf' && <FileText className="h-4 w-4 text-red-500" />}
                                {msg.fileAttachment.type === 'excel' && <FileSpreadsheet className="h-4 w-4 text-green-500" />}
                                {msg.fileAttachment.type === 'csv' && <FileSpreadsheet className="h-4 w-4 text-blue-500" />}
                                {msg.fileAttachment.type === 'text' && <FileText className="h-4 w-4 text-gray-500" />}
                                {msg.fileAttachment.type === 'file' && <FileIcon className="h-4 w-4 text-gray-500" />}
                                <span className="text-xs">
                                  {msg.fileAttachment.file.name} ({(msg.fileAttachment.file.size / 1024).toFixed(1)}KB)
                                </span>
                              </div>
                            </div>
                          )}
                          {editingMessageId === msg.id ? (
                            <div className="w-full">
                              <Textarea
                                value={editingContent}
                                onChange={(e) => setEditingContent(e.target.value)}
                                className="w-full min-h-[100px] mb-2 p-2 rounded border dark:border-zinc-700"
                                autoFocus
                              />
                              <div className="flex gap-2">
                                <Button
                                  size="sm"
                                  onClick={handleSaveEdit}
                                  disabled={isEditSaving}
                                  className="flex items-center gap-1"
                                >
                                  {isEditSaving ? (
                                    <Loader2 className="h-3 w-3 animate-spin" />
                                  ) : (
                                    <Check className="h-3 w-3" />
                                  )}
                                  Save
                                </Button>
                                <Button
                                  size="sm"
                                  variant="secondary"
                                  onClick={handleCancelEdit}
                                  disabled={isEditSaving}
                                  className="flex items-center gap-1"
                                >
                                  <XCircle className="h-3 w-3" />
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          ) : (
                            <MarkdownRenderer 
                              isAgent={msg.role === "assistant"}
                              key={`final-${msg.id || i}-${(String(msg.content || "")).length}`}
                            >
                              {String(msg.content || "")}
                            </MarkdownRenderer>
                          )}
                        </div>
                        <div
                          className={`text-[11px] mt-2 flex items-center justify-between ${
                            msg.role === "user"
                              ? "text-gray-500 dark:text-gray-400"
                              : "text-zinc-500 dark:text-zinc-400"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {msg.edited_at && (
                              <span className="text-xs italic">edited</span>
                            )}
                            {msg.status === "injected" && (
                              <span className="text-xs italic text-blue-500">injected</span>
                            )}
                            {editingMessageId !== msg.id && !streamingMessage && (
                              <button
                                onClick={() => handleEditMessage(msg.id, msg.content)}
                                className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 p-1 hover:bg-gray-100 dark:hover:bg-zinc-700 rounded border border-transparent hover:border-zinc-200 dark:hover:border-zinc-600"
                                title="Edit message"
                                aria-label="Edit message"
                              >
                                <Edit2 className="h-3 w-3" />
                              </button>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
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
                    </div>
                  </React.Fragment>
                );
              })}


              {/* Render streaming message ONLY while actively streaming; allow override via debugNoDedup */}
              {(() => {
                const lastMsg = messages[messages.length - 1];
                const isDuplicateOfLast = !!(streamingMessage && lastMsg && lastMsg.role === 'assistant' && lastMsg.content === streamingMessage.content);
                return streamingMessage && streamingMessage.isStreaming && (debugNoDedup || !isDuplicateOfLast);
              })() && (
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0">
                    <Avatar
                      className="size-8 bg-blue-100 dark:bg-blue-900/30"
                      alt="ShopifyBot"
                      initials="🤖"
                    />
                  </div>

                  <div 
                    className="max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3 shadow-sm border bg-zinc-50/90 dark:bg-zinc-800/80 text-zinc-900 dark:text-zinc-100 rounded-tl-none border-zinc-200 dark:border-zinc-700"
                    data-state={streamingMessage.isComplete ? "complete" : "streaming"}
                  >
                    <div className="w-full break-words max-w-none">
                      <MarkdownRenderer 
                        isAgent={true}
                        key={`stream-${(streamingMessage.content || "").length}`}
                      >
                        {streamingMessage.content || ""}
                      </MarkdownRenderer>
                      {streamingMessage.isStreaming && !streamingMessage.isError && (
                        <span className="inline-flex items-center text-[11px] text-zinc-500 dark:text-zinc-400 mt-1">
                          <Loader2 className="h-3 w-3 animate-spin mr-1" />
                          <span className="inline-flex">
                            <span className="animate-pulse">•</span>
                            <span className="animate-pulse ml-0.5 delay-150">•</span>
                            <span className="animate-pulse ml-0.5 delay-300">•</span>
                          </span>
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] mt-2 flex items-center justify-end gap-2 text-zinc-500 dark:text-zinc-400">
                      {streamingMessage.isStreaming && !streamingMessage.isError && (
                        <span className="flex items-center">
                          <Loader2 className="h-3 w-3 animate-spin mr-1" />
                          {agentProcessingStatus || toolCallStatus || "Generating..."}
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
      <div className="sticky bottom-0 w-full bg-gradient-to-r from-zinc-50/95 to-zinc-50/90 dark:from-zinc-900/95 dark:to-zinc-900/90 py-3 sm:py-0 border-t border-zinc-200 dark:border-zinc-700 z-0 backdrop-blur">
        {/* Suggestions Area */}
        {((taskMarkdown && taskMarkdown.markdown && 
                String(taskMarkdown.conversation_id) === String(activeConv || convId)) || 
                (currentTasks && currentTasks.length > 0)) && (
                <UnifiedTaskDisplay
                  taskMarkdown={taskMarkdown}
                  liveTasks={currentTasks}
                  onInterrupt={handleInterrupt}
                  isStreaming={isSending}
                  conversationId={activeConv || convId}
                  plannerStatus={plannerStatus}
                  dispatcherStatus={dispatcherStatus}
                  synthesizerStatus={synthesizerStatus}
                />
              )}
        {suggestions && suggestions.length > 0 && !isSending && (
          <div className="max-w-3xl w-full mx-auto px-4 mb-2 flex flex-wrap gap-2 justify-center sm:justify-start">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                type="button"
                className="px-2.5 py-1 text-xs rounded-full border border-zinc-300 dark:border-zinc-700 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                onClick={() => handleSuggestionClick(suggestion)}
                aria-label={`Send suggestion: ${suggestion}`}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

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

        {fileAttachment && (
          <div className="max-w-3xl w-full mx-auto px-4 mb-2">
            <div className="relative inline-block">
              <div className="inline-flex items-center gap-2 p-2 rounded bg-zinc-100 dark:bg-zinc-800 border dark:border-zinc-700">
                {fileAttachment.type === 'pdf' && <FileText className="h-4 w-4 text-red-500" />}
                {fileAttachment.type === 'excel' && <FileSpreadsheet className="h-4 w-4 text-green-500" />}
                {fileAttachment.type === 'csv' && <FileSpreadsheet className="h-4 w-4 text-blue-500" />}
                {fileAttachment.type === 'text' && <FileText className="h-4 w-4 text-gray-500" />}
                {fileAttachment.type === 'file' && <FileIcon className="h-4 w-4 text-gray-500" />}
                <span className="text-xs truncate max-w-[200px]">
                  {fileAttachment.file.name} ({(fileAttachment.file.size / 1024).toFixed(1)}KB)
                </span>
              </div>
              <button 
                onClick={removeFileAttachment}
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

        {/* Approval Request */}
        {pendingApproval && (
          <div className="max-w-3xl w-full mx-auto px-4 mb-4">
            <ApprovalRequest
              operation={pendingApproval}
              onApprove={handleApprove}
              onReject={handleReject}
              isProcessing={isSending}
            />
          </div>
        )}

        {/* Input Form */}
        <form
          className="flex max-w-3xl w-full mx-auto gap-2 items-center"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <div className="flex flex-col gap-2 sm:gap-0 p-2 rounded-xl border border-zinc-200 dark:border-zinc-700 bg-white/90 dark:bg-zinc-900/70 shadow-sm w-full">
            <Textarea
              ref={inputRef}
              value={input}
              rows={textareaRows}
              autoCorrect="off"
              autoComplete="new-password"
              spellCheck={true}
              onChange={(e) => {
                setInput(e.target.value);
                if (e.target.value.trim() !== "" && suggestions.length > 0) {
                  setSuggestions([]);
                }
              }}
              placeholder={
                streamingMessage && streamingMessage.isStreaming && !streamingMessage.isComplete
                  ? "Agent is processing... Type to queue a message"
                  : "Type a message..."
              }
              onKeyDown={(e) => {
                // Cmd/Ctrl + Enter to send
                const isMac = navigator.platform.toUpperCase().includes('MAC');
                const cmdEnter = (isMac ? e.metaKey : e.ctrlKey) && e.key === 'Enter';
                if (cmdEnter) {
                  e.preventDefault();
                  handleSend();
                  return;
                }
                // Enter sends, Shift+Enter inserts newline
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              className="w-full resize-none bg-transparent border-none focus:ring-0 p-2"
            />
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  plain
                  onClick={imageAttachment || showImageUrlInput ? toggleImageUrlInput : handleImageUploadClick}
                  className="h-9 w-9 rounded-full"
                  title={imageAttachment ? "Add from URL instead" : "Add image"}
                  aria-label={imageAttachment ? "Use URL instead" : "Attach image"}
                >
                  <ImageIcon />
                </Button>
                <Button
                  type="button"
                  plain
                  onClick={handleFileUploadClick}
                  className="h-9 w-9 rounded-full"
                  title="Add file (PDF, CSV, Excel, Text)"
                  aria-label="Attach file"
                >
                  <FileIcon />
                </Button>
              </div>
              {/* Show interrupt button when streaming */}
              {streamingMessage && streamingMessage.isStreaming && !streamingMessage.isComplete && (
                <Button
                  type="button"
                  onClick={interruptCurrentTasks}
                  className="h-9 px-3.5 py-2 flex items-center justify-center self-center my-auto mr-2"
                  color="orange"
                  size="sm"
                  title="Interrupt current task"
                >
                  <Square className="h-4 w-4" />
                  <span className="ml-2 hidden sm:inline">Stop</span>
                </Button>
              )}
              
              <Button
                type="submit"
                className="h-9 px-3.5 py-2 flex items-center justify-center self-center my-auto"
                disabled={
                  (!input.trim() && !imageAttachment && !fileAttachment) || isSending
                }
              >
                <Send className="h-5 w-5" />
                <span className="ml-2 hidden sm:inline">
                  {streamingMessage && streamingMessage.isStreaming && !streamingMessage.isComplete
                    ? "Interrupt & Send"
                    : "Send"}
                </span>
              </Button>
            </div>
          </div>
        </form>
        
        {/* Hidden file inputs */}
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          onChange={(e) => handleFileAttachment(e.target.files[0])}
          className="hidden"
          aria-hidden="true"
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.csv,.xlsx,.xls,.txt,.md,.json"
          onChange={(e) => handleFileAttachment(e.target.files[0])}
          className="hidden"
          aria-hidden="true"
        />
      </div>
    </div>
  );
}

export default StreamingChatPage;
