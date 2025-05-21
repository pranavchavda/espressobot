
import os
import json
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from flask import url_for, request, redirect, session
from flask_login import current_user

# Google Tasks API scopes
SCOPES = [
    'https://www.googleapis.com/auth/tasks',
    'https://www.googleapis.com/auth/userinfo.email'
]

def get_credentials_path(user_id):
    """Get the path to store user's Google credentials"""
    credentials_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'storage', 'credentials')
    os.makedirs(credentials_dir, exist_ok=True)
    return os.path.join(credentials_dir, f'google_tasks_credentials_{user_id}.json')

def get_flow():
    """Create OAuth flow object for Google Tasks API"""
    client_config = {
        "web": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID"),
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [url_for('google_auth_callback', _external=True)]
        }
    }
    
    # Get the Replit domain from environment if available
    replit_domain = os.environ.get('REPLIT_SLUG')
    
    # If running on Replit, use the Replit domain for the redirect URI
    if replit_domain:
        redirect_uri = f"https://{replit_domain}.replit.app/api/google/callback"
    else:
        # For local development, use the Flask URL
        redirect_uri = url_for('google_auth_callback', _external=True)
        if not redirect_uri.startswith('https://') and not redirect_uri.startswith('http://localhost'):
            redirect_uri = redirect_uri.replace('http://', 'https://')
    
    print(f"Using redirect URI: {redirect_uri}")
    
    return Flow.from_client_config(
        client_config, 
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )

def get_credentials(user_id):
    """Get stored credentials for the user or return None"""
    creds_path = get_credentials_path(user_id)
    if not os.path.exists(creds_path):
        return None
        
    with open(creds_path, 'r') as f:
        creds_data = json.load(f)
        creds = Credentials.from_authorized_user_info(creds_data)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh the token
            creds.refresh(Request())
            # Save refreshed credentials
            with open(creds_path, 'w') as f:
                f.write(creds.to_json())
        else:
            return None
    
    return creds

def save_credentials(user_id, credentials):
    """Save credentials to a file"""
    creds_path = get_credentials_path(user_id)
    with open(creds_path, 'w') as f:
        f.write(credentials.to_json())

def is_authorized(user_id):
    """Check if the user has authorized Google Tasks"""
    return get_credentials(user_id) is not None

def get_service(user_id):
    """Get a Google Tasks service object for the user"""
    creds = get_credentials(user_id)
    if not creds:
        return None
    return build('tasks', 'v1', credentials=creds)

def get_task_lists(user_id):
    """Get all task lists for the user"""
    service = get_service(user_id)
    if not service:
        return {"error": "Not authorized"}
        
    try:
        results = service.tasklists().list().execute()
        return results.get('items', [])
    except Exception as e:
        return {"error": str(e)}

def get_tasks(user_id, tasklist_id='@default'):
    """Get all tasks in a task list"""
    service = get_service(user_id)
    if not service:
        return {"error": "Not authorized"}
        
    try:
        results = service.tasks().list(tasklist=tasklist_id).execute()
        return results.get('items', [])
    except Exception as e:
        return {"error": str(e)}

def create_task(user_id, title, notes=None, due=None, tasklist_id='@default'):
    """Create a new task"""
    service = get_service(user_id)
    if not service:
        return {"error": "Not authorized"}
        
    task = {
        'title': title,
    }
    
    if notes:
        task['notes'] = notes
        
    if due:
        # Format date as RFC 3339 timestamp
        if isinstance(due, str):
            # Try to parse the string as a date
            try:
                due_date = datetime.datetime.strptime(due, "%Y-%m-%d")
                due = due_date.isoformat() + 'Z'  # 'Z' indicates UTC time
            except ValueError:
                # If parsing fails, use the string as is
                pass
        elif isinstance(due, datetime.datetime):
            due = due.isoformat() + 'Z'
            
        task['due'] = due
    
    try:
        result = service.tasks().insert(tasklist=tasklist_id, body=task).execute()
        return result
    except Exception as e:
        return {"error": str(e)}

def update_task(user_id, task_id, title=None, notes=None, due=None, status=None, tasklist_id='@default'):
    """Update an existing task"""
    service = get_service(user_id)
    if not service:
        return {"error": "Not authorized"}
        
    # First get the existing task to update only provided fields
    try:
        task = service.tasks().get(tasklist=tasklist_id, task=task_id).execute()
    except Exception as e:
        return {"error": f"Task not found: {str(e)}"}
    
    if title:
        task['title'] = title
    if notes:
        task['notes'] = notes
    if status in ['needsAction', 'completed']:
        task['status'] = status
        
    if due:
        # Format date as RFC 3339 timestamp
        if isinstance(due, str):
            # Try to parse the string as a date
            try:
                due_date = datetime.datetime.strptime(due, "%Y-%m-%d")
                due = due_date.isoformat() + 'Z'  # 'Z' indicates UTC time
            except ValueError:
                # If parsing fails, use the string as is
                pass
        elif isinstance(due, datetime.datetime):
            due = due.isoformat() + 'Z'
            
        task['due'] = due
    
    try:
        result = service.tasks().update(tasklist=tasklist_id, task=task_id, body=task).execute()
        return result
    except Exception as e:
        return {"error": str(e)}

def delete_task(user_id, task_id, tasklist_id='@default'):
    """Delete a task"""
    service = get_service(user_id)
    if not service:
        return {"error": "Not authorized"}
        
    try:
        service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}

def complete_task(user_id, task_id, tasklist_id='@default'):
    """Mark a task as completed"""
    return update_task(user_id, task_id, status='completed', tasklist_id=tasklist_id)
