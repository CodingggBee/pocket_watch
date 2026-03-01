"""
Vercel serverless entry point.
Imports the FastAPI app from main.py and wraps it with Mangum
for AWS Lambda / Vercel ASGI compatibility.
"""

import os
import sys

# Make sure the backend root is on the path so `app.*` imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # noqa: E402
from mangum import Mangum  # noqa: E402

handler = Mangum(app, lifespan="off")
