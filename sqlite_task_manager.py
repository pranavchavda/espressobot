"""
SQLite-based Task Management System
Fast, local storage without embeddings for real-time task tracking.
"""

import sqlite3
import json
import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class SQLiteTaskManager:
    """
    Lightweight task management using SQLite for speed.
    No embeddings, no vector storage - just fast CRUD operations.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'tasks.db')
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS task_lists (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    template_name TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    task_list_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority TEXT DEFAULT 'medium',
                    order_index INTEGER DEFAULT 0,
                    parent_id TEXT,
                    subtasks TEXT,  -- JSON array of subtasks
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_list_id) REFERENCES task_lists (id)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_task_lists_user_id ON task_lists (user_id)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_tasks_task_list_id ON tasks (task_list_id)
            ''')
            
            conn.commit()
    
    async def create_task_list(self, user_id: int, title: str, tasks: List[Dict], template_name: str = None) -> Dict[str, Any]:
        """Create a new task list with tasks."""
        task_list_id = str(uuid.uuid4())
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Create task list
                conn.execute('''
                    INSERT INTO task_lists (id, user_id, title, template_name)
                    VALUES (?, ?, ?, ?)
                ''', (task_list_id, user_id, title, template_name))
                
                # Clear any existing active task lists for this user
                conn.execute('''
                    UPDATE task_lists 
                    SET status = 'completed' 
                    WHERE user_id = ? AND id != ? AND status = 'active'
                ''', (user_id, task_list_id))
                
                # Create tasks
                for i, task in enumerate(tasks):
                    task_id = str(uuid.uuid4())
                    content = task.get("content", "") if isinstance(task, dict) else str(task)
                    subtasks = json.dumps(task.get("subtasks", [])) if isinstance(task, dict) and "subtasks" in task else None
                    
                    conn.execute('''
                        INSERT INTO tasks (id, task_list_id, content, order_index, subtasks)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (task_id, task_list_id, content, i, subtasks))
                
                conn.commit()
                
                # Count tasks
                cursor = conn.execute('SELECT COUNT(*) FROM tasks WHERE task_list_id = ?', (task_list_id,))
                task_count = cursor.fetchone()[0]
                
                return {
                    "success": True,
                    "task_list_id": task_list_id,
                    "task_count": task_count,
                    "message": f"Created task list '{title}' with {task_count} tasks"
                }
                
        except Exception as e:
            logger.error(f"Error creating task list: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_current_task_list(self, user_id: int) -> Dict[str, Any]:
        """Get the current active task list for a user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                
                # Get active task list
                cursor = conn.execute('''
                    SELECT * FROM task_lists 
                    WHERE user_id = ? AND status = 'active'
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (user_id,))
                
                task_list_row = cursor.fetchone()
                if not task_list_row:
                    return {"success": True, "task_list": None}
                
                task_list = dict(task_list_row)
                
                # Get tasks for this list
                cursor = conn.execute('''
                    SELECT * FROM tasks 
                    WHERE task_list_id = ? 
                    ORDER BY order_index
                ''', (task_list["id"],))
                
                tasks = []
                for task_row in cursor.fetchall():
                    task = dict(task_row)
                    if task["subtasks"]:
                        task["subtasks"] = json.loads(task["subtasks"])
                    tasks.append(task)
                
                task_list["tasks"] = tasks
                
                return {
                    "success": True,
                    "task_list": task_list
                }
                
        except Exception as e:
            logger.error(f"Error getting current task list: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_task_status(self, user_id: int, task_id: str, status: str) -> Dict[str, Any]:
        """Update the status of a specific task."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    UPDATE tasks 
                    SET status = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND task_list_id IN (
                        SELECT id FROM task_lists WHERE user_id = ?
                    )
                ''', (status, task_id, user_id))
                
                if cursor.rowcount == 0:
                    return {"success": False, "error": "Task not found"}
                
                conn.commit()
                return {"success": True, "message": f"Task status updated to {status}"}
                
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            return {"success": False, "error": str(e)}
    
    async def add_task(self, user_id: int, content: str, priority: str = "medium", parent_id: str = None) -> Dict[str, Any]:
        """Add a new task to the current task list."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get current task list
                cursor = conn.execute('''
                    SELECT id FROM task_lists 
                    WHERE user_id = ? AND status = 'active'
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (user_id,))
                
                task_list_row = cursor.fetchone()
                if not task_list_row:
                    return {"success": False, "error": "No active task list found"}
                
                task_list_id = task_list_row[0]
                
                # Get next order index
                cursor = conn.execute('''
                    SELECT COALESCE(MAX(order_index), -1) + 1 
                    FROM tasks WHERE task_list_id = ?
                ''', (task_list_id,))
                order_index = cursor.fetchone()[0]
                
                # Create new task
                task_id = str(uuid.uuid4())
                conn.execute('''
                    INSERT INTO tasks (id, task_list_id, content, priority, order_index, parent_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (task_id, task_list_id, content, priority, order_index, parent_id))
                
                conn.commit()
                return {"success": True, "task_id": task_id, "message": "Task added successfully"}
                
        except Exception as e:
            logger.error(f"Error adding task: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_task_context_string(self, user_id: int) -> str:
        """Get formatted task context for injection into agent prompts."""
        try:
            result = await self.get_current_task_list(user_id)
            if not result.get("success") or not result.get("task_list"):
                return ""
            
            task_list = result["task_list"]
            tasks = task_list.get("tasks", [])
            
            if not tasks:
                return ""
            
            context = f"\n📋 CURRENT TASK LIST: {task_list['title']}\n"
            context += "Tasks (you MUST update status as you work):\n"
            
            for i, task in enumerate(tasks, 1):
                status_icon = {
                    "pending": "⏳",
                    "in_progress": "🔄", 
                    "completed": "✅"
                }.get(task["status"], "⏳")
                
                context += f"{i}. {status_icon} {task['content']} ({task['status']})\n"
                
                # Add subtasks if any
                if task.get("subtasks"):
                    for subtask in task["subtasks"]:
                        if isinstance(subtask, dict):
                            subtask_content = subtask.get("content", str(subtask))
                        else:
                            subtask_content = str(subtask)
                        context += f"   • {subtask_content}\n"
            
            context += "\nRemember: Call task_update_status() when starting/completing tasks!\n"
            return context
            
        except Exception as e:
            logger.error(f"Error getting task context: {e}")
            return ""

# Create singleton instance
sqlite_task_manager = SQLiteTaskManager()