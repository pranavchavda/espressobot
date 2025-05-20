import React, { useState, useEffect } from "react";
import { Button } from "@common/button";
import { Input } from "@common/input";
import { Textarea } from "@common/textarea";
import {
  CalendarIcon,
  CheckIcon,
  Clock,
  PlusIcon,
  RefreshCw,
  Trash2,
  XCircle,
} from "lucide-react";
import { Text } from "@common/text";
import { Heading } from "@common/heading";
import { Badge } from "@common/badge";
import { format, parseISO, isValid } from "date-fns";

function TasksPage() {
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState({ title: "", notes: "", due: "" });
  const [selectedTaskList, setSelectedTaskList] = useState("@default");
  const [taskLists, setTaskLists] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    checkAuthStatus();
  }, []);

  useEffect(() => {
    if (isAuthorized) {
      fetchTaskLists();
      fetchTasks();
    }
  }, [isAuthorized, selectedTaskList]);

  const checkAuthStatus = async () => {
    try {
      setLoading(true);
      const response = await fetch("/api/tasks/auth_status");
      const data = await response.json();
      setIsAuthorized(data.is_authorized);
    } catch (err) {
      console.error("Error checking auth status:", err);
      setError("Failed to check Google Tasks authorization");
    } finally {
      setLoading(false);
    }
  };

  const fetchTaskLists = async () => {
    try {
      const response = await fetch("/api/tasks/lists");
      const data = await response.json();
      if (Array.isArray(data)) {
        setTaskLists(data);
      } else {
        console.error("Invalid task lists data:", data);
      }
    } catch (err) {
      console.error("Error fetching task lists:", err);
      setError("Failed to fetch task lists");
    }
  };

  const fetchTasks = async () => {
    try {
      setLoading(true);
      const response = await fetch(
        `/api/tasks?tasklist_id=${selectedTaskList}`,
      );
      const data = await response.json();
      if (Array.isArray(data)) {
        // Sort tasks: incomplete first, then by due date
        const sortedTasks = data.sort((a, b) => {
          // First, sort by status (needsAction before completed)
          if (a.status === "needsAction" && b.status === "completed") return -1;
          if (a.status === "completed" && b.status === "needsAction") return 1;

          // Then sort by due date if both have one
          if (a.due && b.due) return new Date(a.due) - new Date(b.due);
          if (a.due) return -1;
          if (b.due) return 1;

          // Default sort by title
          return a.title.localeCompare(b.title);
        });
        setTasks(sortedTasks);
      } else {
        console.error("Invalid tasks data:", data);
      }
    } catch (err) {
      console.error("Error fetching tasks:", err);
      setError("Failed to fetch tasks");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    if (!newTask.title.trim()) return;

    try {
      setLoading(true);
      const response = await fetch("/api/tasks", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ...newTask,
          tasklist_id: selectedTaskList,
        }),
      });

      if (response.ok) {
        setNewTask({ title: "", notes: "", due: "" });
        fetchTasks();
      } else {
        const error = await response.json();
        setError(error.error || "Failed to create task");
      }
    } catch (err) {
      console.error("Error creating task:", err);
      setError("Failed to create task");
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteTask = async (taskId) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/tasks/${taskId}/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tasklist_id: selectedTaskList,
        }),
      });

      if (response.ok) {
        fetchTasks();
      } else {
        const error = await response.json();
        setError(error.error || "Failed to complete task");
      }
    } catch (err) {
      console.error("Error completing task:", err);
      setError("Failed to complete task");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!window.confirm("Are you sure you want to delete this task?")) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(
        `/api/tasks/${taskId}?tasklist_id=${selectedTaskList}`,
        {
          method: "DELETE",
        },
      );

      if (response.ok) {
        fetchTasks();
      } else {
        const error = await response.json();
        setError(error.error || "Failed to delete task");
      }
    } catch (err) {
      console.error("Error deleting task:", err);
      setError("Failed to delete task");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "";

    try {
      const date = parseISO(dateString);
      if (!isValid(date)) return "Invalid date";
      return format(date, "MMM d, yyyy");
    } catch (err) {
      console.error("Error formatting date:", err);
      return "Invalid date";
    }
  };

  if (loading && !isAuthorized) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-500" />
          <Text>Checking Google Tasks authorization...</Text>
        </div>
      </div>
    );
  }

  if (!isAuthorized) {
    return (
      <div className="flex flex-col items-center justify-center h-full">
        <div className="text-center max-w-md mx-auto p-6 bg-white dark:bg-zinc-800 rounded-lg shadow-md">
          <Heading className="mb-4">Connect to Google Tasks</Heading>
          <Text className="mb-6">
            You need to authorize this app to access your Google Tasks.
          </Text>
          <Button
            onClick={() => (window.location.href = "/api/authorize/google")}
            className="mx-auto"
          >
            Connect Google Tasks
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="container max-w-4xl mx-auto p-4">
      <div className="flex justify-between items-center mb-6">
        <Heading level={1}>Google Tasks</Heading>
        <Button
          size="sm"
          variant="outline"
          onClick={fetchTasks}
          className="flex items-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="bg-red-100 dark:bg-red-900/30 border border-red-300 dark:border-red-700 text-red-800 dark:text-red-200 px-4 py-3 rounded mb-4 flex items-start justify-between">
          <span>{error}</span>
          <XCircle
            className="h-5 w-5 cursor-pointer"
            onClick={() => setError(null)}
          />
        </div>
      )}

      {/* Task List Selector */}
      {taskLists.length > 0 && (
        <div className="mb-6">
          <label
            htmlFor="taskListSelect"
            className="block text-sm font-medium mb-2"
          >
            Task List
          </label>
          <select
            id="taskListSelect"
            value={selectedTaskList}
            onChange={(e) => setSelectedTaskList(e.target.value)}
            className="w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-zinc-800 dark:border-zinc-700"
          >
            <option value="@default">Default</option>
            {taskLists.map((list) => (
              <option key={list.id} value={list.id}>
                {list.title}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* New Task Form */}
      <form
        onSubmit={handleCreateTask}
        className="mb-8 p-4 bg-white dark:bg-zinc-800 rounded-lg shadow-sm"
      >
        <div className="mb-4">
          <Input
            type="text"
            value={newTask.title}
            onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
            placeholder="New task title"
            className="w-full"
          />
        </div>
        <div className="mb-4">
          <Textarea
            value={newTask.notes}
            onChange={(e) => setNewTask({ ...newTask, notes: e.target.value })}
            placeholder="Add notes (optional)"
            className="w-full"
            rows={2}
          />
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <label htmlFor="dueDate" className="mr-2 text-sm">
              Due Date:
            </label>
            <Input
              id="dueDate"
              type="date"
              value={newTask.due}
              onChange={(e) => setNewTask({ ...newTask, due: e.target.value })}
              className="w-32"
            />
          </div>
          <Button
            type="submit"
            disabled={!newTask.title.trim() || loading}
            className="flex items-center gap-2"
          >
            <PlusIcon className="h-4 w-4" />
            Add Task
          </Button>
        </div>
      </form>

      {/* Tasks List */}
      <div className="space-y-4">
        {loading ? (
          <div className="flex justify-center p-8">
            <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 dark:bg-zinc-800 rounded-lg">
            <Text className="text-gray-500 dark:text-gray-400">
              No tasks found
            </Text>
          </div>
        ) : (
          tasks.map((task) => (
            <div
              key={task.id}
              className={`p-4 border rounded-lg flex items-start gap-3 ${
                task.status === "completed"
                  ? "bg-gray-50 dark:bg-zinc-800/50 border-gray-200 dark:border-zinc-700"
                  : "bg-white dark:bg-zinc-800 border-gray-200 dark:border-zinc-700"
              }`}
            >
              <button
                onClick={() => handleCompleteTask(task.id)}
                className={`flex-shrink-0 h-6 w-6 mt-0.5 rounded-full border ${
                  task.status === "completed"
                    ? "bg-green-500 border-green-500 text-white"
                    : "border-gray-300 dark:border-gray-600"
                } flex items-center justify-center`}
                aria-label={
                  task.status === "completed"
                    ? "Mark as incomplete"
                    : "Mark as complete"
                }
              >
                {task.status === "completed" && (
                  <CheckIcon className="h-4 w-4" />
                )}
              </button>

              <div className="flex-grow min-w-0">
                <div className="flex items-start justify-between">
                  <h3
                    className={`font-medium ${
                      task.status === "completed"
                        ? "line-through text-gray-500 dark:text-gray-400"
                        : ""
                    }`}
                  >
                    {task.title}
                  </h3>
                  <button
                    onClick={() => handleDeleteTask(task.id)}
                    className="text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 p-1"
                    aria-label="Delete task"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                {task.notes && (
                  <p
                    className={`mt-1 text-sm ${
                      task.status === "completed"
                        ? "text-gray-400 dark:text-gray-500"
                        : "text-gray-600 dark:text-gray-300"
                    }`}
                  >
                    {task.notes}
                  </p>
                )}

                {task.due && (
                  <div className="mt-2">
                    <Badge
                      variant={
                        task.status === "completed" ? "outline" : "secondary"
                      }
                      className="flex items-center gap-1 text-xs"
                    >
                      <CalendarIcon className="h-3 w-3" />
                      {formatDate(task.due)}
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default TasksPage;
