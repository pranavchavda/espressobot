"""
Sandbox file serving API.
Serves files created by the bash agent in the sandbox directory.
"""

import os
import mimetypes
from pathlib import Path
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Get sandbox directory path
SANDBOX_DIR = Path(__file__).parent.parent / "agent_sandbox"

@router.get("/sandbox/{filename}")
async def serve_sandbox_file(filename: str):
    """
    Serve a file from the bash agent sandbox directory.
    
    Args:
        filename: Name of the file to serve
        
    Returns:
        File content with appropriate MIME type
    """
    try:
        # Security: Only allow files directly in sandbox directory (no subdirectories)
        if '/' in filename or '..' in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        file_path = SANDBOX_DIR / filename
        
        # Check if file exists and is actually a file
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Not a file")
        
        # Check if file is within sandbox directory (security check)
        try:
            file_path.resolve().relative_to(SANDBOX_DIR.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Determine MIME type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"
        
        logger.info(f"Serving sandbox file: {filename} ({content_type})")
        
        # Return file response
        return FileResponse(
            path=str(file_path),
            media_type=content_type,
            filename=filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving sandbox file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/sandbox")
async def list_sandbox_files():
    """
    List all files in the sandbox directory.
    
    Returns:
        JSON list of files with metadata
    """
    try:
        files = []
        
        if SANDBOX_DIR.exists():
            for item in SANDBOX_DIR.iterdir():
                if item.is_file() and item.name not in ['.gitignore']:
                    file_stat = item.stat()
                    files.append({
                        "name": item.name,
                        "size": file_stat.st_size,
                        "modified": file_stat.st_mtime,
                        "url": f"/api/sandbox/{item.name}"
                    })
        
        return {
            "success": True,
            "files": files,
            "sandbox_path": str(SANDBOX_DIR)
        }
        
    except Exception as e:
        logger.error(f"Error listing sandbox files: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")