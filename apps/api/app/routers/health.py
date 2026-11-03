"""
Health check router.

GET /health — used by load balancers, CI, and the frontend to confirm the API is alive.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["meta"])


class HealthResponse(BaseModel):
    """Response schema for the health endpoint."""

    status: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns `ok` if the API is running.",
)
async def health() -> HealthResponse:
    """Return a simple health status."""
    return HealthResponse(status="ok", version="0.1.0")
