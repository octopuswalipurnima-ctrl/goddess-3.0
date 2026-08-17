"""
Tests for Module capability and permission model.
"""

from app.modules.models import ModuleCapability, ModuleMetadata


def test_module_capability_declarations():
    meta = ModuleMetadata(
        id="perm_test",
        name="Perm Test",
        capabilities=[
            ModuleCapability.CHAT_READ,
            ModuleCapability.CHAT_WRITE,
            ModuleCapability.STREAM_READ,
        ],
    )
    assert ModuleCapability.CHAT_READ in meta.capabilities
    assert ModuleCapability.CHAT_WRITE in meta.capabilities
    assert ModuleCapability.AI_REQUEST not in meta.capabilities
