"""
Exceptions for Module System in GODDESS AI 2.0.
"""


class ModuleError(Exception):
    """Base exception for all module-related errors."""
    pass


class ModuleNotFoundError(ModuleError):
    """Raised when a requested module ID is not registered."""
    pass


class DuplicateModuleError(ModuleError):
    """Raised when attempting to register a module with an already registered ID."""
    pass


class InvalidModuleMetadataError(ModuleError):
    """Raised when module metadata fails schema validation."""
    pass


class InvalidStateTransitionError(ModuleError):
    """Raised when an invalid lifecycle transition is attempted."""
    pass


class MissingDependencyError(ModuleError):
    """Raised when a module requires a dependency that is not registered or loaded."""
    pass


class CircularDependencyError(ModuleError):
    """Raised when circular dependencies are detected in the module dependency graph."""
    pass


class ModuleExecutionError(ModuleError):
    """Raised when an unhandled error occurs during module event handling or execution."""
    pass


class PermissionDeniedError(ModuleError):
    """Raised when a module attempts an action without declaring the required capability."""
    pass
