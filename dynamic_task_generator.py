"""
Dynamic Task Generation Agent
Uses gpt-4.1-mini to intelligently create contextual task lists for any user request.
"""

import openai
import json
import os
from typing import List, Dict, Any

async def generate_dynamic_tasks(user_message: str, user_context: str = "") -> Dict[str, Any]:
    """
    Use gpt-4.1-mini to generate a dynamic, contextual task list for the user's request.
    
    Args:
        user_message: The user's request/question
        user_context: Additional context about the user or conversation
    
    Returns:
        Dict with success status and generated tasks
    """
    
    # Create the task generation prompt
    system_prompt = """You are a task planning specialist for an e-commerce/Shopify assistant. 

Your job is to analyze user requests and create appropriate task lists that break down complex work into manageable steps.

RULES:
1. Create 2-6 tasks (not too many, not too few)
2. Tasks should be specific and actionable
3. Each task should represent a meaningful step toward completing the user's request
4. Tasks should be in logical order
5. Focus on what the AI agent needs to DO, not just think about

RESPONSE FORMAT - Return ONLY valid JSON:
{
  "title": "Brief title for the task list",
  "tasks": [
    {
      "content": "Specific action the agent should take",
      "subtasks": ["Optional subtask 1", "Optional subtask 2"]
    }
  ],
  "complexity": "simple|moderate|complex"
}

EXAMPLES:

User: "Create a new product listing for a coffee grinder"
Response: {
  "title": "Create Coffee Grinder Product Listing",
  "tasks": [
    {
      "content": "Research coffee grinder specifications and features",
      "subtasks": ["Find product details", "Identify key selling points", "Check competitor listings"]
    },
    {
      "content": "Write compelling product title and description",
      "subtasks": ["Create SEO-optimized title", "Write detailed description", "Include technical specifications"]
    },
    {
      "content": "Set up product pricing and inventory",
      "subtasks": ["Determine competitive pricing", "Set inventory levels", "Configure SKU"]
    },
    {
      "content": "Add product images and finalize listing",
      "subtasks": ["Upload product images", "Set product tags", "Review and publish"]
    }
  ],
  "complexity": "moderate"
}

User: "Help me duplicate this product but change the color to red"
Response: {
  "title": "Duplicate Product with Color Variant",
  "tasks": [
    {
      "content": "Locate and analyze the source product",
      "subtasks": ["Find the product to duplicate", "Review current specifications"]
    },
    {
      "content": "Create duplicate with red color variant",
      "subtasks": ["Use product duplication API", "Update color specification", "Modify title/description"]
    },
    {
      "content": "Update images and verify details",
      "subtasks": ["Replace with red product images", "Verify all details are correct", "Set as draft for review"]
    }
  ],
  "complexity": "simple"
}

User: "What's the best coffee machine for offices?"
Response: {
  "title": "Research Office Coffee Machine Options", 
  "tasks": [
    {
      "content": "Research office coffee machine requirements",
      "subtasks": ["Identify office size considerations", "Determine capacity needs", "Review maintenance requirements"]
    },
    {
      "content": "Compare available coffee machine models",
      "subtasks": ["Search product catalog", "Compare features and prices", "Check customer reviews"]
    },
    {
      "content": "Provide recommendation with reasoning",
      "subtasks": ["Analyze pros/cons of top options", "Consider budget factors", "Present clear recommendation"]
    }
  ],
  "complexity": "simple"
}

User: "demo the internal task system with some arbitrary multi-step task"
Response: {
  "title": "Demo Internal Task System",
  "tasks": [
    {
      "content": "Explain the task system capabilities",
      "subtasks": ["Describe auto task creation", "Show task progress tracking", "Explain interrupt functionality"]
    },
    {
      "content": "Create a sample multi-step workflow",
      "subtasks": ["Choose an example task", "Break it into logical steps", "Show task status updates"]
    },
    {
      "content": "Demonstrate task management features",
      "subtasks": ["Update task status in real-time", "Show progress to user", "Complete demo workflow"]
    }
  ],
  "complexity": "simple"
}

Now analyze this user request and create an appropriate task list:"""

    user_prompt = f"""User Request: "{user_message}"

{f"Context: {user_context}" if user_context else ""}

Generate a focused task list that breaks down this request into logical steps for an AI assistant to follow."""

    try:
        # Use gpt-4.1-mini for fast, cost-effective task generation
        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Low temperature for consistent, logical task generation
            max_tokens=1000
        )
        
        # Parse the JSON response
        task_data = json.loads(response.choices[0].message.content.strip())
        
        # Validate the response structure
        if not isinstance(task_data, dict) or "tasks" not in task_data:
            raise ValueError("Invalid task structure returned")
        
        # Convert to the format expected by our task manager
        formatted_tasks = []
        for task in task_data["tasks"]:
            if isinstance(task, dict):
                formatted_tasks.append(task)
            else:
                formatted_tasks.append({"content": str(task)})
        
        return {
            "success": True,
            "title": task_data.get("title", "Generated Task List"),
            "tasks": formatted_tasks,
            "complexity": task_data.get("complexity", "moderate"),
            "task_count": len(formatted_tasks)
        }
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse task generation response as JSON: {e}")
        return {"success": False, "error": "Failed to parse task generation response"}
    
    except Exception as e:
        print(f"Error generating dynamic tasks: {e}")
        return {"success": False, "error": str(e)}

