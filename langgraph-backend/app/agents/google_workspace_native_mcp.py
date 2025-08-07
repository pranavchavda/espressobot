"""
Google Workspace Agent using direct Google API integration with stored OAuth tokens
Handles Gmail, Calendar, Drive, and Tasks operations
"""
from typing import List, Dict, Any, Optional, Union
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field
import logging
import os
import asyncio
from datetime import datetime, timedelta
import json
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Google API imports
try:
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google.auth.exceptions import RefreshError
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    # Define placeholder if imports fail
    Credentials = None

import asyncpg
import aiosqlite

logger = logging.getLogger(__name__)


async def get_user_google_credentials(user_id: int) -> Optional['Credentials']:
    """Get Google credentials for the user from database using direct queries"""
    if not GOOGLE_AVAILABLE:
        logger.warning("Google API libraries not available")
        return None
    
    try:
        # Get database URL and connect appropriately
        database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./espressobot.db")
        
        if database_url.startswith("sqlite"):
            # SQLite using aiosqlite
            db_path = database_url.replace("sqlite+aiosqlite:///", "")
            async with aiosqlite.connect(db_path) as conn:
                cursor = await conn.execute(
                    "SELECT google_access_token, google_refresh_token, google_token_expiry FROM users WHERE id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                if not row or not row[0]:
                    return None
                
                credentials = Credentials(
                    token=row[0],
                    refresh_token=row[1],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=os.getenv("GOOGLE_CLIENT_ID"),
                    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                    scopes=[
                        'https://www.googleapis.com/auth/gmail.readonly',
                        'https://www.googleapis.com/auth/gmail.send',
                        'https://www.googleapis.com/auth/calendar',
                        'https://www.googleapis.com/auth/drive.readonly',
                        'https://www.googleapis.com/auth/tasks'
                    ]
                )
                
                if row[2]:
                    credentials.expiry = datetime.fromisoformat(row[2]) if isinstance(row[2], str) else row[2]
                
                # Refresh if expired
                if credentials.expired and credentials.refresh_token:
                    try:
                        credentials.refresh(Request())
                        # Update database with new token (no updated_at)
                        await conn.execute(
                            "UPDATE users SET google_access_token = ?, google_token_expiry = ? WHERE id = ?",
                            (credentials.token, credentials.expiry.isoformat() if credentials.expiry else None, user_id)
                        )
                        await conn.commit()
                    except RefreshError as e:
                        logger.error(f"Token refresh failed for user {user_id}: {e}")
                        return None
                
                return credentials
        
        else:
            # PostgreSQL using asyncpg
            if database_url.startswith("postgresql+asyncpg://"):
                database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
            
            conn = await asyncpg.connect(database_url)
            try:
                row = await conn.fetchrow(
                    "SELECT google_access_token, google_refresh_token, google_token_expiry FROM users WHERE id = $1",
                    user_id
                )
                if not row or not row[0]:
                    return None
                
                credentials = Credentials(
                    token=row[0],
                    refresh_token=row[1],
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=os.getenv("GOOGLE_CLIENT_ID"),
                    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                    scopes=[
                        'https://www.googleapis.com/auth/gmail.readonly',
                        'https://www.googleapis.com/auth/gmail.send',
                        'https://www.googleapis.com/auth/calendar',
                        'https://www.googleapis.com/auth/drive.readonly',
                        'https://www.googleapis.com/auth/tasks'
                    ]
                )
                
                if row[2]:
                    credentials.expiry = row[2]
                
                # Refresh if expired
                if credentials.expired and credentials.refresh_token:
                    try:
                        credentials.refresh(Request())
                        # Update database with new token (no updated_at)
                        await conn.execute(
                            "UPDATE users SET google_access_token = $1, google_token_expiry = $2 WHERE id = $3",
                            credentials.token, credentials.expiry, user_id
                        )
                    except RefreshError as e:
                        logger.error(f"Token refresh failed for user {user_id}: {e}")
                        return None
                
                return credentials
            finally:
                await conn.close()
                
    except Exception as e:
        logger.error(f"Failed to get Google credentials for user {user_id}: {e}")
        return None

class GoogleWorkspaceError(Exception):
    """Custom exception for Google Workspace operations"""
    pass


class GmailSearchTool(BaseTool):
    """Tool for searching Gmail messages"""
    name: str = "gmail_search"
    description: str = "Search Gmail messages using Gmail query syntax. Returns message summaries with IDs for further processing."
    user_id: int
    
    class ArgsSchema(BaseModel):
        query: str = Field(description="Gmail search query (e.g., 'from:example@gmail.com subject:invoice', 'newer_than:7d', 'has:attachment')")
        max_results: int = Field(default=10, description="Maximum number of results to return")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Run the tool synchronously - not supported for async operations"""
        raise NotImplementedError("Use async version")
    
    async def _arun(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """Search Gmail messages"""
        try:
            service = await self._get_gmail_service()
            if not service:
                return {"error": "Gmail service not available"}
            
            # Search for messages
            results = service.users().messages().list(
                userId='me', 
                q=query, 
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            # Get basic info for each message
            message_summaries = []
            for msg in messages:
                msg_detail = service.users().messages().get(
                    userId='me', 
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                headers = {h['name']: h['value'] for h in msg_detail['payload'].get('headers', [])}
                
                message_summaries.append({
                    'id': msg['id'],
                    'subject': headers.get('Subject', ''),
                    'from': headers.get('From', ''),
                    'date': headers.get('Date', ''),
                    'snippet': msg_detail.get('snippet', '')
                })
            
            return {
                'success': True,
                'messages': message_summaries,
                'total_found': len(message_summaries),
                'query_used': query
            }
            
        except Exception as e:
            logger.error(f"Gmail search error: {e}")
            return {'error': f"Gmail search failed: {str(e)}"}
    
    async def _get_gmail_service(self):
        """Get authenticated Gmail service"""
        creds = await self._get_google_credentials()
        if not creds:
            return None
        return build('gmail', 'v1', credentials=creds)
    
    async def _get_google_credentials(self) -> Optional['Credentials']:
        """Get Google credentials for the user from database"""
        return await get_user_google_credentials(self.user_id)


class GmailGetMessageTool(BaseTool):
    """Tool for getting full Gmail message content"""
    name: str = "gmail_get_message"
    description: str = "Get full email content by message ID. Use this after gmail_search to get complete email text."
    user_id: int
    
    class ArgsSchema(BaseModel):
        message_id: str = Field(description="Gmail message ID from search results")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, message_id: str) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, message_id: str) -> Dict[str, Any]:
        """Get full message content"""
        try:
            service = await self._get_gmail_service()
            if not service:
                return {"error": "Gmail service not available"}
            
            message = service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
            
            # Extract body
            body_text = ""
            html_body = ""
            
            def extract_body(payload):
                nonlocal body_text, html_body
                
                if 'parts' in payload:
                    for part in payload['parts']:
                        extract_body(part)
                elif payload.get('body', {}).get('data'):
                    data = payload['body']['data']
                    content = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    
                    if payload.get('mimeType') == 'text/plain':
                        body_text = content
                    elif payload.get('mimeType') == 'text/html':
                        html_body = content
            
            extract_body(message['payload'])
            
            return {
                'success': True,
                'id': message_id,
                'subject': headers.get('Subject', ''),
                'from': headers.get('From', ''),
                'to': headers.get('To', ''),
                'date': headers.get('Date', ''),
                'body': body_text or html_body,
                'html_body': html_body,
                'snippet': message.get('snippet', ''),
                'thread_id': message.get('threadId', ''),
                'labels': message.get('labelIds', [])
            }
            
        except Exception as e:
            logger.error(f"Gmail get message error: {e}")
            return {'error': f"Failed to get message: {str(e)}"}
    
    async def _get_gmail_service(self):
        """Get authenticated Gmail service"""
        creds = await self._get_google_credentials()
        if not creds:
            return None
        return build('gmail', 'v1', credentials=creds)
    
    async def _get_google_credentials(self) -> Optional['Credentials']:
        """Get Google credentials for the user from database"""
        return await get_user_google_credentials(self.user_id)


class GmailSendTool(BaseTool):
    """Tool for sending Gmail messages"""
    name: str = "gmail_send"
    description: str = "Send an email via Gmail. Use this to send responses or new emails."
    user_id: int
    
    class ArgsSchema(BaseModel):
        to: str = Field(description="Recipient email address")
        subject: str = Field(description="Email subject")
        body: str = Field(description="Email body content (plain text or HTML)")
        cc: Optional[str] = Field(default=None, description="CC recipients (comma-separated)")
        bcc: Optional[str] = Field(default=None, description="BCC recipients (comma-separated)")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, to: str, subject: str, body: str, cc: Optional[str] = None, bcc: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, to: str, subject: str, body: str, cc: Optional[str] = None, bcc: Optional[str] = None) -> Dict[str, Any]:
        """Send email"""
        try:
            service = await self._get_gmail_service()
            if not service:
                return {"error": "Gmail service not available"}
            
            # Create message
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send message
            result = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {
                'success': True,
                'message_id': result['id'],
                'thread_id': result.get('threadId', ''),
                'sent_to': to,
                'subject': subject
            }
            
        except Exception as e:
            logger.error(f"Gmail send error: {e}")
            return {'error': f"Failed to send email: {str(e)}"}
    
    async def _get_gmail_service(self):
        """Get authenticated Gmail service"""
        creds = await self._get_google_credentials()
        if not creds:
            return None
        return build('gmail', 'v1', credentials=creds)
    
    async def _get_google_credentials(self) -> Optional['Credentials']:
        """Get Google credentials for the user from database"""
        return await get_user_google_credentials(self.user_id)


class CalendarListEventsTool(BaseTool):
    """Tool for listing calendar events"""
    name: str = "calendar_list_events"
    description: str = "List upcoming calendar events. Use this to check schedules and availability."
    user_id: int
    
    class ArgsSchema(BaseModel):
        time_min: Optional[str] = Field(default=None, description="Start time (ISO format, defaults to now)")
        time_max: Optional[str] = Field(default=None, description="End time (ISO format)")
        max_results: int = Field(default=10, description="Maximum number of events")
        calendar_id: str = Field(default="primary", description="Calendar ID (default: primary)")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, time_min: Optional[str] = None, time_max: Optional[str] = None, 
            max_results: int = 10, calendar_id: str = "primary") -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, time_min: Optional[str] = None, time_max: Optional[str] = None, 
                   max_results: int = 10, calendar_id: str = "primary") -> Dict[str, Any]:
        """List calendar events"""
        try:
            service = await self._get_calendar_service()
            if not service:
                return {"error": "Calendar service not available"}
            
            # Default to current time if no time_min specified
            if not time_min:
                time_min = datetime.utcnow().isoformat() + 'Z'
            
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            event_list = []
            for event in events:
                event_data = {
                    'id': event['id'],
                    'summary': event.get('summary', ''),
                    'description': event.get('description', ''),
                    'start': event.get('start', {}).get('dateTime', event.get('start', {}).get('date', '')),
                    'end': event.get('end', {}).get('dateTime', event.get('end', {}).get('date', '')),
                    'location': event.get('location', ''),
                    'attendees': [{'email': a.get('email', ''), 'responseStatus': a.get('responseStatus', '')} 
                                for a in event.get('attendees', [])]
                }
                event_list.append(event_data)
            
            return {
                'success': True,
                'events': event_list,
                'total_found': len(event_list),
                'calendar_id': calendar_id
            }
            
        except Exception as e:
            logger.error(f"Calendar list events error: {e}")
            return {'error': f"Failed to list events: {str(e)}"}
    
    async def _get_calendar_service(self):
        """Get authenticated Calendar service"""
        creds = await self._get_google_credentials()
        if not creds:
            return None
        return build('calendar', 'v3', credentials=creds)
    
    async def _get_google_credentials(self) -> Optional['Credentials']:
        """Get Google credentials for the user from database"""
        return await get_user_google_credentials(self.user_id)


class CalendarCreateEventTool(BaseTool):
    """Tool for creating calendar events"""
    name: str = "calendar_create_event"
    description: str = "Create a new calendar event. Use this to schedule meetings and appointments."
    user_id: int
    
    class ArgsSchema(BaseModel):
        summary: str = Field(description="Event title/summary")
        description: Optional[str] = Field(default=None, description="Event description")
        start_time: str = Field(description="Start time (ISO format)")
        end_time: str = Field(description="End time (ISO format)")
        location: Optional[str] = Field(default=None, description="Event location")
        attendees: Optional[List[str]] = Field(default=None, description="List of attendee email addresses")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, summary: str, start_time: str, end_time: str, description: Optional[str] = None,
            location: Optional[str] = None, attendees: Optional[List[str]] = None) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, summary: str, start_time: str, end_time: str, description: Optional[str] = None,
                   location: Optional[str] = None, attendees: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create calendar event"""
        try:
            service = await self._get_calendar_service()
            if not service:
                return {"error": "Calendar service not available"}
            
            event = {
                'summary': summary,
                'start': {'dateTime': start_time},
                'end': {'dateTime': end_time},
            }
            
            if description:
                event['description'] = description
            if location:
                event['location'] = location
            if attendees:
                event['attendees'] = [{'email': email} for email in attendees]
            
            created_event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            return {
                'success': True,
                'event_id': created_event['id'],
                'html_link': created_event.get('htmlLink', ''),
                'summary': summary,
                'start_time': start_time,
                'end_time': end_time
            }
            
        except Exception as e:
            logger.error(f"Calendar create event error: {e}")
            return {'error': f"Failed to create event: {str(e)}"}
    
    async def _get_calendar_service(self):
        """Get authenticated Calendar service"""
        creds = await self._get_google_credentials()
        if not creds:
            return None
        return build('calendar', 'v3', credentials=creds)
    
    async def _get_google_credentials(self) -> Optional['Credentials']:
        """Get Google credentials for the user from database"""
        return await get_user_google_credentials(self.user_id)


class DriveSearchTool(BaseTool):
    """Tool for searching Google Drive files"""
    name: str = "drive_search"
    description: str = "Search Google Drive files by name and other criteria. Use this to find documents, spreadsheets, and other files."
    user_id: int
    
    class ArgsSchema(BaseModel):
        query: str = Field(description="Search query for file names")
        mime_type: Optional[str] = Field(default=None, description="Filter by MIME type (e.g., 'application/vnd.google-apps.document')")
        max_results: int = Field(default=10, description="Maximum results")
        folder_id: Optional[str] = Field(default=None, description="Search within specific folder ID")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, query: str, mime_type: Optional[str] = None, max_results: int = 10, 
            folder_id: Optional[str] = None) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, query: str, mime_type: Optional[str] = None, max_results: int = 10, 
                   folder_id: Optional[str] = None) -> Dict[str, Any]:
        """Search Drive files"""
        try:
            service = await self._get_drive_service()
            if not service:
                return {"error": "Drive service not available"}
            
            # Build search query
            search_query = f"name contains '{query}'"
            if mime_type:
                search_query += f" and mimeType='{mime_type}'"
            if folder_id:
                search_query += f" and '{folder_id}' in parents"
            
            results = service.files().list(
                q=search_query,
                pageSize=max_results,
                fields='files(id, name, mimeType, webViewLink, modifiedTime, parents)'
            ).execute()
            
            files = results.get('files', [])
            
            return {
                'success': True,
                'files': files,
                'total_found': len(files),
                'query_used': search_query
            }
            
        except Exception as e:
            logger.error(f"Drive search error: {e}")
            return {'error': f"Drive search failed: {str(e)}"}
    
    async def _get_drive_service(self):
        """Get authenticated Drive service"""
        creds = await self._get_google_credentials()
        if not creds:
            return None
        return build('drive', 'v3', credentials=creds)
    
    async def _get_google_credentials(self) -> Optional['Credentials']:
        """Get Google credentials for the user from database"""
        return await get_user_google_credentials(self.user_id)


