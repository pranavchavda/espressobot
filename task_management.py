"""
Task Management System for EspressoBot
Modeled after Claude Code's proven task management approach.

This module provides task creation, tracking, and completion functionality
to help the agent stay organized and provide transparency to users.
"""

import json
import uuid
import logging
from typing import Dict, Any, List, Optional, Union
from memory_service import memory_service

logger = logging.getLogger(__name__)

# Task templates - starting with product listing creation
TASK_TEMPLATES = {
    "product_listing_creation": {
        "name": "Product Listing Creation: {product_name}",
        "tasks": [
            {
                "content": "Gather product information and verify details",
                "subtasks": [
                    "Search for accurate product specifications",
                    "Confirm brand name and proper product naming convention", 
                    "Verify pricing and availability",
                    "Identify product type (espresso machine, grinder, accessory, etc.)"
                ]
            },
            {
                "content": "Create Buy Box content (`buybox.content`)",
                "subtasks": [
                    "Write engaging J. Peterman-style sales pitch",
                    "Focus on customer experience and value proposition"
                ]
            },
            {
                "content": "Write comprehensive Overview (`body_html`)",
                "subtasks": [
                    "Conversational \"kitchen conversation\" tone",
                    "Highlight key features, design, and performance"
                ]
            },
            {
                "content": "Build Features section",
                "subtasks": [
                    "Create bolded subtitles with descriptions",
                    "Optional: Format as JSON for `content.featuresjson`"
                ]
            },
            {
                "content": "Develop FAQs (`faq.content`)",
                "subtasks": [
                    "Research 5-7 common customer questions",
                    "Write clear, professional answers",
                    "Format as JSON structure"
                ]
            },
            {
                "content": "Compile Tech Specs (`specs.techjson`)",
                "subtasks": [
                    "Include manufacturer, boiler type, size, power",
                    "Add other relevant specifications",
                    "Format as JSON"
                ]
            },
            {
                "content": "Set basic product details",
                "subtasks": [
                    "Configure title using naming convention",
                    "Set vendor/brand",
                    "Set product type",
                    "Set status to DRAFT"
                ]
            },
            {
                "content": "Create variant(s)",
                "subtasks": [
                    "Set price",
                    "Configure SKU", 
                    "Set cost (COGS) via inventory item",
                    "Enable inventory tracking (deny when out of stock)",
                    "Set inventory weight in grams"
                ]
            },
            {
                "content": "Add variant preview name (`ext.variantPreviewName`) if applicable"
            },
            {
                "content": "Upload and optimize product images",
                "subtasks": [
                    "Add primary product image with relevant alt text",
                    "Upload additional variant/detail images",
                    "Ensure proper image quality and sizing"
                ]
            },
            {
                "content": "Apply product type tags",
                "subtasks": [
                    "Add category-specific tags (espresso-machines, grinders, etc.)",
                    "Include warranty tags (WAR-SG, WAR-VIM, etc.)"
                ]
            },
            {
                "content": "Apply brand/vendor tags",
                "subtasks": [
                    "Add lowercase vendor name",
                    "Include VIM and WAR-VIM for qualifying brands"
                ]
            },
            {
                "content": "Add thematic/feature tags",
                "subtasks": [
                    "Include relevant NC_ collection tags",
                    "Add icon- feature tags (E61-Group-Head, PID, etc.)",
                    "Apply function-specific tags (dual-boiler, super-automatic, etc.)"
                ]
            },
            {
                "content": "Handle special cases if applicable",
                "subtasks": [
                    "Coffee products: Set vendor to \"Escarpment Coffee Roasters\", skip Buy Box/FAQs, add coffee tags, set seasonality",
                    "Accessories/consumables: Skip Buy Box, FAQs, Tech Specs, Features - focus on detailed overview"
                ]
            },
            {
                "content": "Review and finalize",
                "subtasks": [
                    "Verify all required fields are populated",
                    "Double-check pricing and SKU accuracy",
                    "Confirm proper tagging for filtering/search",
                    "Review content for Canadian English spelling",
                    "Ensure DRAFT status before completion"
                ]
            }
        ]
    }
}

