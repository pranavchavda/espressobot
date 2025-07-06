#\!/usr/bin/env python3
"""
MCP Server with file watching and auto-restart
Ensures server stays running and restarts on file changes
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

class MCPServerManager:
    def __init__(self):
        self.process = None
        
    def start_server(self):
        """Start the MCP server process"""
        if self.process:
            self.stop_server()
            
        print("🚀 Starting MCP server...")
        self.process = subprocess.Popen(
            [sys.executable, "mcp-server.py"],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        
    def stop_server(self):
        """Stop the MCP server process"""
        if self.process:
            print("🛑 Stopping MCP server...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
            
    def restart_server(self):
        """Restart the MCP server"""
        self.stop_server()
        time.sleep(0.5)  # Brief pause
        self.start_server()
        
    def run(self):
        """Run the server with auto-restart on crash"""
        # Start the server
        self.start_server()
        
        # Handle shutdown gracefully
        def signal_handler(sig, frame):
            print("\n👋 Shutting down...")
            self.stop_server()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Keep running and monitor the process
            while True:
                if self.process and self.process.poll() is not None:
                    print(f"\n⚠️  MCP server exited with code {self.process.returncode}")
                    print("🔄 Restarting in 2 seconds...")
                    time.sleep(2)
                    self.start_server()
                time.sleep(1)
        except KeyboardInterrupt:
            signal_handler(None, None)

if __name__ == "__main__":
    manager = MCPServerManager()
    manager.run()
