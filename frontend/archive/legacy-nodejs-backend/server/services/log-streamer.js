import { EventEmitter } from 'events';

export class LogStreamer extends EventEmitter {
  constructor() {
    super();
    this.clients = new Map(); // userId -> SSE response object
    this.buffers = new Map(); // userId -> circular buffer of logs
    this.bufferSize = 1000; // Keep last 1000 logs per user
  }

  // Add a new SSE client
  addClient(userId, res) {
    // Set SSE headers
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'Access-Control-Allow-Origin': '*'
    });

    // Store the response object
    this.clients.set(userId, res);

    // Send any buffered logs
    const buffer = this.buffers.get(userId) || [];
    buffer.forEach(log => {
      this.sendToClient(res, log);
    });

    // Send initial connection message
    res.write(`data: ${JSON.stringify({ type: 'connected', timestamp: Date.now() })}\n\n`);

    // Handle client disconnect
    res.on('close', () => {
      this.clients.delete(userId);
    });
  }

  // Stream a log entry to connected clients
  streamLog(userId, logEntry) {
    // Add to buffer
    if (!this.buffers.has(userId)) {
      this.buffers.set(userId, []);
    }
    
    const buffer = this.buffers.get(userId);
    buffer.push(logEntry);
    
    // Maintain circular buffer size
    if (buffer.length > this.bufferSize) {
      buffer.shift();
    }

    // Send to connected client if any
    const client = this.clients.get(userId);
    if (client) {
      this.sendToClient(client, logEntry);
    }

    // Emit event for other services
    this.emit('log', { userId, logEntry });
  }

  // Helper to send SSE data
  sendToClient(res, data) {
    try {
      res.write(`data: ${JSON.stringify(data)}\n\n`);
    } catch (error) {
      console.error('Error sending SSE data:', error);
    }
  }

  // Create a formatted log entry
  createLogEntry(category, level, component, message, metadata = {}) {
    return {
      timestamp: Date.now(),
      category,
      level,
      component,
      message,
      metadata
    };
  }

  // Clear buffer for a user
  clearBuffer(userId) {
    this.buffers.delete(userId);
  }

  // Get buffer for debugging
  getBuffer(userId) {
    return this.buffers.get(userId) || [];
  }
}

// Singleton instance
export const logStreamer = new LogStreamer();