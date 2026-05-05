"""Utility functions for shape calculations."""

from __future__ import annotations

from shapes import Circle, Rectangle, ShapeRegistry


def create_default_shapes() -> ShapeRegistry:
    """Create a registry populated with default shapes."""
    registry = ShapeRegistry()
    registry.register(Circle(radius=5.0))
    registry.register(Rectangle(width=4.0, height=6.0))
    return registry


def scale_shape_area(shape_area: float, factor: float) -> float:
    """Scale an area value by a given factor."""
    return shape_area * factor


def format_area(area: float, unit: str = "sq units") -> str:
    """Format an area value as a human-readable string."""
    return f"{area:.4f} {unit}"


def summarize_registry(registry: ShapeRegistry) -> str:
    """Return a summary string for a shape registry."""
    total = registry.total_area()
    count = len(registry)
    formatted = format_area(total)
    return f"{count} shapes, total area: {formatted}"
