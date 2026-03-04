"""
Vercel serverless entry point for FastAPI.
Exposes the FastAPI app for Vercel's Python runtime.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize database on cold start (non-blocking)
try:
    from app.database import init_db

    init_db()
    print("✓ Database initialized")
except Exception as e:
    print(f"⚠ DB init deferred: {e}")

# Import the FastAPI application
from main import app  # noqa: E402

# Vercel expects 'app' variable for ASGI applications
# No need for Mangum - Vercel handles ASGI→Lambda internally
