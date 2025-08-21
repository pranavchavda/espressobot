#!/usr/bin/env python3
"""
Quick setup script for CLI authentication using existing JWT token
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

# Your JWT token from the browser
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MSwiZW1haWwiOiJwcmFuYXZAaWRyaW5rY29mZmVlLmNvbSIsIm5hbWUiOiJQcmFuYXYgQ2hhdmRhIiwiaWF0IjoxNzU1Njk5Njk1LCJleHAiOjE3NTYzMDQ0OTV9.2KL4xMxfx6tOMDYOAJtMtU422-XARqXD2ZnxgBlZ_H0"

def setup_cli_auth():
    """Set up CLI authentication with JWT token"""
    
    # Create config directory
    config_dir = Path.home() / ".config" / "espressobot"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "cli.json"
    
    # Create config with JWT token
    config = {
        "base_url": "http://localhost:8000",
        "default_user_id": "1",
        "timeout": 60.0,
        "max_retries": 3,
        "access_token": JWT_TOKEN
    }
    
    # Save config
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ CLI authentication configured!")
    print(f"📁 Config saved to: {config_file}")
    print(f"👤 User: pranav@idrinkcoffee.com")
    print(f"⏰ Token expires: 2025-08-27 10:21:35")
    print()
    print("🚀 You can now use OAuth-required CLI commands:")
    print("   python cli.py --message 'check my email'")
    print("   python cli.py --message 'what is my GA4 traffic today'")

if __name__ == "__main__":
    setup_cli_auth()