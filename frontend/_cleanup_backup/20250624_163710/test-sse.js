// A simplified version of the SSE handler to diagnose the issue
import { Router } from 'express';
const router = Router();

// Helper to send SSE messages - using the simplest proven format
router.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>SSE Test</title>
      <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        #messages { border: 1px solid #ccc; padding: 10px; height: 300px; overflow-y: auto; margin-bottom: 10px; }
        .message { margin-bottom: 5px; }
        button { padding: 8px 16px; }
      </style>
    </head>
    <body>
      <h1>SSE Test Client</h1>
      <div id="status">Status: Disconnected</div>
      <div id="messages"></div>
      <button id="connect">Connect</button>
      <button id="disconnect">Disconnect</button>
      
      <script>
        const statusEl = document.getElementById('status');
        const messagesEl = document.getElementById('messages');
        const connectBtn = document.getElementById('connect');
        const disconnectBtn = document.getElementById('disconnect');
        
        let eventSource = null;
        
        function addMessage(type, data) {
          const msgEl = document.createElement('div');
          msgEl.className = 'message';
          msgEl.textContent = \`[\${new Date().toLocaleTimeString()}] \${type}: \${JSON.stringify(data)}\`;
          messagesEl.appendChild(msgEl);
          messagesEl.scrollTop = messagesEl.scrollHeight;
        }
        
        connectBtn.addEventListener('click', () => {
          if (eventSource) {
            addMessage('Info', 'Already connected');
            return;
          }
          
          eventSource = new EventSource('/api/sse/test');
          statusEl.textContent = 'Status: Connecting...';
          
          eventSource.onopen = () => {
            statusEl.textContent = 'Status: Connected';
            addMessage('Info', 'Connection opened');
          };
          
          eventSource.onerror = (err) => {
            statusEl.textContent = 'Status: Error';
            addMessage('Error', err);
          };
          
          // Generic message handler
          eventSource.onmessage = (event) => {
            addMessage('Generic message', event.data);
          };
          
          // Specific event handlers
          eventSource.addEventListener('test_event', (event) => {
            const data = JSON.parse(event.data);
            addMessage('test_event', data);
          });
          
          eventSource.addEventListener('assistant_delta', (event) => {
            const data = JSON.parse(event.data);
            addMessage('assistant_delta', data);
          });
          
          eventSource.addEventListener('done', (event) => {
            const data = JSON.parse(event.data);
            addMessage('done', data);
            // Close connection on done
            eventSource.close();
            eventSource = null;
            statusEl.textContent = 'Status: Disconnected (received done)';
          });
        });
        
        disconnectBtn.addEventListener('click', () => {
          if (eventSource) {
            eventSource.close();
            eventSource = null;
            statusEl.textContent = 'Status: Disconnected';
            addMessage('Info', 'Connection closed by user');
          } else {
            addMessage('Info', 'Not connected');
          }
        });
      </script>
    </body>
    </html>
  `);
});

export default router;
