"""
Bash execution tool for the bash agent.
Executes bash commands in the project's root directory.
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
        # Set up the root directory
        self.root_dir = Path(__file__).parent.parent.parent 
        logger.info(f"Bash tool initialized with root directory: {self.root_dir}")
    
    async def execute_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a bash command in the project's root directory.

        Args:
            command: The bash command to execute
            timeout: Timeout in seconds (default: 30)

        Returns:
            Dict with output, error, and return_code
        """
        try:
            # Log the command being executed
            logger.info(f"Executing bash command: {command}")

            # Execute command in the root directory
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=str(self.root_dir),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, 'PWD': str(self.root_dir)}
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
                }

            # Decode output
            stdout_str = stdout.decode('utf-8', errors='replace') if stdout else ""
            stderr_str = stderr.decode('utf-8', errors='replace') if stderr else ""

            success = return_code == 0

            result = {
                "success": success,
                "return_code": return_code,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "working_directory": str(self.root_dir)
            }

            if not success:
                result["error"] = f"Command failed with return code {return_code}"
                if stderr_str:
                    result["error"] += f": {stderr_str}"

            logger.info(f"Command completed: success={success}, return_code={return_code}")
            return result

        except Exception as e:
            logger.error(f"Error executing bash command: {e}")
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "return_code": -1,
                "stdout": "",
                "stderr": "",
            }
    


# Global instance
bash_tool = BashTool()