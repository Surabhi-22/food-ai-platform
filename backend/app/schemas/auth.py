"""Authentication request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class VendorRegisterRequest(BaseModel):
    """Request body for vendor registration."""
    business_name: str = Field(..., min_length=2, max_length=255, examples=["Tasty Bites Kitchen"])
    email: EmailStr = Field(..., examples=["vendor@example.com"])
    password: str = Field(..., min_length=8, max_length=128, examples=["SecurePass123!"])


class VendorLoginRequest(BaseModel):
    """Request body for vendor login."""
    email: EmailStr = Field(..., examples=["vendor@example.com"])
    password: str = Field(..., examples=["SecurePass123!"])


class TokenRefreshRequest(BaseModel):
    """Request body for token refresh."""
    refresh_token: str


class TokenResponse(BaseModel):
    """Response containing JWT tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class VendorProfileResponse(BaseModel):
    """Vendor profile data returned after auth."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    business_name: str
    email: str
    logo_url: str | None = None
    created_at: datetime


class AuthResponse(BaseModel):
    """Complete auth response with tokens and vendor profile."""
    tokens: TokenResponse
    vendor: VendorProfileResponse
