import { logStreamer } from '../services/log-streamer.js';

// Store original console methods
const originalConsoleLog = console.log;
const originalConsoleError = console.error;
const originalConsoleWarn = console.warn;

// Helper to extract category and component from console log
function parseConsoleLog(args) {
  const firstArg = args[0];
  if (typeof firstArg === 'string') {
    // Check for [Component] pattern
    const match = firstArg.match(/^\[([^\]]+)\]\s*(.*)/);
    if (match) {
      const component = match[1];
      const message = match[2] + ' ' + args.slice(1).map(arg => 
        typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
      ).join(' ');
      
      // Determine category based on component
      let category = 'GENERAL';
      if (component.includes('ORCHESTRATOR')) category = 'ORCHESTRATOR';
      else if (component.includes('MCP')) category = 'MCP';
      else if (component.includes('MEMORY')) category = 'MEMORY';
      else if (component.includes('LEARNING')) category = 'LEARNING';
      else if (component.includes('AGENT')) category = 'AGENT';
      else if (component.includes('CONTEXT')) category = 'CONTEXT';
      
      return { category, component, message };
    }
  }
  
  // Fallback for non-formatted logs
  return {
    category: 'GENERAL',
    component: 'System',
    message: args.map(arg => 
      typeof arg === 'object' ? JSON.stringify(arg) : String(arg)
    ).join(' ')
  };
}

// Intercept console.log
export function interceptConsoleForUser(userId) {
  console.log = function(...args) {
    // Call original console.log
    originalConsoleLog.apply(console, args);
    
    // Parse and stream to log drawer if user is set
    if (userId && logStreamer) {
      const { category, component, message } = parseConsoleLog(args);
      const logEntry = logStreamer.createLogEntry(category, 'info', component, message);
      logStreamer.streamLog(userId, logEntry);
    }
  };
  
  console.error = function(...args) {
    // Call original console.error
    originalConsoleError.apply(console, args);
    
    // Stream to log drawer
    if (userId && logStreamer) {
      const { category, component, message } = parseConsoleLog(args);
      const logEntry = logStreamer.createLogEntry(category, 'error', component, message);
      logStreamer.streamLog(userId, logEntry);
    }
  };
  
  console.warn = function(...args) {
    // Call original console.warn
    originalConsoleWarn.apply(console, args);
    
    // Stream to log drawer
    if (userId && logStreamer) {
      const { category, component, message } = parseConsoleLog(args);
      const logEntry = logStreamer.createLogEntry(category, 'warn', component, message);
      logStreamer.streamLog(userId, logEntry);
    }
  };
}

// Restore original console methods
export function restoreConsole() {
  console.log = originalConsoleLog;
  console.error = originalConsoleError;
  console.warn = originalConsoleWarn;
}