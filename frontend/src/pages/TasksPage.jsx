
import { useState, useEffect } from "react";
import {
  PlusCircle,
  RefreshCw,
  XCircle,
  Edit,
  Trash,
  Calendar,
  CheckCircle,
  Save,
  X,
} from "lucide-react";
import { Heading } from "../components/common/heading";
import { Button } from "../components/common/button";
import { Text } from "../components/common/text";
import { Input } from "../components/common/input";
import { Textarea } from "../components/common/textarea";

function TasksPage() {
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState({ title: "", notes: "", due: "" });
  const [selectedTaskList, setSelectedTaskList] = useState("@default");
  const [taskLists, setTaskLists] = useState([]);
  const [error, setError] = useState(null);
  const [editingTask, setEditingTask] = useState(null);

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
        `/api/tasks?tasklist_id=${selectedTaskList}`
      );
      const data = await response.json();
      if (Array.isArray(data)) {
        setTasks(data);
      } else {
        console.error("Invalid tasks data:", data);
        if (data.error) {
          setError(data.error);
        }
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
    if (!newTask.title.trim()) {
      setError("Task title is required");
      return;
    }

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

      const data = await response.json();
      if (data.error) {
        setError(data.error);
      } else {
        setNewTask({ title: "", notes: "", due: "" });
        fetchTasks();
      }
    } catch (err) {
      console.error("Error creating task:", err);
      setError("Failed to create task");
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteTask = async (taskId, isCompleted) => {
    try {
      setLoading(true);
      const method = isCompleted ? "PUT" : "POST"; // PUT for updating status, POST for completing
      const endpoint = isCompleted 
        ? `/api/tasks/${taskId}`
        : `/api/tasks/${taskId}/complete`;
      
      const body = isCompleted
        ? JSON.stringify({ status: "needsAction", tasklist_id: selectedTaskList })
        : null;
      
      const options = {
        method,
        headers: {
          "Content-Type": "application/json",
        },
      };
      
      if (body) {
        options.body = body;
      }
      
      const response = await fetch(endpoint, options);
      
      const data = await response.json();
      if (data.error) {
        setError(data.error);
      } else {
        fetchTasks();
      }
    } catch (err) {
      console.error("Error updating task status:", err);
      setError(`Failed to ${isCompleted ? "uncheck" : "complete"} task`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!confirm("Are you sure you want to delete this task?")) {
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(
        `/api/tasks/${taskId}?tasklist_id=${selectedTaskList}`,
        {
          method: "DELETE",
        }
      );

      const data = await response.json();
      if (data.error) {
        setError(data.error);
      } else {
        fetchTasks();
      }
    } catch (err) {
      console.error("Error deleting task:", err);
      setError("Failed to delete task");
    } finally {
      setLoading(false);
    }
  };

  const startEditingTask = (task) => {
    setEditingTask({
      id: task.id,
      title: task.title || "",
      notes: task.notes || "",
      due: task.due ? task.due.split('T')[0] : "",
    });
  };

  const cancelEditingTask = () => {
    setEditingTask(null);
  };

  const saveTaskChanges = async () => {
    if (!editingTask || !editingTask.title.trim()) {
      setError("Task title is required");
      return;
    }

    try {
      setLoading(true);
      const response = await fetch(`/api/tasks/${editingTask.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: editingTask.title,
          notes: editingTask.notes,
          due: editingTask.due,
          tasklist_id: selectedTaskList,
        }),
      });

      const data = await response.json();
      if (data.error) {
        setError(data.error);
      } else {
        fetchTasks();
        setEditingTask(null);
      }
    } catch (err) {
      console.error("Error updating task:", err);
      setError("Failed to update task");
    } finally {
      setLoading(false);
    }
  };

  if (loading && !tasks.length) {
    return (
      <div className="flex justify-center items-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary"></div>
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

      {taskLists.length > 1 && (
        <div className="mb-4">
          <select
            value={selectedTaskList}
            onChange={(e) => setSelectedTaskList(e.target.value)}
            className="w-full p-2 border rounded dark:bg-zinc-800 dark:border-zinc-700"
          >
            {taskLists.map((list) => (
              <option key={list.id} value={list.id}>
                {list.title}
              </option>
            ))}
          </select>
        </div>
      )}

      <form onSubmit={handleCreateTask} className="mb-6">
        <div className="bg-white dark:bg-zinc-800 p-4 rounded-lg shadow-sm">
          <div className="mb-4">
            <Input
              placeholder="Add a new task..."
              value={newTask.title}
              onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
              className="w-full"
            />
          </div>
          <div className="mb-4">
            <Textarea
              placeholder="Add notes (optional)"
              value={newTask.notes}
              onChange={(e) => setNewTask({ ...newTask, notes: e.target.value })}
              className="w-full h-20"
            />
          </div>
          <div className="mb-4">
            <Input
              type="date"
              value={newTask.due}
              onChange={(e) => setNewTask({ ...newTask, due: e.target.value })}
              className="w-full"
            />
          </div>
          <Button
            type="submit"
            className="w-full flex items-center justify-center gap-2"
            disabled={loading}
          >
            <PlusCircle className="h-5 w-5" />
            Add Task
          </Button>
        </div>
      </form>

      <div className="space-y-2">
        {tasks.length === 0 ? (
          <div className="text-center p-6 bg-white dark:bg-zinc-800 rounded-lg">
            <Text>No tasks found. Create a new task above.</Text>
          </div>
        ) : (
          tasks.map((task) => (
            <div
              key={task.id}
              className={`p-4 bg-white dark:bg-zinc-800 rounded-lg shadow-sm hover:shadow-md transition-shadow ${
                task.status === "completed" ? "opacity-70" : ""
              }`}
            >
              {editingTask && editingTask.id === task.id ? (
                <div className="space-y-3">
                  <Input
                    value={editingTask.title}
                    onChange={(e) => setEditingTask({ ...editingTask, title: e.target.value })}
                    className="w-full font-medium"
                  />
                  <Textarea
                    value={editingTask.notes}
                    onChange={(e) => setEditingTask({ ...editingTask, notes: e.target.value })}
                    className="w-full h-20"
                  />
                  <Input
                    type="date"
                    value={editingTask.due}
                    onChange={(e) => setEditingTask({ ...editingTask, due: e.target.value })}
                    className="w-full"
                  />
                  <div className="flex justify-end gap-2 mt-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={cancelEditingTask}
                      className="flex items-center gap-1"
                    >
                      <X className="h-4 w-4" />
                      Cancel
                    </Button>
                    <Button
                      size="sm"
                      onClick={saveTaskChanges}
                      className="flex items-center gap-1"
                    >
                      <Save className="h-4 w-4" />
                      Save
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-3">
                      <button
                        onClick={() => handleCompleteTask(task.id, task.status === "completed")}
                        className="mt-1 flex-shrink-0"
                      >
                        {task.status === "completed" ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : (
                          <div className="h-5 w-5 border-2 rounded-full"></div>
                        )}
                      </button>
                      <div className="flex-grow">
                        <Text
                          className={`font-medium ${
                            task.status === "completed" ? "line-through" : ""
                          }`}
                        >
                          {task.title}
                        </Text>
                        {task.notes && (
                          <Text className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {task.notes}
                          </Text>
                        )}
                        {task.due && (
                          <div className="flex items-center text-gray-500 text-sm mt-1">
                            <Calendar className="h-3 w-3 mr-1" />
                            {new Date(task.due).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => startEditingTask(task)}
                        className="p-1 text-gray-500 hover:text-blue-500"
                      >
                        <Edit className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDeleteTask(task.id)}
                        className="p-1 text-gray-500 hover:text-red-500"
                      >
                        <Trash className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default TasksPage;
