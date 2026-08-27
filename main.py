"""Root-level ASGI application entrypoint for Railway and Uvicorn compatibility."""

from app.main import app

__all__ = ["app"]