def should_create_tasks(user_message: str) -> bool:
    """
    Improved logic to determine if a user message requires task creation.
    More conservative than before - focuses on actual work requests.
    """
    message_lower = user_message.lower().strip()
    
    print(f"DEBUG: Checking task requirement for: '{message_lower}'")
    
    # Skip very short messages (likely simple questions)
    if len(message_lower.split()) < 4:
        print(f"DEBUG: Message too short ({len(message_lower.split())} words)")
        return False
    
    # Skip obvious simple questions
    simple_question_patterns = [
        "what is", "what's", "how much", "when", "where", "who",
        "which", "why", "how many", "is there", "are there",
        "do you", "can i", "should i"
    ]
    
    if any(pattern in message_lower[:20] for pattern in simple_question_patterns):
        print(f"DEBUG: Detected simple question pattern")
        return False
    
    # Require tasks for action-oriented requests
    action_indicators = [
        "create", "make", "add", "build", "set up", "setup", "generate",
        "help me", "i need", "can you", "please", "duplicate", "copy",
        "update", "modify", "change", "fix", "configure", "install",
        "demo", "test", "show"  # Added for demo requests
    ]
    
    # Complex work indicators
    complex_work = [
        "product", "listing", "inventory", "shopify", "store", "catalog",
        "description", "pricing", "image", "variant", "collection",
        "task", "multi-step", "workflow", "system"  # Added task-related terms
    ]
    
    # Multi-step indicators
    multi_step = [
        "and", "then", "also", "after", "before", "first", "next",
        "step by step", "process", "workflow", "multi-step", "several"
    ]
    
    has_action = any(indicator in message_lower for indicator in action_indicators)
    has_complex_work = any(work in message_lower for work in complex_work)
    has_multi_step = any(step in message_lower for step in multi_step)
    
    print(f"DEBUG: has_action={has_action}, has_complex_work={has_complex_work}, has_multi_step={has_multi_step}")
    print(f"DEBUG: word_count={len(message_lower.split())}")
    
    # Require at least action + (complex work OR multi-step) OR long message with action
    result = has_action and (has_complex_work or has_multi_step or len(message_lower.split()) > 10)
    print(f"DEBUG: Task creation needed: {result}")
    
    # TEMPORARY: Force task creation for testing
    if "demo" in message_lower or "test" in message_lower or "task" in message_lower:
        print("DEBUG: FORCING task creation for demo/test request")
        return True
    
    return result