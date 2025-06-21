#!/usr/bin/env python
"""Run the EspressoBot v0.2 API server."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Check for required environment variables
if not os.getenv('OPENAI_API_KEY'):
    print("ERROR: OPENAI_API_KEY not set in .env file")
    print("Please add your OpenAI API key to the .env file")
    sys.exit(1)

# Run the server
import uvicorn

if __name__ == "__main__":
    print("Starting EspressoBot v0.2 API server...")
    print("API will be available at: http://localhost:8000")
    print("Frontend should connect to: http://localhost:8000/chat")
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )