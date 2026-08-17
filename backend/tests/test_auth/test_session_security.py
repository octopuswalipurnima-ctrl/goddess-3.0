"""
Tests for Session Security, Algorithm Confusion Prevention, and Key Safety.
"""

import jwt
import pytest
from app.auth.exceptions import InvalidTokenException
from app.auth.models import UserRole
from app.auth.service import AuthService
from app.core.config import settings


def test_reject_none_algorithm_jwt():
    """Verify that tokens signed with the 'none' algorithm are strictly rejected."""
    service = AuthService()

    # Craft an unsigned token with 'none' algorithm
    unsigned_payload = {
        "sub": "attacker",
        "role": "OWNER",
        "permissions": ["system.admin"],
        "exp": 9999999999,
        "iat": 1000000000,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }

    # Attempt to decode raw token signed with None
    fake_token = jwt.encode(unsigned_payload, key="", algorithm="none")

    with pytest.raises(InvalidTokenException):
        service.decode_access_token(fake_token)


def test_reject_invalid_issuer_or_audience():
    """Verify tokens from unauthorized issuers or audiences are rejected."""
    service = AuthService()

    # Craft token with wrong issuer
    invalid_token = jwt.encode(
        {
            "sub": "impostor",
            "role": "OWNER",
            "permissions": ["system.admin"],
            "exp": 9999999999,
            "iat": 1000000000,
            "iss": "rogue-issuer",
            "aud": settings.jwt_audience,
        },
        settings.secret_key,
        algorithm="HS256",
    )

    with pytest.raises(InvalidTokenException):
        service.decode_access_token(invalid_token)
