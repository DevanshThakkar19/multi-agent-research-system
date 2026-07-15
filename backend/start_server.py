#!/usr/bin/env python3
"""
Startup script for Multi-Agent Research System Backend
Run this from the backend directory: python start_server.py
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Check for required API keys
if not os.getenv("OPENAI_API_KEY"):
    print("⚠️  WARNING: OPENAI_API_KEY not found in environment!")
    print("   Please create a .env file with your API keys.")
    print("   See .env.example for template.")
    print()
    # Check if running interactively
    if sys.stdin.isatty():
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    else:
        print("   Starting server anyway (non-interactive mode)...")
        print("   Note: Agents will fail without OPENAI_API_KEY")

# Import and run
if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Multi-Agent Research System Backend...")
    print("📡 API will be available at http://localhost:8000")
    print("📚 API docs at http://localhost:8000/docs")
    print()
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

