"""Vercel entry point. Vercel's Python runtime serves the WSGI object named `app` from this file;
vercel.json rewrites every path here, and Flask routes it (pages, /static, /api)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from failover.app.server import app  # noqa: E402,F401
