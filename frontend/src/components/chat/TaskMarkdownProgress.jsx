import React from "react";
import { CheckCircle, Clock, Circle } from "lucide-react";
import { Text } from "@common/text";
import { Badge } from "@common/badge";

export function TaskMarkdownProgress({ markdown, conversationId }) {
  if (!markdown) return null;

  // Parse the markdown to extract tasks
  const lines = markdown.split('\n');
  const tasks = [];
  
  lines.forEach((line, index) => {
    const match = line.match(/^\s*-\s*\[( |x)\]\s*(.+)$/i);
    if (match) {
      const isCompleted = match[1].toLowerCase() === 'x';
      const taskText = match[2].trim();
      const isInProgress = taskText.includes('🔄');
      const cleanText = taskText.replace('🔄 ', '');
      
      tasks.push({
        id: index,
        text: cleanText,
        completed: isCompleted,
        inProgress: isInProgress,
        status: isCompleted ? 'completed' : (isInProgress ? 'in_progress' : 'pending')
      });
    }
  });

  if (tasks.length === 0) return null;

  const completedCount = tasks.filter(t => t.completed).length;
  const progressPercentage = (completedCount / tasks.length) * 100;

  const getStatusIcon = (task) => {
    if (task.completed) {
      return <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />;
    } else if (task.inProgress) {
      return <Clock className="h-4 w-4 text-blue-500 animate-pulse flex-shrink-0" />;
    } else {
      return <Circle className="h-4 w-4 text-gray-300 flex-shrink-0" />;
    }
  };

  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Text className="font-medium text-blue-900 dark:text-blue-100">
            Task Progress
          </Text>
          <Badge color="blue">
            {completedCount}/{tasks.length}
          </Badge>
        </div>
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
        {tasks.map((task) => (
          <div key={task.id} className="flex items-start gap-2">
            {getStatusIcon(task)}
            <Text 
              className={`text-sm ${
                task.completed 
                  ? "line-through text-gray-500 dark:text-gray-400" 
                  : task.inProgress
                  ? "text-blue-700 dark:text-blue-300 font-medium"
                  : "text-gray-900 dark:text-gray-100"
              }`}
            >
              {task.text}
            </Text>
          </div>
        ))}
      </div>
    </div>
  );
}