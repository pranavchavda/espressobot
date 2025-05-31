import React from "react";
import { CheckCircle, Clock, AlertTriangle, X, Loader2, Circle } from "lucide-react";
import { Button } from "@common/button";
import { Text } from "@common/text";
import { Badge } from "@common/badge";

export function TaskProgress({ tasks, onInterrupt, isStreaming, conversationId }) {
  // Render even with empty tasks array to maintain component presence
  // Only return null if tasks is explicitly null (not undefined or empty array)
  if (tasks === null) {
    return null;
  }

  // Filter tasks by conversationId if provided
  const filteredTasks = conversationId && tasks ? 
    tasks.filter(task => !task.conversation_id || task.conversation_id === conversationId) : 
    tasks || [];

  // Do not filter out completed tasks to ensure they are always visible
  const totalTasks = filteredTasks.length;
  const completedTasks = filteredTasks.filter(task => !task.active).length;
  const progressPercentage = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500 dark:text-green-400" />;
      case "in_progress":
        return <Loader2 className="h-4 w-4 text-blue-500 dark:text-blue-400 animate-spin" />;
      case "pending":
      default:
        return <Circle className="h-4 w-4 text-gray-400 dark:text-gray-500" />;
    }
  };

  // If no tasks exist yet, show an empty state but keep component visible
  if (!filteredTasks || filteredTasks.length === 0) {
    return (
      <div className="task-progress-container mb-4 p-3 bg-gray-100 rounded-lg shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Text className="font-medium text-blue-900 dark:text-blue-100">
              Task Progress
            </Text>
            <span className="text-xs bg-white dark:bg-zinc-800 px-2 py-1 rounded-full text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700">
              0/0
            </span>
          </div>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-3">
          <div className="bg-blue-500 dark:bg-blue-400 rounded-full h-2" style={{ width: '0%' }} />
        </div>
      </div>
    );
  }

  // Log tasks for debugging
  console.log('Rendering TaskProgress with tasks:', filteredTasks);

  return (
    <div className="task-progress-container mb-4 p-3 bg-gray-100 rounded-lg shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Text className="font-medium text-blue-900 dark:text-blue-100">
            Task Progress
          </Text>
          <span className="text-xs bg-white dark:bg-zinc-800 px-2 py-1 rounded-full text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700">
            {completedTasks}/{totalTasks}
          </span>
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
            Interrupt
          </Button>
        )}
      </div>
      {/* Progress bar */}
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mb-3">
        <div 
          className="bg-blue-500 dark:bg-blue-400 h-2 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>
      {/* Task list */}
      <div className="space-y-2">
        {filteredTasks.map((task, index) => (
          <li
            key={index}
            className={`flex items-start p-2 rounded-md ${
              task.status === "completed" || !task.active
                ? "bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
                : task.status === "in_progress"
                ? "bg-blue-50 dark:bg-blue-900/20 font-medium"
                : "bg-gray-100 dark:bg-gray-800"
            }`}
          >
            <span className="mr-2">{getStatusIcon(task.status)}</span>
            <div className="flex-1 min-w-0">
              <Text 
                className={`text-sm ${task.status === "completed" || !task.active ? "line-through text-gray-500 dark:text-gray-400" : ""}`}
              >
                {task.content || task.text || task.title}
              </Text>
              {task.subtasks && task.subtasks.length > 0 && (
                <div className="ml-4 mt-1 space-y-1">
                  {task.subtasks.map((subtask, subIndex) => (
                    <div key={subIndex} className="flex items-start gap-2">
                      {getStatusIcon(subtask.status || "pending")}
                      <Text className="text-xs text-gray-600 dark:text-gray-400">
                        {subtask.content || subtask}
                      </Text>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300">
              {task.status || (task.active ? "pending" : "completed")}
            </span>
          </li>
        ))}
      </div>
    </div>
  );
}