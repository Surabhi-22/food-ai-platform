"""
Authentication API routes.
POST /auth/register — create vendor account
POST /auth/login — authenticate and return tokens
POST /auth/refresh — rotate access token using refresh token
"""

from fastapi import APIRouter, Depends, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError, BadRequestError
from app.core.redis import check_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models.vendor import Vendor
from app.schemas.auth import (
    AuthResponse,
    TokenRefreshRequest,
    TokenResponse,
    VendorLoginRequest,
    VendorProfileResponse,
    VendorRegisterRequest,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def _build_token_response(vendor: Vendor) -> AuthResponse:
    """Build a complete auth response with tokens and vendor profile."""
    access_token = create_access_token(vendor.id, vendor.email)
    refresh_token = create_refresh_token(vendor.id, vendor.email)
    return AuthResponse(
        tokens=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        ),
        vendor=VendorProfileResponse.model_validate(vendor),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new vendor account",
)
async def register_vendor(
    body: VendorRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Create a new vendor account.
    - Checks for existing email
    - Hashes password with bcrypt
    - Returns JWT access + refresh tokens
    """
    # Rate limit: max 5 registrations per minute per IP
    # Since we don't have IP easily available here without Request object, we'll rate limit by email attempt
    is_allowed, _, _ = await check_rate_limit(f"register:{body.email}", max_requests=5, window_seconds=60)
    if not is_allowed:
        raise BadRequestError("Too many registration attempts. Please try again later.")

    existing = await db.execute(select(Vendor).where(Vendor.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A vendor with this email already exists")

    vendor = Vendor(
        business_name=body.business_name,
        email=body.email,
        password_hash=hash_password(body.password),
    )
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)

    return _build_token_response(vendor)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Authenticate and receive tokens",
)
async def login_vendor(
    body: VendorLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Authenticate a vendor with email and password.
    Returns JWT access + refresh tokens on success.
    """
    is_allowed, _, _ = await check_rate_limit(f"login:{body.email}", max_requests=10, window_seconds=60)
    if not is_allowed:
        raise BadRequestError("Too many login attempts. Please try again later.")

    result = await db.execute(select(Vendor).where(Vendor.email == body.email))
    vendor = result.scalar_one_or_none()

    if vendor is None or not verify_password(body.password, vendor.password_hash):
        raise AuthenticationError("Invalid email or password")

    return _build_token_response(vendor)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
async def refresh_token(
    body: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    The old refresh token is invalidated by issuing a new one.
    """
    try:
        payload = decode_refresh_token(body.refresh_token)
    except JWTError:
        raise AuthenticationError("Invalid or expired refresh token")

    vendor_id = payload.get("sub")
    email = payload.get("email")
    if not vendor_id or not email:
        raise AuthenticationError("Invalid token payload")

    from uuid import UUID
    result = await db.execute(select(Vendor).where(Vendor.id == UUID(vendor_id)))
    vendor = result.scalar_one_or_none()
    if vendor is None:
        raise AuthenticationError("Vendor account not found")

    access_token = create_access_token(vendor.id, vendor.email)
    new_refresh_token = create_refresh_token(vendor.id, vendor.email)

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