class TaskManager:
    """
    Task management system that provides task creation, tracking, and completion.
    Modeled after Claude Code's task management approach.
    """
    
    def __init__(self):
        self.memory_key_prefix = "tasks"
    
    async def create_task_list(self, user_id: int, title: str, tasks: List[Dict], template_name: str = None) -> Dict[str, Any]:
        """
        Create a new task list for a user.
        
        Args:
            user_id: User ID
            title: Title/name for the task list
            tasks: List of task dictionaries with content and optional subtasks
            template_name: Optional template name used to create this task list
            
        Returns:
            Dict with task list ID and creation status
        """
        task_list_id = str(uuid.uuid4())
        
        # Convert task structure to our format
        formatted_tasks = []
        task_counter = 1
        
        for task_item in tasks:
            task_id = str(task_counter)
            formatted_task = {
                "id": task_id,
                "content": task_item["content"],
                "status": "pending",
                "priority": "medium"
            }
            formatted_tasks.append(formatted_task)
            task_counter += 1
            
            # Handle subtasks
            if "subtasks" in task_item and task_item["subtasks"]:
                for subtask_content in task_item["subtasks"]:
                    subtask_id = f"{task_id}.{task_counter}"
                    formatted_subtask = {
                        "id": subtask_id,
                        "content": f"  - {subtask_content}",  # Indent to show nesting
                        "status": "pending", 
                        "priority": "low",
                        "parent_id": task_id
                    }
                    formatted_tasks.append(formatted_subtask)
                    task_counter += 1
        
        task_list = {
            "id": task_list_id,
            "title": title,
            "template_name": template_name,
            "tasks": formatted_tasks,
            "created_at": str(datetime.now()),
            "status": "active"
        }
        
        # Store in memory
        memory_key = f"{self.memory_key_prefix}:{task_list_id}"
        result = await memory_service.store_memory(user_id, memory_key, task_list)
        
        # Also store current active task list reference
        await memory_service.store_memory(user_id, f"{self.memory_key_prefix}:current", task_list_id)
        
        logger.info(f"Created task list '{title}' for user {user_id} with {len(formatted_tasks)} tasks")
        
        return {
            "success": True,
            "task_list_id": task_list_id,
            "task_count": len(formatted_tasks),
            "message": f"Created task list '{title}' with {len(formatted_tasks)} tasks"
        }
    
    async def create_from_template(self, user_id: int, template_name: str, **kwargs) -> Dict[str, Any]:
        """
        Create a task list from a predefined template.
        
        Args:
            user_id: User ID
            template_name: Name of the template to use
            **kwargs: Template variables (e.g., product_name)
            
        Returns:
            Dict with task list creation status
        """
        if template_name not in TASK_TEMPLATES:
            return {
                "success": False,
                "error": f"Template '{template_name}' not found. Available templates: {list(TASK_TEMPLATES.keys())}"
            }
        
        template = TASK_TEMPLATES[template_name]
        
        # Format template name with variables
        title = template["name"].format(**kwargs)
        
        return await self.create_task_list(
            user_id=user_id,
            title=title,
            tasks=template["tasks"],
            template_name=template_name
        )
    
    async def get_current_task_list(self, user_id: int) -> Dict[str, Any]:
        """
        Get the current active task list for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with current task list or None if no active tasks
        """
        # Get current task list ID
        current_result = await memory_service.retrieve_memory(user_id, f"{self.memory_key_prefix}:current")
        
        if not current_result["success"]:
            return {"success": True, "task_list": None, "message": "No active task list"}
        
        task_list_id = current_result["value"]
        
        # Get the actual task list
        task_list_result = await memory_service.retrieve_memory(user_id, f"{self.memory_key_prefix}:{task_list_id}")
        
        if not task_list_result["success"]:
            return {"success": False, "error": "Failed to retrieve current task list"}
        
        return {
            "success": True,
            "task_list": task_list_result["value"]
        }
    
    async def update_task_status(self, user_id: int, task_id: str, status: str) -> Dict[str, Any]:
        """
        Update the status of a specific task.
        
        Args:
            user_id: User ID
            task_id: Task ID to update
            status: New status (pending, in_progress, completed)
            
        Returns:
            Dict with update status
        """
        current_result = await self.get_current_task_list(user_id)
        
        if not current_result["success"] or not current_result["task_list"]:
            return {"success": False, "error": "No active task list found"}
        
        task_list = current_result["task_list"]
        
        # Find and update the task
        task_found = False
        for task in task_list["tasks"]:
            if task["id"] == task_id:
                task["status"] = status
                task_found = True
                break
        
        if not task_found:
            return {"success": False, "error": f"Task {task_id} not found"}
        
        # Save updated task list
        memory_key = f"{self.memory_key_prefix}:{task_list['id']}"
        result = await memory_service.store_memory(user_id, memory_key, task_list)
        
        return {
            "success": True,
            "message": f"Task {task_id} status updated to {status}"
        }
    
    async def add_task(self, user_id: int, content: str, priority: str = "medium", parent_id: str = None) -> Dict[str, Any]:
        """
        Add a new task to the current task list.
        
        Args:
            user_id: User ID
            content: Task content/description
            priority: Task priority (low, medium, high)
            parent_id: Optional parent task ID for subtasks
            
        Returns:
            Dict with addition status
        """
        current_result = await self.get_current_task_list(user_id)
        
        if not current_result["success"] or not current_result["task_list"]:
            return {"success": False, "error": "No active task list found"}
        
        task_list = current_result["task_list"]
        
        # Generate new task ID
        existing_ids = [int(t["id"].split(".")[0]) for t in task_list["tasks"] if "." not in t["id"]]
        new_id = str(max(existing_ids) + 1) if existing_ids else "1"
        
        if parent_id:
            # This is a subtask
            new_id = f"{parent_id}.{len([t for t in task_list['tasks'] if t.get('parent_id') == parent_id]) + 1}"
            content = f"  - {content}"  # Indent for nesting
        
        new_task = {
            "id": new_id,
            "content": content,
            "status": "pending",
            "priority": priority
        }
        
        if parent_id:
            new_task["parent_id"] = parent_id
        
        task_list["tasks"].append(new_task)
        
        # Save updated task list
        memory_key = f"{self.memory_key_prefix}:{task_list['id']}"
        result = await memory_service.store_memory(user_id, memory_key, task_list)
        
        return {
            "success": True,
            "task_id": new_id,
            "message": f"Added new task: {content}"
        }
    
    async def get_task_context_string(self, user_id: int) -> str:
        """
        Generate a context string showing current tasks for injection into agent prompts.
        
        Args:
            user_id: User ID
            
        Returns:
            Formatted string of current tasks or empty string if no tasks
        """
        current_result = await self.get_current_task_list(user_id)
        
        if not current_result["success"] or not current_result["task_list"]:
            return ""
        
        task_list = current_result["task_list"]
        
        context_lines = [f"## Current Task List: {task_list['title']}\n"]
        
        for task in task_list["tasks"]:
            status_marker = "✅" if task["status"] == "completed" else "🔄" if task["status"] == "in_progress" else "⭕"
            priority_marker = "🔴" if task["priority"] == "high" else "🟡" if task["priority"] == "medium" else "🔵"
            
            context_lines.append(f"{status_marker} {priority_marker} [{task['id']}] {task['content']}")
        
        context_lines.append("\n**Instructions**: Always refer to this task list. Update task status as you work. Add new tasks/subtasks as needed.")
        
        return "\n".join(context_lines)


# Create singleton instance
task_manager = TaskManager()

# Add missing datetime import
from datetime import datetime