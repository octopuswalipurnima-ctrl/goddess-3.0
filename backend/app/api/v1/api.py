"""
API v1 Router Aggregator for GODDESS AI 2.0.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import health, streams, ws

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(streams.router)
api_router.include_router(ws.router, tags=["WebSocket"])
