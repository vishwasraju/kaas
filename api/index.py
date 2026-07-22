import sys
import os

# Add root directory to sys.path so modules (routes, models, pipeline, etc.) are importable
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app

# Export app for Vercel serverless function
__all__ = ["app"]
