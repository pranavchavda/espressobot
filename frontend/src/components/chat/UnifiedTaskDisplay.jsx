import React, { useState, useEffect } from 'react';
import { CheckCircle, Clock, Circle, AlertTriangle, ChevronDown, ChevronUp, X } from 'lucide-react';
import { Text, Code } from "@common/text";
import { Badge } from "@common/badge";
import { Button } from "@common/button";

export function UnifiedTaskDisplay({ 
  taskMarkdown, 
  liveTasks, 
  onInterrupt, 
  isStreaming, 
  conversationId,
  plannerStatus,
  dispatcherStatus,
  synthesizerStatus 
}) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [tasks, setTasks] = useState([]);

  useEffect(() => {
    // Merge task data from markdown and live tasks
    const mergedTasks = [];
    
    // First, parse tasks from markdown if available
    if (taskMarkdown?.markdown) {
      const lines = taskMarkdown.markdown.split('\n');
      lines.forEach((line, index) => {
        const match = line.match(/^\s*-\s*\[( |x)\]\s*(.+)$/i);
        if (match) {
          const isCompleted = match[1].toLowerCase() === 'x';
          const taskText = match[2].trim();
          const isInProgress = taskText.includes('🔄');
          const cleanText = taskText.replace('🔄 ', '').replace(/\*\*/g, '');
          
          // Extract task details from markdown format
          const detailMatch = cleanText.match(/^([^:]+):\s*(.+)$/);
          const title = detailMatch ? detailMatch[1].trim() : cleanText;
          const description = detailMatch ? detailMatch[2].trim() : '';
          
          mergedTasks.push({
            id: `md_${index}`,
            title,
            description,
            content: cleanText,
            status: isCompleted ? 'completed' : (isInProgress ? 'in_progress' : 'pending'),
            source: 'markdown'
          });
        }
      });
    }
    
    // Then, merge with live task data
    if (liveTasks && liveTasks.length > 0) {
      liveTasks.forEach((liveTask) => {
        // Try to find corresponding markdown task
        const taskContent = typeof liveTask.content === 'string' 
          ? liveTask.content 
          : (liveTask.content?.description || liveTask.content?.name || 'Task');
          
        const matchingMarkdownTask = mergedTasks.find(mdTask => 
          mdTask.content.toLowerCase().includes(taskContent.toLowerCase()) ||
          taskContent.toLowerCase().includes(mdTask.title.toLowerCase())
        );
        
        if (matchingMarkdownTask) {
          // Update markdown task with live data
          matchingMarkdownTask.status = liveTask.status;
          matchingMarkdownTask.toolName = liveTask.toolName;
          matchingMarkdownTask.action = liveTask.action;
          matchingMarkdownTask.args = liveTask.args;
          matchingMarkdownTask.result = liveTask.result;
          matchingMarkdownTask.error = liveTask.error;
          matchingMarkdownTask.liveId = liveTask.id;
        } else {
          // Add as new task if not found in markdown
          mergedTasks.push({
            id: liveTask.id,
            title: liveTask.toolName || 'Task',
            description: taskContent,
            content: taskContent,
            status: liveTask.status,
            toolName: liveTask.toolName,
            action: liveTask.action,
            args: liveTask.args,
            result: liveTask.result,
            error: liveTask.error,
            source: 'live'
          });
        }
      });
    }
    
    setTasks(mergedTasks);
  }, [taskMarkdown, liveTasks]);

  // Filter tasks by conversation if needed
  const filteredTasks = conversationId && tasks ? 
    tasks.filter(task => !task.conversation_id || task.conversation_id === conversationId) : 
    tasks;

  const showStatus = Boolean(plannerStatus || dispatcherStatus || synthesizerStatus);
  
  if ((!filteredTasks || filteredTasks.length === 0) && !showStatus) {
    return null;
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'in_progress':
        return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />;
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      case 'pending':
      default:
        return <Circle className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'green';
      case 'in_progress':
        return 'blue';
      case 'error':
        return 'red';
      case 'pending':
      default:
        return 'gray';
    }
  };

  const completedTasks = filteredTasks.filter(task => task.status === 'completed').length;
  const totalTasks = filteredTasks.length;
  const progressPercentage = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 hover:opacity-80 transition-opacity"
          >
            <Text className="font-medium text-blue-900 dark:text-blue-100">
              Task Plan
            </Text>
            <Badge color="blue">
              {completedTasks}/{totalTasks}
            </Badge>
            {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          
          {/* Show current execution phase */}
          {(plannerStatus || dispatcherStatus || synthesizerStatus) && (
            <div className="flex items-center gap-1">
              <div className="h-2 w-2 bg-blue-500 rounded-full animate-pulse"></div>
              <Text className="text-xs text-blue-700 dark:text-blue-300">
                {plannerStatus || dispatcherStatus || synthesizerStatus}
              </Text>
            </div>
          )}
        </div>
        
        {isStreaming && onInterrupt && (
          <Button 
            size="sm" 
            variant="outline" 
            color="red"
            onClick={onInterrupt}
            className="flex items-center gap-1"
          >
            <X className="h-3 w-3" />
            Stop
          </Button>
        )}
      </div>

      {/* Progress bar */}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-3">
        <div 
          className="bg-blue-500 h-2 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>

      {/* Task list */}
      {isExpanded && (
        <div className="space-y-2">
          {filteredTasks.map((task) => (
            <div key={task.id} className="flex items-start gap-2">
              {getStatusIcon(task.status)}
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <Text 
                      className={`text-sm font-medium ${
                        task.status === 'completed' 
                          ? "line-through text-gray-600 dark:text-gray-400" 
                          : task.status === 'error'
                          ? "text-red-700 dark:text-red-300"
                          : task.status === 'in_progress'
                          ? "text-blue-700 dark:text-blue-300"
                          : "text-gray-900 dark:text-gray-100"
                      }`}
                    >
                      {task.title}
                      {task.description && task.title !== task.description && (
                        <span className="font-normal text-gray-600 dark:text-gray-400">
                          : {task.description}
                        </span>
                      )}
                    </Text>
                    
                    {/* Show tool and action details */}
                    {(task.toolName || task.action) && (
                      <div className="mt-1 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                        {task.toolName && (
                          <Badge size="sm" color="gray" className="text-xs">
                            {task.toolName}
                          </Badge>
                        )}
                        {task.action && (
                          <Code className="text-xs">
                            {task.action}
                          </Code>
                        )}
                      </div>
                    )}
                    
                    {/* Show task arguments in collapsible format */}
                    {task.args && Object.keys(task.args).length > 0 && (
                      <details className="mt-1 group">
                        <summary className="text-xs text-gray-500 dark:text-gray-400 cursor-pointer select-none hover:text-gray-700 dark:hover:text-gray-300">
                          View parameters
                        </summary>
                        <div className="mt-1 bg-gray-50 dark:bg-gray-800 rounded p-2">
                          <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                            {JSON.stringify(task.args, null, 2)}
                          </pre>
                        </div>
                      </details>
                    )}
                    
                    {/* Show task result if available */}
                    {task.result && (
                      <details className="mt-1 group">
                        <summary className="text-xs text-green-600 dark:text-green-400 cursor-pointer select-none hover:text-green-700 dark:hover:text-green-300">
                          View result
                        </summary>
                        <div className="mt-1 bg-green-50 dark:bg-green-900/20 rounded p-2">
                          <pre className="text-xs text-green-700 dark:text-green-300 whitespace-pre-wrap">
                            {typeof task.result === 'string' ? task.result : JSON.stringify(task.result, null, 2)}
                          </pre>
                        </div>
                      </details>
                    )}
                    
                    {/* Show error if available */}
                    {task.error && (
                      <div className="mt-1 bg-red-50 dark:bg-red-900/20 rounded p-2">
                        <Text className="text-xs text-red-700 dark:text-red-300">
                          Error: {typeof task.error === 'string' ? task.error : JSON.stringify(task.error)}
                        </Text>
                      </div>
                    )}
                  </div>
                  
                  {task.status && (
                    <Badge 
                      size="sm" 
                      color={getStatusColor(task.status)}
                      className="flex-shrink-0"
                    >
                      {task.status}
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}