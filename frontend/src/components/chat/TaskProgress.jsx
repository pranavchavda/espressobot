import React from "react";
import { CheckCircle, Clock, AlertTriangle, X } from "lucide-react";
import { Button } from "@common/button";
import { Text } from "@common/text";
import { Badge } from "@common/badge";

export function TaskProgress({ tasks, onInterrupt, isStreaming }) {
  if (!tasks || tasks.length === 0) {
    return null;
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "in_progress":
        return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />;
      case "pending":
        return <div className="h-4 w-4 border-2 border-gray-300 rounded-full" />;
      case "error":
        return <AlertTriangle className="h-4 w-4 text-red-500" />;
      default:
        return <div className="h-4 w-4 border-2 border-gray-300 rounded-full" />;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "completed":
        return "green";
      case "in_progress":
        return "blue";
      case "pending":
        return "gray";
      case "error":
        return "red";
      default:
        return "gray";
    }
  };

  const completedTasks = tasks.filter(task => task.status === "completed").length;
  const totalTasks = tasks.length;
  const progressPercentage = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Text className="font-medium text-blue-900 dark:text-blue-100">
            Agent Task Progress
          </Text>
          <Badge color="blue">
            {completedTasks}/{totalTasks}
          </Badge>
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
      <div className="space-y-2">
        {tasks.map((task, index) => (
          <div key={task.id || index} className="flex items-start gap-2">
            {getStatusIcon(task.status)}
            <div className="flex-1 min-w-0">
              <Text 
                className={`text-sm ${
                  task.status === "completed" 
                    ? "line-through text-gray-600 dark:text-gray-400" 
                    : "text-gray-900 dark:text-gray-100"
                }`}
              >
                {task.content}
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
            {task.status && (
              <Badge 
                size="sm" 
                color={getStatusColor(task.status)}
                className="ml-2"
              >
                {task.status}
              </Badge>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}