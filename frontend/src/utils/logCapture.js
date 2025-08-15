/**
 * Frontend Log Capture Utility
 * Captures console logs and sends them to the backend for display in the Live Agent Console
 */

class LogCapture {
  constructor() {
    this.enabled = false;
    this.logBuffer = [];
    this.batchTimeout = null;
    this.maxBatchSize = 10;
    this.batchDelay = 500; // ms
    
    // Store original console methods
    this.originalConsole = {
      log: console.log,
      error: console.error,
      warn: console.warn,
      info: console.info,
      debug: console.debug
    };
  }

  /**
   * Start capturing console logs
   */
  start() {
    if (this.enabled) return;
    
    this.enabled = true;
    
    // Override console methods
    console.log = (...args) => {
      this.originalConsole.log(...args);
      this.capture('info', 'FRONTEND', args);
    };
    
    console.error = (...args) => {
      this.originalConsole.error(...args);
      this.capture('error', 'FRONTEND', args);
    };
    
    console.warn = (...args) => {
      this.originalConsole.warn(...args);
      this.capture('warn', 'FRONTEND', args);
    };
    
    console.info = (...args) => {
      this.originalConsole.info(...args);
      this.capture('info', 'FRONTEND', args);
    };
    
    console.debug = (...args) => {
      this.originalConsole.debug(...args);
      this.capture('debug', 'FRONTEND', args);
    };
    
    // Capture uncaught errors
    window.addEventListener('error', this.handleError);
    window.addEventListener('unhandledrejection', this.handleRejection);
    
    console.log('🎬 Frontend log capture started');
  }

  /**
   * Stop capturing console logs
   */
  stop() {
    if (!this.enabled) return;
    
    this.enabled = false;
    
    // Restore original console methods
    console.log = this.originalConsole.log;
    console.error = this.originalConsole.error;
    console.warn = this.originalConsole.warn;
    console.info = this.originalConsole.info;
    console.debug = this.originalConsole.debug;
    
    // Remove error listeners
    window.removeEventListener('error', this.handleError);
    window.removeEventListener('unhandledrejection', this.handleRejection);
    
    // Flush remaining logs
    this.flush();
    
    console.log('🛑 Frontend log capture stopped');
  }

  /**
   * Handle uncaught errors
   */
  handleError = (event) => {
    this.capture('error', 'FRONTEND', [`Uncaught Error: ${event.message}`, {
      filename: event.filename,
      lineno: event.lineno,
      colno: event.colno,
      error: event.error?.stack
    }]);
  };

  /**
   * Handle unhandled promise rejections
   */
  handleRejection = (event) => {
    this.capture('error', 'FRONTEND', [`Unhandled Promise Rejection: ${event.reason}`]);
  };

  /**
   * Capture a log entry
   */
  capture(level, category, args) {
    if (!this.enabled) return;
    
    // Convert arguments to string
    const message = args.map(arg => {
      if (typeof arg === 'object') {
        try {
          return JSON.stringify(arg, null, 2);
        } catch (e) {
          return String(arg);
        }
      }
      return String(arg);
    }).join(' ');
    
    // Determine component based on message content
    let component = 'frontend';
    if (message.includes('[DEBUG]')) component = 'frontend.debug';
    if (message.includes('StreamingChatPage')) component = 'frontend.chat';
    if (message.includes('Agent')) component = 'frontend.agent';
    if (message.includes('Memory')) component = 'frontend.memory';
    
    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      category,
      component,
      message,
      metadata: {
        url: window.location.href,
        userAgent: navigator.userAgent
      }
    };
    
    // Add to buffer
    this.logBuffer.push(logEntry);
    
    // Schedule batch send
    if (!this.batchTimeout) {
      this.batchTimeout = setTimeout(() => this.flush(), this.batchDelay);
    }
    
    // Force flush if buffer is full
    if (this.logBuffer.length >= this.maxBatchSize) {
      this.flush();
    }
  }

  /**
   * Flush log buffer to backend
   */
  async flush() {
    if (this.logBuffer.length === 0) return;
    
    // Clear timeout
    if (this.batchTimeout) {
      clearTimeout(this.batchTimeout);
      this.batchTimeout = null;
    }
    
    // Get logs to send
    const logsToSend = [...this.logBuffer];
    this.logBuffer = [];
    
    try {
      // Send each log entry (could batch these in future)
      for (const log of logsToSend) {
        await fetch('/api/agent/log', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('authToken') || ''}`
          },
          body: JSON.stringify(log)
        });
      }
    } catch (error) {
      // Don't log errors about logging to avoid infinite loop
      this.originalConsole.error('Failed to send logs to backend:', error);
    }
  }

  /**
   * Check if capture is enabled
   */
  isEnabled() {
    return this.enabled;
  }
}

// Create singleton instance
const logCapture = new LogCapture();

// Auto-start if in development or if flag is set
if (process.env.NODE_ENV === 'development' || localStorage.getItem('enableLogCapture') === 'true') {
  // Wait for app to initialize
  setTimeout(() => {
    logCapture.start();
  }, 1000);
}

export default logCapture;