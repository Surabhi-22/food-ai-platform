"""
JWT token management and password hashing utilities.
Uses python-jose for JWT and passlib with bcrypt for password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# ── Password Hashing ────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Tokens ──────────────────────────────────────────────────────────────

def _create_token(data: dict[str, Any], expires_delta: timedelta) -> str:
    """Create a signed JWT with the given payload and expiry."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(vendor_id: UUID, email: str, role: str = "vendor") -> str:
    """Create a short-lived access token."""
    return _create_token(
        data={"sub": str(vendor_id), "email": email, "role": role, "type": "access"},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(vendor_id: UUID, email: str, role: str = "vendor") -> str:
    """Create a long-lived refresh token."""
    return _create_token(
        data={"sub": str(vendor_id), "email": email, "role": role, "type": "refresh"},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.
    Raises JWTError if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        raise


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode an access token, verifying it is not a refresh token."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Token is not an access token")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode a refresh token, verifying it is not an access token."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Token is not a refresh token")
    return payload
