import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, ChevronLeft, ChevronRight, Minimize2, Maximize2, Download, Search } from 'lucide-react';
import './LogDrawer.css';

const LogDrawer = ({ isOpen, onToggle, token }) => {
  const [logs, setLogs] = useState([]);
  const [filteredLogs, setFilteredLogs] = useState([]);
  const [filter, setFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [drawerWidth, setDrawerWidth] = useState(50); // percentage
  const logContainerRef = useRef(null);
  const eventSourceRef = useRef(null);

  // Connect to SSE endpoint
  useEffect(() => {
    if (isOpen && token) {
      const eventSource = new EventSource(`/api/agent/logs?token=${encodeURIComponent(token)}`);

      eventSource.onmessage = (event) => {
        try {
          const logEntry = JSON.parse(event.data);
          if (logEntry.type !== 'connected') {
            setLogs(prev => [...prev, logEntry]);
          }
        } catch (error) {
          console.error('Error parsing log entry:', error);
        }
      };

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
      };

      eventSourceRef.current = eventSource;

      return () => {
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
        }
      };
    }
  }, [isOpen, token]);

  // Filter logs based on category and search
  useEffect(() => {
    let filtered = logs;
    
    if (filter !== 'ALL') {
      filtered = filtered.filter(log => log.category === filter);
    }
    
    if (searchQuery) {
      filtered = filtered.filter(log => 
        log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.component.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    
    setFilteredLogs(filtered);
  }, [logs, filter, searchQuery]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [filteredLogs, autoScroll]);

  // Handle resize
  const handleResize = useCallback((e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startWidth = drawerWidth;

    const handleMouseMove = (e) => {
      const deltaX = startX - e.clientX;
      const viewportWidth = window.innerWidth;
      const deltaPercent = (deltaX / viewportWidth) * 100;
      const newWidth = Math.max(25, Math.min(75, startWidth + deltaPercent));
      setDrawerWidth(newWidth);
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [drawerWidth]);

  // Export logs
  const exportLogs = () => {
    const logText = logs.map(log => 
      `[${new Date(log.timestamp).toISOString()}] [${log.category}] [${log.level}] [${log.component}] ${log.message}`
    ).join('\n');
    
    const blob = new Blob([logText], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `espressobot-logs-${new Date().toISOString()}.log`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // Format timestamp
  const formatTime = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  // Get log color based on level/category
  const getLogColor = (log) => {
    if (log.level === 'error') return 'log-error';
    if (log.level === 'warn') return 'log-warn';
    
    switch (log.category) {
      case 'ORCHESTRATOR': return 'log-orchestrator';
      case 'MCP': return 'log-mcp';
      case 'MEMORY': return 'log-memory';
      case 'LEARNING': return 'log-learning';
      case 'AGENT': return 'log-agent';
      case 'CONTEXT': return 'log-context';
      default: return 'log-general';
    }
  };

  if (!isOpen) {
    return (
      <button 
        className="log-drawer-toggle"
        onClick={onToggle}
        title="Open Log Console (Ctrl/Cmd + Shift + L)"
      >
        <ChevronLeft size={20} />
      </button>
    );
  }

  return (
    <div className="log-drawer" style={{ width: `${drawerWidth}%` }}>
      <div className="log-drawer-resize-handle" onMouseDown={handleResize} />
      
      <div className="log-drawer-header">
        <div className="log-drawer-title">
          <span className="log-drawer-status">🔴</span>
          Live Agent Console
        </div>
        <div className="log-drawer-controls">
          <button onClick={() => setDrawerWidth(25)} title="Minimize">
            <Minimize2 size={16} />
          </button>
          <button onClick={() => setDrawerWidth(50)} title="Half">
            □
          </button>
          <button onClick={() => setDrawerWidth(75)} title="Maximize">
            <Maximize2 size={16} />
          </button>
          <button onClick={onToggle} title="Close">
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="log-drawer-filters">
        <select 
          value={filter} 
          onChange={(e) => setFilter(e.target.value)}
          className="log-filter-select"
        >
          <option value="ALL">All Categories</option>
          <option value="ORCHESTRATOR">Orchestrator</option>
          <option value="MCP">MCP Tools</option>
          <option value="MEMORY">Memory</option>
          <option value="LEARNING">Learning</option>
          <option value="AGENT">Agents</option>
          <option value="CONTEXT">Context</option>
          <option value="ERROR">Errors</option>
        </select>

        <div className="log-search">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <label className="log-autoscroll">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
          />
          Auto-scroll
        </label>

        <button onClick={exportLogs} title="Export logs" className="log-export-btn">
          <Download size={16} />
        </button>
      </div>

      <div className="log-container" ref={logContainerRef}>
        {filteredLogs.length === 0 ? (
          <div className="log-empty">
            {logs.length === 0 ? 'Waiting for logs...' : 'No logs match your filters'}
          </div>
        ) : (
          filteredLogs.map((log, index) => (
            <div key={index} className={`log-entry ${getLogColor(log)}`}>
              <span className="log-time">{formatTime(log.timestamp)}</span>
              <span className="log-category">[{log.category}]</span>
              <span className="log-component">[{log.component}]</span>
              <span className="log-message">{log.message}</span>
              {log.metadata && Object.keys(log.metadata).length > 0 && (
                <span className="log-metadata">
                  {JSON.stringify(log.metadata)}
                </span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default LogDrawer;