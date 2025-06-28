import React from "react";
import { CheckCircle, Clock, AlertTriangle, X, ChevronDown, ChevronUp, ListTodo } from "lucide-react";
import { Text } from "@common/text";
import { Badge } from "@common/badge";

export function TaskDatabaseDisplay({ tasks = [], isExpanded = true }) {
  const [expanded, setExpanded] = React.useState(isExpanded);
  
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
      case "blocked":
        return <X className="h-4 w-4 text-orange-500" />;
      default:
        return <div className="h-4 w-4 border-2 border-gray-300 rounded-full" />;
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case "high":
        return "red";
      case "medium":
        return "yellow";
      case "low":
        return "green";
      default:
        return "gray";
    }
  };

  const completedCount = tasks.filter(t => t.status === "completed").length;
  const inProgressCount = tasks.filter(t => t.status === "in_progress").length;
  const blockedCount = tasks.filter(t => t.status === "blocked").length;
  const totalCount = tasks.length;

  return (
    <div className="mb-4 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-200 dark:border-blue-800 rounded-lg shadow-sm">
      <div className="p-4">
        <div 
          className="flex items-center justify-between cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-center gap-3">
            <ListTodo className="h-5 w-5 text-blue-600 dark:text-blue-400" />
            <Text className="font-semibold text-blue-900 dark:text-blue-100">
              Task Plan
            </Text>
            <div className="flex items-center gap-2">
              <Badge color="green" size="sm">{completedCount} done</Badge>
              {inProgressCount > 0 && (
                <Badge color="blue" size="sm">{inProgressCount} active</Badge>
              )}
              {blockedCount > 0 && (
                <Badge color="orange" size="sm">{blockedCount} blocked</Badge>
              )}
              <Badge color="gray" size="sm">{totalCount} total</Badge>
            </div>
          </div>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          )}
        </div>

        {expanded && (
          <div className="mt-4 space-y-3">
            {/* Progress bar */}
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
              <div 
                className="bg-gradient-to-r from-blue-500 to-indigo-500 h-2 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${totalCount > 0 ? (completedCount / totalCount) * 100 : 0}%` }}
              />
            </div>

            {/* Task list grouped by priority */}
            {['high', 'medium', 'low'].map(priority => {
              const priorityTasks = tasks.filter(t => t.priority === priority);
              if (priorityTasks.length === 0) return null;

              return (
                <div key={priority} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge color={getPriorityColor(priority)} size="sm">
                      {priority} priority
                    </Badge>
                    <Text className="text-xs text-gray-500 dark:text-gray-400">
                      ({priorityTasks.length} tasks)
                    </Text>
                  </div>
                  
                  <div className="space-y-2 ml-4">
                    {priorityTasks.map((task) => (
                      <div key={task.id} className="flex items-start gap-3 group">
                        {getStatusIcon(task.status)}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start gap-2">
                            <Text className="text-xs font-bold text-gray-500 dark:text-gray-400">
                              {task.id}:
                            </Text>
                            <div className="flex-1">
                              <Text 
                                className={`text-sm ${
                                  task.status === "completed" 
                                    ? "line-through text-gray-600 dark:text-gray-400" 
                                    : task.status === "in_progress"
                                    ? "text-blue-700 dark:text-blue-300 font-medium"
                                    : task.status === "blocked"
                                    ? "text-orange-700 dark:text-orange-300"
                                    : "text-gray-900 dark:text-gray-100"
                                }`}
                              >
                                {task.description}
                              </Text>
                              
                              {/* Additional task info */}
                              <div className="mt-1 space-y-1">
                                {task.assignedTo && (
                                  <div className="flex items-center gap-2">
                                    <Text className="text-xs text-gray-500 dark:text-gray-400">
                                      Assigned to:
                                    </Text>
                                    <Badge size="sm" color="blue" className="text-xs">
                                      {task.assignedTo}
                                    </Badge>
                                  </div>
                                )}
                                
                                {task.notes && (
                                  <Text className="text-xs text-gray-600 dark:text-gray-400 italic bg-gray-100 dark:bg-gray-800 rounded px-2 py-1">
                                    {task.status === 'completed' ? '✓' : task.status === 'blocked' ? '⚠' : '→'} {task.notes}
                                  </Text>
                                )}
                                
                                {task.dependencies && task.dependencies.length > 0 && (
                                  <Text className="text-xs text-gray-500 dark:text-gray-400">
                                    Depends on: {task.dependencies.join(', ')}
                                  </Text>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}