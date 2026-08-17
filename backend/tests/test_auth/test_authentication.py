"""
Tests for Password Hashing and JWT Token Verification.
"""

from datetime import timedelta
import pytest
from app.auth.exceptions import (
    CredentialsException,
    InvalidTokenException,
    TokenExpiredException,
)
from app.auth.models import UserRole
from app.auth.service import AuthService


def test_password_hashing_and_verification():
    """Verify PBKDF2-HMAC-SHA256 salted password hashing and timing-safe check."""
    service = AuthService()
    password = "SuperSecretPassword123!"

    hashed = service.hash_password(password)
    assert hashed != password
    assert "$" in hashed

    # Valid password verification
    assert service.verify_password(password, hashed) is True

    # Invalid password verification
    assert service.verify_password("WrongPassword", hashed) is False
    assert service.verify_password("", hashed) is False


def test_jwt_creation_and_decoding():
    """Verify signed JWT token creation and claim extraction."""
    service = AuthService()

    token = service.create_access_token(
        subject="creator_alice",
        role=UserRole.OWNER,
    )

    payload = service.decode_access_token(token)
    assert payload.sub == "creator_alice"
    assert payload.role == "OWNER"
    assert "dashboard.read" in payload.permissions
    assert "system.admin" in payload.permissions


def test_jwt_expired_token_rejection():
    """Verify that expired JWT tokens raise TokenExpiredException."""
    service = AuthService()

    # Create token that expired 10 seconds ago
    token = service.create_access_token(
        subject="creator_bob",
        role=UserRole.OPERATOR,
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(TokenExpiredException):
        service.decode_access_token(token)


def test_jwt_tampered_token_rejection():
    """Verify that tampered or corrupted JWT tokens raise InvalidTokenException."""
    service = AuthService()

    token = service.create_access_token(
        subject="creator_charlie",
        role=UserRole.ADMIN,
    )

    # Tamper with token signature
    tampered_token = token[:-4] + "abcd"

    with pytest.raises(InvalidTokenException):
        service.decode_access_token(tampered_token)
