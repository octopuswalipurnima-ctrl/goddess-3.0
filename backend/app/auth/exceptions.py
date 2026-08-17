"""
Standard Authentication and Authorization Exceptions for GODDESS AI 2.0.
"""

from typing import Optional
from fastapi import HTTPException, status


class CredentialsException(HTTPException):
    def __init__(self, detail: str = "Could not validate authentication credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class TokenExpiredException(HTTPException):
    def __init__(self, detail: str = "Authentication token has expired. Please log in again."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenException(HTTPException):
    def __init__(self, detail: str = "Invalid or tampered authentication token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class PermissionDeniedException(HTTPException):
    def __init__(
        self,
        detail: str = "Forbidden: Insufficient permissions for this operation",
        required_permission: Optional[str] = None,
    ):
        full_detail = f"{detail} (requires '{required_permission}')" if required_permission else detail
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=full_detail,
        )


class UserInactiveException(HTTPException):
    def __init__(self, detail: str = "User account is inactive"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class RateLimitExceededException(HTTPException):
    def __init__(self, detail: str = "Rate limit exceeded. Please slow down.", retry_after: Optional[int] = None):
        headers = {"Retry-After": str(retry_after)} if retry_after is not None else {}
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
        )
