"""
FastAPI dependencies for database sessions and authentication.
Provides get_db and get_current_vendor for route injection.
"""

from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, NotFoundError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.vendor import Vendor


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_vendor(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Vendor:
    """
    Extract and validate the JWT from the Authorization header using OAuth2PasswordBearer.
    Returns the authenticated Vendor ORM instance.
    """
    if not token:
        raise AuthenticationError("Token is missing")

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise AuthenticationError("Invalid or expired access token")

    vendor_id_str = payload.get("sub")
    if not vendor_id_str:
        raise AuthenticationError("Token payload missing subject")

    try:
        vendor_id = UUID(vendor_id_str)
    except ValueError:
        raise AuthenticationError("Invalid vendor ID in token")

    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()

    if vendor is None:
        raise AuthenticationError("Vendor account not found or deactivated")

    return vendor
