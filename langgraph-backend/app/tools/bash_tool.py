"""
Bash execution tool for the bash agent.
Executes bash commands within a secure sandbox directory.
"""

import os
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BashTool:
    def __init__(self):
        # Set up sandbox directory
        self.sandbox_dir = Path(__file__).parent.parent / "agent_sandbox"
        self.sandbox_dir.mkdir(exist_ok=True)
        
        # Ensure sandbox is properly isolated
        self.sandbox_path = str(self.sandbox_dir.absolute())
        logger.info(f"Bash tool initialized with sandbox: {self.sandbox_path}")
    
    async def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a bash command in the sandbox directory.
        
        Args:
            command: The bash command to execute
            timeout: Timeout in seconds (default: 30)
            
        Returns:
            Dict with output, error, return_code, and any created files
        """
        try:
            # Log the command being executed
            logger.info(f"Executing bash command in sandbox: {command}")
            
            # List files before execution
            files_before = set(os.listdir(self.sandbox_path)) if os.path.exists(self.sandbox_path) else set()
            
            # Execute command in sandbox directory
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=self.sandbox_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, 'PWD': self.sandbox_path}
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), 
                    timeout=timeout
                )
                return_code = process.returncode
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds",
                    "return_code": -1,
                    "stdout": "",
                    "stderr": "",
                    "created_files": []
                }
            
            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""
            
            # Check for newly created files
            files_after = set(os.listdir(self.sandbox_path)) if os.path.exists(self.sandbox_path) else set()
            created_files = list(files_after - files_before)
            
            # Create file info for created files
            file_info = []
            for file in created_files:
                file_path = Path(self.sandbox_path) / file
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    file_info.append({
                        "name": file,
                        "size": file_size,
                        "url": f"/api/sandbox/{file}"
                    })
            
            success = return_code == 0
            
            result = {
                "success": success,
                "return_code": return_code,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "created_files": file_info,
                "working_directory": self.sandbox_path
            }
            
            if not success:
                result["error"] = f"Command failed with return code {return_code}"
                if stderr_str:
                    result["error"] += f": {stderr_str}"
            
            logger.info(f"Command completed: success={success}, return_code={return_code}, created_files={len(file_info)}")
            return result
            
        except Exception as e:
            logger.error(f"Error executing bash command: {e}")
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "return_code": -1,
                "stdout": "",
                "stderr": "",
                "created_files": []
            }
    
    async def list_sandbox_files(self) -> Dict[str, Any]:
        """List all files in the sandbox directory."""
        try:
            files = []
            if os.path.exists(self.sandbox_path):
                for item in os.listdir(self.sandbox_path):
                    item_path = os.path.join(self.sandbox_path, item)
                    if os.path.isfile(item_path):
                        file_size = os.path.getsize(item_path)
                        files.append({
                            "name": item,
                            "size": file_size,
                            "url": f"/api/sandbox/{item}"
                        })
            
            return {
                "success": True,
                "files": files,
                "sandbox_path": self.sandbox_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "files": []
            }
    
    async def clean_sandbox(self) -> Dict[str, Any]:
        """Clean the sandbox directory (remove all files except README.md and .gitignore)."""
        try:
            removed_files = []
            if os.path.exists(self.sandbox_path):
                for item in os.listdir(self.sandbox_path):
                    if item not in ['README.md', '.gitignore']:
                        item_path = os.path.join(self.sandbox_path, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                            removed_files.append(item)
                        elif os.path.isdir(item_path):
                            import shutil
                            shutil.rmtree(item_path)
                            removed_files.append(f"{item}/ (directory)")
            
            return {
                "success": True,
                "message": f"Cleaned sandbox directory",
                "removed_files": removed_files
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# Global instance
bash_tool = BashTool()