class TasksListTool(BaseTool):
    """Tool for listing Google Tasks"""
    name: str = "tasks_list"
    description: str = "List tasks from Google Tasks. Use this to see current todos and task status."
    user_id: int
    
    class ArgsSchema(BaseModel):
        task_list_id: str = Field(default="@default", description="Task list ID (default: @default)")
        show_completed: bool = Field(default=False, description="Include completed tasks")
        max_results: int = Field(default=100, description="Maximum number of tasks")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, task_list_id: str = "@default", show_completed: bool = False, 
            max_results: int = 100) -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, task_list_id: str = "@default", show_completed: bool = False, 
                   max_results: int = 100) -> Dict[str, Any]:
        """List tasks"""
        try:
            service = await self._get_tasks_service()
            if not service:
                return {"error": "Tasks service not available"}
            
            results = service.tasks().list(
                tasklist=task_list_id,
                showCompleted=show_completed,
                maxResults=max_results
            ).execute()
            
            tasks = results.get('items', [])
            
            task_list = []
            for task in tasks:
                task_data = {
                    'id': task['id'],
                    'title': task.get('title', ''),
                    'notes': task.get('notes', ''),
                    'status': task.get('status', ''),
                    'due': task.get('due', ''),
                    'completed': task.get('completed', ''),
                    'updated': task.get('updated', '')
                }
                task_list.append(task_data)
            
            return {
                'success': True,
                'tasks': task_list,
                'total_found': len(task_list),
                'task_list_id': task_list_id
            }
            
        except Exception as e:
            logger.error(f"Tasks list error: {e}")
            return {'error': f"Failed to list tasks: {str(e)}"}
    
    async def _get_tasks_service(self):
        """Get authenticated Tasks service"""
        creds = await self._get_google_credentials()
        if not creds:
            return None
        return build('tasks', 'v1', credentials=creds)
    
    async def _get_google_credentials(self) -> Optional['Credentials']:
        """Get Google credentials for the user from database"""
        return await get_user_google_credentials(self.user_id)


