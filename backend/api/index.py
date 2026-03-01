"""
Vercel serverless entry point.
Imports the FastAPI app from main.py and wraps it with Mangum
for AWS Lambda / Vercel ASGI compatibility.
"""

import os
import sys

# Make sure the backend root is on the path so `app.*` imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import and initialize DB tables for serverless (runs once per cold start)
try:
    from app.database import init_db
    init_db()
    print("✓ Database tables initialized")
except Exception as e:
    print(f"⚠ Database init warning: {e}")
    # Non-blocking - will retry on first request

from main import app  # noqa: E402
from mangum import Mangum  # noqa: E402

# lifespan="off" disables startup/shutdown events (handled above)
handler = Mangum(app, lifespan="off")
