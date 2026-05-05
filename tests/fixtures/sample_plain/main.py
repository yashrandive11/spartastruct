"""Entry point for the shape analysis tool."""

from __future__ import annotations

from utils import create_default_shapes, summarize_registry


def run() -> None:
    """Execute the main application logic."""
    registry = create_default_shapes()
    summary = summarize_registry(registry)
    print(summary)


if __name__ == "__main__":
    run()