class TasksCreateTool(BaseTool):
    """Tool for creating Google Tasks"""
    name: str = "tasks_create"
    description: str = "Create a new task in Google Tasks. Use this to add todos and action items."
    user_id: int
    
    class ArgsSchema(BaseModel):
        title: str = Field(description="Task title")
        notes: Optional[str] = Field(default=None, description="Task notes/description")
        due: Optional[str] = Field(default=None, description="Due date (RFC 3339 format)")
        task_list_id: str = Field(default="@default", description="Task list ID")
    
    args_schema: type[BaseModel] = ArgsSchema
    
    def _run(self, title: str, notes: Optional[str] = None, due: Optional[str] = None, 
            task_list_id: str = "@default") -> Dict[str, Any]:
        raise NotImplementedError("Use async version")
    
    async def _arun(self, title: str, notes: Optional[str] = None, due: Optional[str] = None, 
                   task_list_id: str = "@default") -> Dict[str, Any]:
        """Create task"""
        try:
            service = await self._get_tasks_service()
            if not service:
                return {"error": "Tasks service not available"}
            
            task_body = {'title': title}
            if notes:
                task_body['notes'] = notes
            if due:
                task_body['due'] = due
            
            result = service.tasks().insert(
                tasklist=task_list_id,
                body=task_body
            ).execute()
            
            return {
                'success': True,
                'task_id': result['id'],
                'title': result.get('title', ''),
                'status': result.get('status', ''),
                'task_list_id': task_list_id
            }
            
        except Exception as e:
            logger.error(f"Tasks create error: {e}")
            return {'error': f"Failed to create task: {str(e)}"}
    
    async def _get_tasks_service(self):
        """Get authenticated Tasks service"""
        creds = await self._get_google_credentials()
        if not creds:
            return None
        return build('tasks', 'v1', credentials=creds)
    
    async def _get_google_credentials(self) -> Optional['Credentials']:
        """Get Google credentials for the user from database"""
        return await get_user_google_credentials(self.user_id)


