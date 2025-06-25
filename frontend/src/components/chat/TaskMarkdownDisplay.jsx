import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { ChevronDown, ChevronUp, CheckCircle2, Circle, Clock, AlertCircle } from 'lucide-react';

const TaskMarkdownDisplay = ({ taskMarkdown, isExpanded: defaultExpanded = true }) => {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [taskStatuses, setTaskStatuses] = useState({});

  useEffect(() => {
    if (taskMarkdown?.markdown) {
      // Parse task statuses from markdown
      const lines = taskMarkdown.markdown.split('\n');
      const statuses = {};
      lines.forEach((line, index) => {
        const match = line.match(/^\s*-\s*\[([ x])\]\s*\*\*([^:]+)\*\*:/i);
        if (match) {
          const taskId = match[2];
          const isCompleted = match[1].toLowerCase() === 'x';
          const isInProgress = line.includes('🔄');
          statuses[taskId] = isCompleted ? 'completed' : (isInProgress ? 'in_progress' : 'pending');
        }
      });
      setTaskStatuses(statuses);
    }
  }, [taskMarkdown]);

  if (!taskMarkdown || !taskMarkdown.markdown) {
    return null;
  }

  const getTaskIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'in_progress':
        return <Clock className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'pending':
        return <Circle className="w-4 h-4 text-gray-400" />;
      default:
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
    }
  };

  // Custom renderer for checkboxes to add icons
  const customComponents = {
    li: ({ children, ...props }) => {
      // Extract task ID from the content
      const content = children?.toString() || '';
      const taskIdMatch = content.match(/\*\*([^:]+)\*\*:/);
      const taskId = taskIdMatch ? taskIdMatch[1] : null;
      const status = taskId ? taskStatuses[taskId] : 'pending';
      
      return (
        <li className="flex items-start gap-2 mb-2" {...props}>
          {getTaskIcon(status)}
          <div className="flex-1">{children}</div>
        </li>
      );
    },
    h1: ({ children }) => (
      <h1 className="text-lg font-bold mb-3">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-md font-semibold mb-2 mt-4">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-sm font-semibold mb-2 mt-3">{children}</h3>
    ),
    p: ({ children }) => (
      <p className="text-sm mb-2">{children}</p>
    ),
    ul: ({ children }) => (
      <ul className="list-none space-y-1 ml-4">{children}</ul>
    ),
    hr: () => <hr className="my-3 border-gray-300 dark:border-gray-600" />
  };

  return (
    <div className="mb-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-blue-700 dark:text-blue-300">
            Task Plan
          </span>
          <span className="text-xs text-blue-600 dark:text-blue-400">
            ({taskMarkdown.taskCount} tasks)
          </span>
        </div>
        <button className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300">
          {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
      </div>
      
      {isExpanded && (
        <div className="mt-3 text-sm text-gray-700 dark:text-gray-300">
          <ReactMarkdown components={customComponents}>
            {taskMarkdown.markdown}
          </ReactMarkdown>
        </div>
      )}
    </div>
  );
};

export default TaskMarkdownDisplay;