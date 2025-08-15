/**
 * Hook to use LangGraph backend directly
 */

import { useState, useRef, useCallback } from 'react';

const BACKEND_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function useLangGraphBackend() {
  const [loading, setLoading] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState(null);
  const eventSourceRef = useRef(null);

  const sendMessage = useCallback(async (message, conversationId, attachments = {}) => {
    setLoading(true);
    setStreamingMessage('');

    // Close any existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const requestBody = {
        message,
        conv_id: conversationId,
        ...attachments
      };

      const response = await fetch(`${BACKEND_URL}/api/agent/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }

      // Handle SSE streaming
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.message) {
                setStreamingMessage(data.message);
              }
              
              if (data.tokens && data.tokens.length > 0) {
                setStreamingMessage(prev => prev + data.tokens.join(''));
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error sending message to LangGraph backend:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  }, []);

  const interrupt = useCallback(async () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setLoading(false);
  }, []);

  return {
    sendMessage,
    interrupt,
    loading,
    streamingMessage,
    backendUrl: BACKEND_URL
  };
}