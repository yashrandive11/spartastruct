"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from routers import users

app = FastAPI(title="Sample API", version="1.0.0")
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/health")
async def health_check() -> dict:
    """Return API health status."""
    return {"status": "ok"}
