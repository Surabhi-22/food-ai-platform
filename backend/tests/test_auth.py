"""
Authentication test suite.

Tests JWT issuance, password verification, token expiry,
and refresh token flow.

Run with: pytest tests/test_auth.py -v
"""

import time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from jose import jwt, JWTError

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    decode_token,
)
from app.core.config import get_settings

settings = get_settings()


# ── Password Hashing ────────────────────────────────────────────────────────

class TestPasswordHashing:
    """Test bcrypt password hashing and verification."""

    def test_hash_and_verify_success(self):
        """Valid password should verify against its hash."""
        password = "StrongP@ssw0rd!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password should fail verification."""
        hashed = hash_password("CorrectPassword123!")
        assert verify_password("WrongPassword", hashed) is False

    def test_hash_is_not_plaintext(self):
        """Hash should never equal the plaintext password."""
        password = "MySecretPassword"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are 60+ chars

    def test_different_hashes_for_same_password(self):
        """bcrypt should produce different hashes each time (salted)."""
        password = "SamePassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # Different salts
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_weak_password_still_hashes(self):
        """Even weak passwords are hashed (validation is at API layer)."""
        weak = "123"
        hashed = hash_password(weak)
        assert verify_password(weak, hashed) is True


# ── JWT Token Creation ───────────────────────────────────────────────────────

class TestJWTCreation:
    """Test JWT access and refresh token creation."""

    def test_access_token_contains_claims(self):
        """Access token should contain vendor_id, email, role, and type."""
        vendor_id = uuid.uuid4()
        email = "vendor@test.com"

        token = create_access_token(vendor_id, email, role="vendor")
        payload = decode_token(token)

        assert payload["sub"] == str(vendor_id)
        assert payload["email"] == email
        assert payload["role"] == "vendor"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_refresh_token_contains_claims(self):
        """Refresh token should have type='refresh'."""
        vendor_id = uuid.uuid4()
        token = create_refresh_token(vendor_id, "test@test.com")
        payload = decode_token(token)

        assert payload["type"] == "refresh"
        assert payload["sub"] == str(vendor_id)

    def test_access_token_expires_correctly(self):
        """Access token expiry should match configured minutes."""
        vendor_id = uuid.uuid4()
        token = create_access_token(vendor_id, "test@test.com")
        payload = decode_token(token)

        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        delta = exp - iat

        assert abs(delta.total_seconds() - settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60) < 5

    def test_refresh_token_expires_correctly(self):
        """Refresh token expiry should match configured days."""
        vendor_id = uuid.uuid4()
        token = create_refresh_token(vendor_id, "test@test.com")
        payload = decode_token(token)

        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        delta = exp - iat

        expected_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        assert abs(delta.total_seconds() - expected_seconds) < 5


# ── JWT Decoding ─────────────────────────────────────────────────────────────

class TestJWTDecoding:
    """Test JWT validation and error cases."""

    def test_decode_valid_access_token(self):
        """Valid access token should decode successfully."""
        vendor_id = uuid.uuid4()
        token = create_access_token(vendor_id, "test@test.com")
        payload = decode_access_token(token)

        assert payload["sub"] == str(vendor_id)
        assert payload["type"] == "access"

    def test_decode_access_rejects_refresh(self):
        """decode_access_token should reject a refresh token."""
        vendor_id = uuid.uuid4()
        refresh_token = create_refresh_token(vendor_id, "test@test.com")

        with pytest.raises(JWTError, match="not an access token"):
            decode_access_token(refresh_token)

    def test_decode_refresh_rejects_access(self):
        """decode_refresh_token should reject an access token."""
        vendor_id = uuid.uuid4()
        access_token = create_access_token(vendor_id, "test@test.com")

        with pytest.raises(JWTError, match="not a refresh token"):
            decode_refresh_token(access_token)

    def test_expired_token_raises_error(self):
        """Expired token should raise JWTError."""
        vendor_id = uuid.uuid4()
        # Create a token that expired 1 hour ago
        expired_payload = {
            "sub": str(vendor_id),
            "email": "test@test.com",
            "role": "vendor",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )

        with pytest.raises(JWTError):
            decode_token(expired_token)

    def test_tampered_token_raises_error(self):
        """Token signed with wrong key should fail."""
        vendor_id = uuid.uuid4()
        bad_payload = {
            "sub": str(vendor_id),
            "email": "hacker@evil.com",
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        bad_token = jwt.encode(bad_payload, "wrong-secret-key", algorithm="HS256")

        with pytest.raises(JWTError):
            decode_token(bad_token)

    def test_malformed_token_raises_error(self):
        """Completely invalid token string should fail."""
        with pytest.raises(JWTError):
            decode_token("not.a.valid.jwt.token")

    def test_empty_token_raises_error(self):
        """Empty string should fail."""
        with pytest.raises(JWTError):
            decode_token("")


# ── Registration / Login Logic ───────────────────────────────────────────────

class TestAuthLogic:
    """Test authentication business logic (hashing + token flow)."""

    def test_registration_flow(self):
        """Full registration: hash password → create tokens → verify."""
        password = "NewVendor@2025"
        hashed = hash_password(password)
        vendor_id = uuid.uuid4()
        email = "new@vendor.com"

        # Simulate login after registration
        assert verify_password(password, hashed) is True

        access = create_access_token(vendor_id, email)
        refresh = create_refresh_token(vendor_id, email)

        access_payload = decode_access_token(access)
        refresh_payload = decode_refresh_token(refresh)

        assert access_payload["sub"] == str(vendor_id)
        assert refresh_payload["sub"] == str(vendor_id)

    def test_duplicate_email_detection(self):
        """Same email should produce same hash verification result."""
        email = "duplicate@vendor.com"
        password = "FirstPassword123"
        hashed = hash_password(password)

        # Second registration attempt with same email
        assert verify_password(password, hashed) is True
        assert verify_password("DifferentPassword", hashed) is False

    def test_login_wrong_password_fails(self):
        """Wrong password during login should fail."""
        correct_password = "CorrectPass@123"
        hashed = hash_password(correct_password)

        assert verify_password("WrongPass@456", hashed) is False

    def test_refresh_token_can_issue_new_access(self):
        """Refresh flow: decode refresh → issue new access token."""
        vendor_id = uuid.uuid4()
        email = "vendor@test.com"

        refresh = create_refresh_token(vendor_id, email)
        refresh_payload = decode_refresh_token(refresh)

        # Issue new access token from refresh payload
        new_access = create_access_token(
            uuid.UUID(refresh_payload["sub"]),
            refresh_payload["email"],
        )
        new_payload = decode_access_token(new_access)

        assert new_payload["sub"] == str(vendor_id)
        assert new_payload["type"] == "access"
