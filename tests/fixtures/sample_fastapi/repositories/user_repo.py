"""Data access layer for user operations."""

from __future__ import annotations


class UserRepository:
    """In-memory repository for user data (demo only)."""

    def __init__(self) -> None:
        """Initialize with empty storage."""
        self._store: dict[int, dict] = {}
        self._next_id: int = 1

    def find_by_id(self, user_id: int) -> dict | None:
        """Return user dict by ID, or None."""
        return self._store.get(user_id)

    def create(self, username: str, email: str) -> dict:
        """Insert a new user and return it."""
        record = {"id": self._next_id, "username": username, "email": email}
        self._store[self._next_id] = record
        self._next_id += 1
        return record

    def find_all(self) -> list[dict]:
        """Return all users."""
        return list(self._store.values())
