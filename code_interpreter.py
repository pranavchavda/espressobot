
import io
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
import ast
import builtins

def is_safe_code(code):
    """
    Basic safety check for user-submitted code.
    Blocks obvious dangerous operations.
    """
    # List of forbidden calls/imports
    forbidden = [
        'os.system', 'subprocess', 'eval', 'exec', 'execfile',
        'open', 'file', '__import__', 'input', 'compile',
        'pty', 'socket', 'sys.modules', 'importlib',
    ]
    
    try:
        parsed = ast.parse(code)
        
        for node in ast.walk(parsed):
            # Check for import statements
            if isinstance(node, ast.Import):
                for name in node.names:
                    if name.name in ['os', 'subprocess', 'sys']:
                        return False, f"Forbidden import: {name.name}"
                        
            # Check for import from statements
            elif isinstance(node, ast.ImportFrom):
                if node.module in ['os', 'subprocess', 'sys']:
                    return False, f"Forbidden import from: {node.module}"
                    
            # Check for calls to forbidden functions
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ['eval', 'exec', 'compile']:
                    return False, f"Forbidden function call: {node.func.id}"
                    
                # Check for attribute access like os.system
                elif isinstance(node.func, ast.Attribute):
                    attr_path = f"{node.func.value.id}.{node.func.attr}" if hasattr(node.func.value, 'id') else node.func.attr
                    if attr_path in forbidden:
                        return False, f"Forbidden function call: {attr_path}"
        
        return True, "Code passed safety check"
    except SyntaxError as e:
        return False, f"Syntax error: {str(e)}"
    except Exception as e:
        return False, f"Error analyzing code: {str(e)}"

def execute_code(code, globals_dict=None, timeout=10):
    """
    Execute Python code in a controlled environment and return the output.
    
    Args:
        code (str): Python code to execute
        globals_dict (dict, optional): Global variables dictionary
        timeout (int, optional): Maximum execution time in seconds
    
    Returns:
        dict: Dictionary containing execution results and status
    """
    # Check if code is safe to execute
    is_safe, message = is_safe_code(code)
    if not is_safe:
        return {
            "status": "error",
            "error": message,
            "output": "",
            "result": None
        }
    
    # Create a safe globals dictionary with limited builtins
    if globals_dict is None:
        globals_dict = {}
    
    # Create a safe set of builtins, removing potentially dangerous ones
    safe_builtins = dict(builtins.__dict__)
    for name in ['open', 'exec', 'eval', 'compile', '__import__']:
        if name in safe_builtins:
            del safe_builtins[name]
    
    # Add safe builtins to globals
    globals_dict['__builtins__'] = safe_builtins
    
    # Capture stdout and stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    result = None
    
    try:
        with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
            # Execute the code
            result = exec(code, globals_dict)
            
        return {
            "status": "success",
            "output": stdout_capture.getvalue(),
            "error": stderr_capture.getvalue(),
            "result": result  # Usually None unless the last statement evaluates to something
        }
    
    except Exception as e:
        return {
            "status": "error",
            "output": stdout_capture.getvalue(),
            "error": f"{stderr_capture.getvalue()}\n{traceback.format_exc()}",
            "result": None
        }
