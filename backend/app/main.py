"""
AI Border Sentinel - App Main Proxy Entry Point

Re-exports unified FastAPI application from backend.main for backward compatibility.
"""

from backend.main import app, root

__all__ = ["app", "root"]
