"""
Vercel serverless entry point for FastAPI.
Vercel has native ASGI support, so we just export the app directly.
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

# Import and export FastAPI app
from main import app  # noqa: E402, F401

# Vercel will use 'app' directly via native ASGI support
