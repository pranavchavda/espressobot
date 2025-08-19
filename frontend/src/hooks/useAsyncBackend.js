/**
 * Hook for async background processing with task tracking
 */

import { useState, useRef, useCallback, useEffect } from 'react';

const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function useAsyncBackend() {
  const [loading, setLoading] = useState(false);
  const [taskStatus, setTaskStatus] = useState(null);
  const [taskResponse, setTaskResponse] = useState('');
  const [taskProgress, setTaskProgress] = useState(0);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const pollIntervalRef = useRef(null);

  // Start async task
  const sendAsyncMessage = useCallback(async (message, conversationId) => {
    setLoading(true);
    setError(null);
    setTaskStatus('pending');
    setTaskResponse('');
    setTaskProgress(0);

    try {
      const requestBody = {
        message,
        conv_id: conversationId,
      };

      const response = await fetch(`${BACKEND_URL}/api/agent/async/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }

      const data = await response.json();
      const { task_id, conversation_id, websocket_url } = data;
      
      setLoading(false);
      
      // Start tracking the task
      startTaskTracking(task_id, conversation_id);
      
      return { task_id, conversation_id };
      
    } catch (err) {
      setError(err.message);
      setLoading(false);
      setTaskStatus('failed');
      throw err;
    }
  }, []);

  // Track task progress via polling (fallback if WebSocket fails)
  const startTaskTracking = useCallback((taskId, conversationId) => {
    // Try WebSocket first (if available)
    const wsUrl = `ws://localhost:8000/api/ws/${conversationId}`;
    
    try {
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected for task tracking');
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'task_update' && data.task_id === taskId) {
            setTaskStatus(data.status);
            setTaskProgress(data.progress || 0);
            setTaskResponse(data.response || '');
            
            if (data.status === 'completed' || data.status === 'failed') {
              setLoading(false);
              if (wsRef.current) {
                wsRef.current.close();
              }
            }
          }
        } catch (err) {
          console.error('WebSocket message parsing error:', err);
        }
      };
      
      wsRef.current.onerror = () => {
        console.log('WebSocket failed, falling back to polling');
        startPolling(taskId);
      };
      
    } catch (err) {
      console.log('WebSocket not available, using polling');
      startPolling(taskId);
    }
  }, []);

  // Polling fallback
  const startPolling = useCallback((taskId) => {
    const pollTaskStatus = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/api/agent/async/task/${taskId}`);
        
        if (response.ok) {
          const data = await response.json();
          setTaskStatus(data.status);
          setTaskProgress(data.progress || 0);
          setTaskResponse(data.response || '');
          
          if (data.status === 'completed' || data.status === 'failed') {
            setLoading(false);
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
            }
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };
    
    // Poll every 500ms
    pollIntervalRef.current = setInterval(pollTaskStatus, 500);
    
    // Initial poll
    pollTaskStatus();
  }, []);

  // Cancel task
  const cancelTask = useCallback(async (taskId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/agent/async/task/${taskId}`, {
        method: 'DELETE',
      });
      
      if (response.ok) {
        setTaskStatus('cancelled');
        setLoading(false);
      }
    } catch (err) {
      console.error('Cancel task error:', err);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  return {
    sendAsyncMessage,
    cancelTask,
    loading,
    taskStatus,
    taskResponse,
    taskProgress,
    error,
  };
}