
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
  PlusCircleIcon,
} from "lucide-react";
import { Heading } from "../components/common/heading";
import { Button } from "../components/common/button";
import { Text } from "../components/common/text";
import { Input } from "../components/common/input";
import { Textarea } from "../components/common/textarea";
import { Badge } from "../components/common/badge";
import { Dialog, DialogActions, DialogBody, DialogDescription, DialogTitle } from '../components/common/dialog'

function TasksPage() { // This is the start of the correct TasksPage function (line 365)
  const [isAuthorized, setIsAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [newTask, setNewTask] = useState({ title: "", notes: "", due: "" });
  const [selectedTaskList, setSelectedTaskList] = useState("@default");
  const [taskLists, setTaskLists] = useState([]);
  const [error, setError] = useState(null);
  const [editingTask, setEditingTask] = useState(null);
  let [isOpen, setIsOpen] = useState(false)

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

  // Helper: build tree from flat array
  function buildTaskTree(tasks) {
    const taskMap = {};
    const roots = [];
    tasks.forEach(task => {
      task.children = [];
      taskMap[task.id] = task;
    });
    tasks.forEach(task => {
      if (task.parent && taskMap[task.parent]) {
        taskMap[task.parent].children.push(task);
      } else {
        roots.push(task);
      }
    });

    // Helper function to sort tasks
    function sortTasksInternal(taskList) {
      taskList.sort((a, b) => {
        // 1. Completed tasks go to the bottom
        if (a.status === 'completed' && b.status !== 'completed') return 1;
        if (a.status !== 'completed' && b.status === 'completed') return -1;

        // For non-completed tasks:
        if (a.status !== 'completed' && b.status !== 'completed') {
          // 2. Tasks with due dates come before tasks without
          if (a.due && !b.due) return -1;
          if (!a.due && b.due) return 1;

          // 3. If both have due dates, sort by earliest due date
          if (a.due && b.due) {
            const dateA = new Date(a.due);
            const dateB = new Date(b.due);
            if (dateA < dateB) return -1;
            if (dateA > dateB) return 1;
          }
        }

        // 4. Fallback: sort by title alphabetically
        if (a.title && b.title) {
          return a.title.localeCompare(b.title);
        }
        return 0;
      });
    }

    // Sort children of each task
    for (const taskId in taskMap) {
      if (taskMap[taskId].children.length > 0) {
        sortTasksInternal(taskMap[taskId].children);
      }
    }

    // Sort root tasks
    sortTasksInternal(roots);

    return roots;
  }

  // Helper: recursively render task & children
  function renderTaskNode(task, level = 0) {
    const indentClass = level > 0 ? `ml-${Math.min(level * 4, 12)}` : '';
    return (
      <div key={task.id} className={`p-4 bg-white dark:bg-zinc-800 rounded-lg shadow-sm hover:shadow-md transition-shadow ${task.status === "completed" ? "opacity-70" : ""} ${indentClass}`}>
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
                    className={`font-medium ${task.status === "completed" ? "line-through" : ""}`}
                  >
                    {task.title}
                  </Text>
                  {task.notes && (
                    <Text className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {task.notes}
                    </Text>
                  )}
                  {task.status !== "completed" && task.due && (
                    <div className="flex items-center mt-1">
                      <Calendar className="h-3 w-3 mr-1 text-gray-500" />
                      <Badge
                            color={
                              (() => {
                              const [year, month, day] = task.due.substring(0, 10).split('-').map(Number);
                              const dueDateObj = new Date(year, month - 1, day);
                              const today = new Date();
                              today.setHours(0, 0, 0, 0);
                              if (dueDateObj < today) return "red";
                              if (dueDateObj.getTime() === today.getTime()) return "yellow";
                              return "green";
                            })()
                            }
                          >
                            {(() => {
                              const [year, month, day] = task.due.substring(0, 10).split('-');
                              // Create the Date object once with Number-converted parts
                              const dateObj = new Date(Number(year), Number(month) - 1, Number(day));
                              return dateObj.toLocaleDateString(); // Uses browser's locale for formatting the specific date
                            })()}
                            {" · "}
                            {(() => {
                              const [year, month, day] = task.due.substring(0, 10).split('-').map(Number);
                              const dueDateObj = new Date(year, month - 1, day);
                              const today = new Date();
                              today.setHours(0, 0, 0, 0);
                              const msPerDay = 24 * 60 * 60 * 1000;
                              const diffDays = Math.round((dueDateObj.getTime() - today.getTime()) / msPerDay);
                              if (diffDays === 0) return "Due today";
                              if (diffDays > 0) return `Due in ${diffDays} day${diffDays === 1 ? "" : "s"}`;
                              return `${Math.abs(diffDays)} day${Math.abs(diffDays) === 1 ? "" : "s"} overdue`;
                            })()}
                          </Badge>
                    </div>
                  )}
                  {task.links && (
                    task.links.map((link) => (
                      <Badge key={link.link}>
                        <a href={link.link} target="_blank" rel="noopener noreferrer">
                          <Text className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                            {link.description}
                          </Text>
                        </a>
                      </Badge>
                    ))
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
        {/* Render children subtasks recursively */}
        {task.children && task.children.length > 0 && (
          <div className="mt-2">
            {task.children.map(child => renderTaskNode(child, level + 1))}
          </div>
        )}
      </div>
    );
  }

  function renderTaskTree(tasks) {
    const tree = buildTaskTree(tasks);
    return tree.map(task => renderTaskNode(task));
  }

  // Render block (original return)
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
        <Button outline type="button" className="flex gap-2 cursor-pointer" onClick={() => setIsOpen(true)}>
         <PlusCircleIcon className="h-4 w-4" /> Add Task
        </Button>
        <Button
          size="sm"
          variant="outline"
          onClick={fetchTasks}
          className="flex items-center gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
        <Dialog open={isOpen} onClose={setIsOpen}>
        <DialogTitle>Add Task</DialogTitle>
        <DialogDescription>
          Add a new task to your Google Tasks list.
        </DialogDescription>
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
            onClick={() => setIsOpen(false)}

          >
            <PlusCircle className="h-5 w-5" />
            Create Task
          </Button>
        </div>
      </form>
      </Dialog>
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

      

      <div className="space-y-2">
        {tasks.length === 0 ? (
          <div className="text-center p-6 bg-white dark:bg-zinc-800 rounded-lg">
            <Text>No tasks found. Create a new task above.</Text>
          </div>
        ) : (
          renderTaskTree(tasks)
        )}
      </div>
    </div>
  );
}

export default TasksPage;


function NewTaskDialog() {

  return (
    <>

      <Dialog open={isOpen} onClose={setIsOpen}>
        <DialogTitle>Add Task</DialogTitle>
        <DialogDescription>
          Add a new task to your Google Tasks list.
        </DialogDescription>
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
      </Dialog>
    </>
  )
}