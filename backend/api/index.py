"""
Vercel serverless entry point for FastAPI.
Uses Mangum to adapt ASGI (FastAPI) to AWS Lambda/Vercel format.
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

# Import FastAPI app and Mangum adapter
from main import app  # noqa: E402
from mangum import Mangum  # noqa: E402

# Create the Lambda/Vercel handler
# lifespan="off" because we handle initialization above
handler = Mangum(app, lifespan="off")