class GoogleWorkspaceAgentNativeMCP:
    """Google Workspace agent using direct Google API integration with stored OAuth tokens"""
    
    def __init__(self):
        self.name = "google_workspace"
        self.description = "Handles Gmail, Calendar, Drive, and Tasks operations using direct Google API integration"
        self.model = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=0.0,
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        self.tools = None  # Will be created when user_id is available
        self.agent = None
        self.system_prompt = self._get_system_prompt()
        
    def _create_tools(self, user_id: int) -> List[BaseTool]:
        """Create Google Workspace tools for specific user"""
        if not GOOGLE_AVAILABLE:
            logger.warning("Google API libraries not available. Install with: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
            return []
        
        return [
            GmailSearchTool(user_id=user_id),
            GmailGetMessageTool(user_id=user_id),
            GmailSendTool(user_id=user_id),
            CalendarListEventsTool(user_id=user_id),
            CalendarCreateEventTool(user_id=user_id),
            DriveSearchTool(user_id=user_id),
            TasksListTool(user_id=user_id),
            TasksCreateTool(user_id=user_id)
        ]
        
    async def _ensure_agent_ready(self, user_id: int):
        """Ensure agent is initialized for specific user"""
        if not self.agent or not self.tools:
            try:
                # Check if user has Google credentials
                credentials = await get_user_google_credentials(user_id)
                if not credentials:
                    raise GoogleWorkspaceError("User has not authorized Google Workspace access")
                
                # Create tools for this user if not exists
                self.tools = self._create_tools(user_id)
                
                # Create react agent with tools
                self.agent = create_react_agent(
                    self.model,
                    self.tools,
                    state_modifier=self.system_prompt
                )
                
                logger.info(f"Initialized Google Workspace agent with {len(self.tools)} tools for user {user_id}")
                
            except Exception as e:
                logger.error(f"Failed to initialize Google Workspace agent: {e}")
                raise
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for the agent"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        return f"""You are a Google Workspace specialist agent with expertise in Gmail, Google Calendar, Drive, and Tasks.

Today's date: {today}

You have access to the following Google Workspace tools using the user's authenticated account:

## Gmail Tools:
- **gmail_search**: Search emails with Gmail's query syntax
  - Use queries like "from:john@example.com", "subject:invoice", "is:unread", "has:attachment"
  - Date queries: "newer_than:7d" (past week), "after:2025/7/1", "before:2025/7/20"
  - Returns message summaries with IDs
- **gmail_get_message**: Get full email content by message ID
  - Use this after gmail_search to get complete email text
- **gmail_send**: Send emails with to, subject, body, and optional cc/bcc

## Calendar Tools:
- **calendar_list_events**: List upcoming calendar events
  - Can filter by time range and specify different calendars
- **calendar_create_event**: Create new calendar events
  - Requires summary, start_time, end_time (ISO format)
  - Optional: description, location, attendees

## Drive Tools:
- **drive_search**: Search Google Drive files
  - Search by name, filter by MIME type, search within folders
  - Common MIME types: "application/vnd.google-apps.document" (Docs), "application/vnd.google-apps.spreadsheet" (Sheets)

## Tasks Tools:
- **tasks_list**: List tasks from Google Tasks
  - Can show completed tasks, specify task lists
- **tasks_create**: Create new tasks
  - Requires title, optional notes and due date

## Your Expertise:
- Email automation and management
- Calendar scheduling and availability management
- Document organization and collaboration  
- Task tracking and project management
- Cross-service integration (e.g., creating calendar events from emails)

## Business Context:
- These tools help iDrinkCoffee.com manage communications and operations
- Email is critical for customer service and supplier communications
- Calendar manages meetings with vendors and team schedules
- Drive stores product documentation and business files
- Tasks track operational to-dos and projects

## Best Practices:
- **Email workflow**: First use gmail_search to find emails, then use gmail_get_message with the messageId to get full content
- Use appropriate filters when searching to avoid overwhelming results
- Maintain professional communication standards
- Respect privacy and confidentiality of business data
- Handle authentication errors gracefully
- Provide clear feedback on operation results

## Date Awareness:
- Today's date is {today}
- Use this for relative date calculations (e.g., "tasks due this week", "emails from past 7 days")
- For Gmail queries, use date filters like "newer_than:7d" or "after:{today}"
- When creating tasks/events, ensure dates are in the future unless explicitly historical

Always provide clear, formatted responses with relevant information and confirm successful operations."""
    
    async def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state and return updated state"""
        try:
            # Extract user_id from state
            user_id = state.get("user_id")
            if not user_id:
                state["messages"].append(AIMessage(
                    content="Google Workspace agent requires user authentication. Please provide user context.",
                    metadata={"agent": self.name, "error": True}
                ))
                return state
            
            # Convert user_id to int if it's a string
            if isinstance(user_id, str):
                user_id = int(user_id)
            
            await self._ensure_agent_ready(user_id)
            
            messages = state.get("messages", [])
            
            if not messages:
                return state
            
            # Get last user message
            last_message = messages[-1]
            if not isinstance(last_message, HumanMessage):
                return state
            
            # Use the agent to process the request with full conversation history
            agent_state = {"messages": messages}
            
            # Run the agent
            logger.info(f"🚀 Running Google Workspace agent with message: {last_message.content[:100]}...")
            result = await self.agent.ainvoke(agent_state)
            logger.info(f"✅ Google Workspace agent completed")
            
            # Extract the response
            if result.get("messages"):
                # Get the last AI message from the agent's response
                agent_messages = result["messages"]
                for msg in reversed(agent_messages):
                    if hasattr(msg, 'content') and msg.content:
                        state["messages"].append(AIMessage(
                            content=msg.content,
                            metadata={"agent": self.name}
                        ))
                        break
            else:
                state["messages"].append(AIMessage(
                    content="I processed your request but couldn't generate a response.",
                    metadata={"agent": self.name}
                ))
            
            state["last_agent"] = self.name
            return state
            
        except GoogleWorkspaceError as e:
            logger.error(f"Google Workspace authentication error: {e}")
            state["messages"].append(AIMessage(
                content=f"Google Workspace access error: {str(e)}. Please ensure you have authorized Google Workspace access.",
                metadata={"agent": self.name, "error": True}
            ))
            return state
        except Exception as e:
            logger.error(f"Error in GoogleWorkspaceAgentNativeMCP: {e}")
            state["messages"].append(AIMessage(
                content=f"Error in Google Workspace agent: {str(e)}",
                metadata={"agent": self.name, "error": True}
            ))
            return state
    
    def should_handle(self, state: Dict[str, Any]) -> bool:
        """Determine if this agent should handle the request"""
        last_message = state.get("messages", [])[-1] if state.get("messages") else None
        
        if not last_message:
            return False
        
        # Keywords related to Google Workspace services
        keywords = [
            "email", "gmail", "mail", "send", "inbox", "message",
            "calendar", "schedule", "meeting", "appointment", "event",
            "drive", "document", "file", "folder", "doc", "sheet", "slide",
            "task", "todo", "reminder", "deadline", "google"
        ]
        
        message_content = last_message.content.lower()
        return any(keyword in message_content for keyword in keywords)
    
    async def cleanup(self):
        """Clean up resources"""
        # No persistent connections to clean up for direct API calls
        pass