"""Business logic layer for user operations."""

from __future__ import annotations

from repositories.user_repo import UserRepository


class UserService:
    """Service layer for user-related business logic."""

    def __init__(self) -> None:
        """Initialize with a UserRepository."""
        self._repo = UserRepository()

    def get_user(self, user_id: int) -> dict | None:
        """Retrieve a user by ID, returning None if not found."""
        return self._repo.find_by_id(user_id)

    def create_user(self, username: str, email: str) -> dict:
        """Create a new user and return the created record."""
        return self._repo.create(username=username, email=email)

    def list_users(self) -> list[dict]:
        """Return all users."""
        return self._repo.find_all()
