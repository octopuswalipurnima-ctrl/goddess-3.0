"""
Cryptographic Password Hashing and JWT Token Management for GODDESS AI 2.0.

Provides PBKDF2-HMAC-SHA256 salted password hashing, timing-attack-proof verification,
and hardened JWT creation and verification.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets
from typing import Any, Dict, List, Optional
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from app.auth.exceptions import (
    CredentialsException,
    InvalidTokenException,
    TokenExpiredException,
)
from app.auth.models import TokenPayload, UserRole
from app.auth.permissions import get_permissions_for_role
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("auth.service")

# Password Hashing Parameters
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 32


class AuthService:
    """Core cryptographic and token management service."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using PBKDF2-HMAC-SHA256 with a unique 32-byte salt.
        Returns formatted string: `<salt_hex>$<hash_hex>`
        """
        salt = secrets.token_bytes(SALT_BYTES)
        derived_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
        )
        return f"{salt.hex()}${derived_key.hex()}"

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against stored `<salt_hex>$<hash_hex>` in constant time.
        """
        try:
            parts = hashed_password.split("$")
            if len(parts) != 2:
                return False
            salt_hex, stored_hash_hex = parts
            salt = bytes.fromhex(salt_hex)
            stored_hash = bytes.fromhex(stored_hash_hex)

            calculated_hash = hashlib.pbkdf2_hmac(
                "sha256",
                plain_password.encode("utf-8"),
                salt,
                PBKDF2_ITERATIONS,
            )
            return hmac.compare_digest(calculated_hash, stored_hash)
        except Exception as exc:
            logger.warning(f"Password verification error: {exc}")
            return False

    @staticmethod
    def create_access_token(
        subject: str,
        role: UserRole,
        expires_delta: Optional[timedelta] = None,
        custom_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a signed JWT access token.
        Explicitly enforces HS256 algorithm and claims (sub, role, permissions, exp, iat, iss, aud).
        """
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))

        permissions = get_permissions_for_role(role)

        payload: Dict[str, Any] = {
            "sub": subject,
            "role": role.value,
            "permissions": permissions,
            "exp": int(expire.timestamp()),
            "iat": int(now.timestamp()),
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
        }

        if custom_claims:
            payload.update(custom_claims)

        token = jwt.encode(
            payload,
            settings.secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return token

    @staticmethod
    def decode_access_token(token: str) -> TokenPayload:
        """
        Decode and validate JWT access token.
        Rejects tampered tokens, expired tokens, and algorithm confusion.
        """
        try:
            decoded = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.jwt_algorithm],
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "require": ["sub", "role", "permissions", "exp", "iat"],
                },
            )
            return TokenPayload(**decoded)
        except ExpiredSignatureError:
            raise TokenExpiredException()
        except InvalidTokenError as exc:
            logger.warning(f"JWT decode failure: {type(exc).__name__}")
            raise InvalidTokenException()


# Global Singleton Service
auth_service = AuthService()
