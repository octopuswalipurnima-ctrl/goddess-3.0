"""
REST API Endpoints for Module System in GODDESS AI 2.0.

Provides endpoints to list, configure, inspect health, and manage lifecycles
of pluggable extension modules globally and per stream.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import require_permission
from app.modules import (
    ModuleHealth,
    ModuleInfo,
    ModuleNotFoundError,
    StreamModuleConfig,
    module_manager,
)

router = APIRouter(prefix="/modules", tags=["Module System"])


class ModuleConfigUpdateRequest(BaseModel):
    enabled: bool
    settings: Dict[str, Any] = {}


@router.get(
    "",
    response_model=List[ModuleInfo],
    dependencies=[Depends(require_permission("modules.read"))],
    summary="List Registered Modules",
)
async def list_modules():
    """List all registered modules with global status, capabilities, and health."""
    return module_manager.list_modules()


@router.get(
    "/{module_id}",
    response_model=ModuleInfo,
    dependencies=[Depends(require_permission("modules.read"))],
    summary="Get Module Details",
)
async def get_module_details(module_id: str):
    """Retrieve detailed metadata, lifecycle state, and diagnostics for a specific module."""
    try:
        return module_manager.get_module_info(module_id)
    except ModuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' is not registered.",
        )


@router.post(
    "/{module_id}/enable",
    response_model=ModuleInfo,
    dependencies=[Depends(require_permission("modules.configure"))],
    summary="Enable Module Globally",
)
async def enable_module(module_id: str):
    """Enable a module globally."""
    try:
        mod = await module_manager.enable_module(module_id)
        return mod.to_info()
    except ModuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' is not registered.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{module_id}/disable",
    response_model=ModuleInfo,
    dependencies=[Depends(require_permission("modules.configure"))],
    summary="Disable Module Globally",
)
async def disable_module(module_id: str):
    """Disable a module globally."""
    try:
        mod = await module_manager.disable_module(module_id)
        return mod.to_info()
    except ModuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' is not registered.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{module_id}/start",
    response_model=ModuleInfo,
    dependencies=[Depends(require_permission("modules.configure"))],
    summary="Start Module",
)
async def start_module(module_id: str):
    """Start an enabled module."""
    try:
        mod = await module_manager.start_module(module_id)
        return mod.to_info()
    except ModuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' is not registered.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.post(
    "/{module_id}/stop",
    response_model=ModuleInfo,
    dependencies=[Depends(require_permission("modules.configure"))],
    summary="Stop Module",
)
async def stop_module(module_id: str):
    """Stop a running module."""
    try:
        mod = await module_manager.stop_module(module_id)
        return mod.to_info()
    except ModuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' is not registered.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "/{module_id}/health",
    response_model=ModuleHealth,
    dependencies=[Depends(require_permission("modules.read"))],
    summary="Get Module Health",
)
async def get_module_health(module_id: str):
    """Get health status and diagnostics for a module."""
    try:
        info = module_manager.get_module_info(module_id)
        return info.health
    except ModuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' is not registered.",
        )


@router.get(
    "/{module_id}/config/{stream_id}",
    response_model=StreamModuleConfig,
    dependencies=[Depends(require_permission("modules.read"))],
    summary="Get Stream Module Configuration",
)
async def get_stream_module_config(module_id: str, stream_id: str):
    """Retrieve stream-specific configuration for a module."""
    try:
        return module_manager.get_stream_config(module_id, stream_id)
    except ModuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' is not registered.",
        )


@router.put(
    "/{module_id}/config/{stream_id}",
    response_model=StreamModuleConfig,
    dependencies=[Depends(require_permission("modules.configure"))],
    summary="Update Stream Module Configuration",
)
async def update_stream_module_config(module_id: str, stream_id: str, payload: ModuleConfigUpdateRequest):
    """Update stream-specific configuration for a module."""
    try:
        config = StreamModuleConfig(enabled=payload.enabled, settings=payload.settings)
        return module_manager.update_stream_config(module_id, stream_id, config)
    except ModuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' is not registered.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
