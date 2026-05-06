"""Geometric shape classes demonstrating ABC, dataclasses, and inheritance."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass


class Shape(ABC):
    """Abstract base class for all geometric shapes."""

    color: str = "white"

    @abstractmethod
    def area(self) -> float:
        """Calculate the area of the shape."""
        ...

    @abstractmethod
    def perimeter(self) -> float:
        """Calculate the perimeter of the shape."""
        ...

    def describe(self) -> str:
        """Return a human-readable description of the shape."""
        return f"{self.__class__.__name__}(area={self.area():.2f})"


@dataclass
class Circle(Shape):
    """A circle defined by its radius."""

    radius: float
    color: str = "red"

    def area(self) -> float:
        """Calculate circle area."""
        return math.pi * self.radius**2

    def perimeter(self) -> float:
        """Calculate circle circumference."""
        return 2 * math.pi * self.radius


@dataclass
class Rectangle(Shape):
    """A rectangle defined by width and height."""

    width: float
    height: float
    color: str = "blue"

    def area(self) -> float:
        """Calculate rectangle area."""
        return self.width * self.height

    def perimeter(self) -> float:
        """Calculate rectangle perimeter."""
        return 2 * (self.width + self.height)

    def is_square(self) -> bool:
        """Return True if width equals height."""
        return self.width == self.height


class ShapeRegistry:
    """Registry for tracking shape instances."""

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._shapes: list[Shape] = []

    def register(self, shape: Shape) -> None:
        """Add a shape to the registry."""
        self._shapes.append(shape)

    def total_area(self) -> float:
        """Sum the areas of all registered shapes."""
        return sum(s.area() for s in self._shapes)

    def __len__(self) -> int:
        """Return number of registered shapes."""
        return len(self._shapes)
