"""Common Pydantic schemas used across the application."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    environment: str


class PaginationParams(BaseModel):
    """Pagination query parameters."""
    page: int = 1
    page_size: int = 20

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    model_config = ConfigDict(from_attributes=True)

    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str


class ErrorDetail(BaseModel):
    """Structured error detail."""
    code: str
    detail: str | list[dict]


class ErrorResponse(BaseModel):
    """Structured error response."""
    success: bool = False
    error: ErrorDetail
