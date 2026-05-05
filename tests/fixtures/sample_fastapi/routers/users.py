"""User-related API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from services.user_service import UserService

router = APIRouter()
_service = UserService()


@router.get("/{user_id}")
async def get_user(user_id: int) -> dict:
    """Retrieve a user by ID."""
    user = _service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/")
async def create_user(username: str, email: str) -> dict:
    """Create a new user."""
    return _service.create_user(username, email)


@router.get("/")
async def list_users() -> list:
    """List all users."""
    return _service.list_users()
