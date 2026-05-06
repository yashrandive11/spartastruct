"""Django ORM models for the blog application."""

from __future__ import annotations

from django.db import models


class Author(models.Model):
    """A blog post author."""

    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    bio = models.TextField(blank=True)

    class Meta:
        """Model metadata."""

        ordering = ["name"]

    def __str__(self) -> str:
        """Return string representation."""
        return self.name


class Article(models.Model):
    """A published article."""

    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name="articles")
    tags = models.ManyToManyField("Tag", blank=True)
    published = models.BooleanField(default=False)

    def __str__(self) -> str:
        """Return string representation."""
        return self.title


class Tag(models.Model):
    """A content tag."""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self) -> str:
        """Return string representation."""
        return self.name
