"""
API v1 Router Aggregator for GODDESS AI 2.0.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import ai, auth, cohost, dashboard, health, moderation, modules, operations, streams, ws

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(dashboard.router, tags=["Dashboard Overview"])
api_router.include_router(operations.router)
api_router.include_router(streams.router)
api_router.include_router(ai.router)
api_router.include_router(moderation.router)
api_router.include_router(cohost.router)
api_router.include_router(modules.router)
api_router.include_router(ws.router, tags=["WebSocket"])
