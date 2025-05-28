"""
Filesystem service implementation for safe file operations.
Replaces the FileSystemMCPServer with a direct implementation.
"""
import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Union
import logging
import shutil

from services.base_service import BaseService, ServiceError
from services.config import service_config

class FilesystemServiceError(ServiceError):
    """Exception raised for filesystem service errors."""
    pass

class FilesystemService(BaseService):
    """
    Direct implementation of filesystem service functionality.
    Provides controlled file operations without MCP overhead.
    """
    def __init__(self):
        """Initialize the filesystem service."""
        super().__init__("filesystem")
        
        # Get storage path from config
        self.storage_path = service_config.get(
            "filesystem", 
            "storage_path", 
            os.path.join(os.getcwd(), "storage")
        )
        
        # Ensure storage directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Create subdirectories
        self.templates_dir = os.path.join(self.storage_path, "templates")
        self.exports_dir = os.path.join(self.storage_path, "exports")
        self.users_dir = os.path.join(self.storage_path, "users")
        
        os.makedirs(self.templates_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)
        os.makedirs(self.users_dir, exist_ok=True)
    
    def _get_user_dir(self, user_id: str) -> str:
        """
        Get the storage directory for a specific user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Path to user's storage directory
        """
        user_dir = os.path.join(self.users_dir, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def _resolve_path(self, path: str, user_id: Optional[str] = None) -> str:
        """
        Resolve a path to its absolute location within the controlled storage.
        
        Args:
            path: Relative path within the storage
            user_id: Optional user identifier for user-specific paths
            
        Returns:
            Absolute path within the controlled storage
            
        Raises:
            FilesystemServiceError: If path attempts to escape the controlled storage
        """
        # Handle user-specific paths
        if path.startswith("users/") and user_id:
            # Replace users/ with the actual user directory
            path = os.path.join(self._get_user_dir(user_id), path[6:])
        elif user_id:
            # If user_id is provided but path doesn't start with users/,
            # assume it's a user-specific path
            path = os.path.join(self._get_user_dir(user_id), path)
        else:
            # Regular path within storage
            path = os.path.join(self.storage_path, path)
        
        # Normalize path
        normalized_path = os.path.normpath(path)
        
        # Ensure path is within storage
        if not normalized_path.startswith(self.storage_path):
            raise FilesystemServiceError(f"Path '{path}' attempts to escape controlled storage")
        
        return normalized_path
    
    async def read_file(self, path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Read a file from the controlled storage.
        
        Args:
            path: Relative path within the storage
            user_id: Optional user identifier for user-specific paths
            
        Returns:
            File content and metadata
        """
        try:
            # Resolve path
            full_path = self._resolve_path(path, user_id)
            
            # Check if file exists
            if not os.path.isfile(full_path):
                return {
                    "success": False,
                    "error": f"File '{path}' not found"
                }
            
            # Read file
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "path": path,
                "content": content,
                "size": os.path.getsize(full_path),
                "modified": os.path.getmtime(full_path)
            }
        except Exception as e:
            raise FilesystemServiceError(f"Failed to read file '{path}': {str(e)}")
    
    async def write_file(self, path: str, content: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Write content to a file in the controlled storage.
        
        Args:
            path: Relative path within the storage
            content: Content to write
            user_id: Optional user identifier for user-specific paths
            
        Returns:
            Success status and metadata
        """
        try:
            # Resolve path
            full_path = self._resolve_path(path, user_id)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Write file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "path": path,
                "size": os.path.getsize(full_path),
                "modified": os.path.getmtime(full_path)
            }
        except Exception as e:
            raise FilesystemServiceError(f"Failed to write file '{path}': {str(e)}")
    
    async def list_directory(self, path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        List contents of a directory in the controlled storage.
        
        Args:
            path: Relative path within the storage
            user_id: Optional user identifier for user-specific paths
            
        Returns:
            Directory contents and metadata
        """
        try:
            # Resolve path
            full_path = self._resolve_path(path, user_id)
            
            # Check if directory exists
            if not os.path.isdir(full_path):
                return {
                    "success": False,
                    "error": f"Directory '{path}' not found"
                }
            
            # List directory
            items = os.listdir(full_path)
            
            # Get item details
            contents = []
            for item in items:
                item_path = os.path.join(full_path, item)
                contents.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0,
                    "modified": os.path.getmtime(item_path)
                })
            
            return {
                "success": True,
                "path": path,
                "contents": contents
            }
        except Exception as e:
            raise FilesystemServiceError(f"Failed to list directory '{path}': {str(e)}")
    
    async def delete_file(self, path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a file from the controlled storage.
        
        Args:
            path: Relative path within the storage
            user_id: Optional user identifier for user-specific paths
            
        Returns:
            Success status and metadata
        """
        try:
            # Resolve path
            full_path = self._resolve_path(path, user_id)
            
            # Check if file exists
            if not os.path.isfile(full_path):
                return {
                    "success": False,
                    "error": f"File '{path}' not found"
                }
            
            # Delete file
            os.remove(full_path)
            
            return {
                "success": True,
                "path": path
            }
        except Exception as e:
            raise FilesystemServiceError(f"Failed to delete file '{path}': {str(e)}")
    
    async def check_file_exists(self, path: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if a file exists in the controlled storage.
        
        Args:
            path: Relative path within the storage
            user_id: Optional user identifier for user-specific paths
            
        Returns:
            Existence status and metadata
        """
        try:
            # Resolve path
            full_path = self._resolve_path(path, user_id)
            
            # Check if file exists
            exists = os.path.isfile(full_path)
            
            return {
                "success": True,
                "path": path,
                "exists": exists,
                "size": os.path.getsize(full_path) if exists else 0,
                "modified": os.path.getmtime(full_path) if exists else 0
            }
        except Exception as e:
            raise FilesystemServiceError(f"Failed to check file existence '{path}': {str(e)}")

# Create a singleton instance
filesystem_service = FilesystemService()
