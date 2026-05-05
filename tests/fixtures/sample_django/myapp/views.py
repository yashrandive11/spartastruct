"""Function-based views for the blog application."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse


def index(request: HttpRequest) -> HttpResponse:
    """Render the blog index page."""
    return HttpResponse("<h1>Blog</h1>")


def article_list(request: HttpRequest) -> JsonResponse:
    """Return a JSON list of all published articles."""
    return JsonResponse({"articles": []})


def article_detail(request: HttpRequest, article_id: int) -> JsonResponse:
    """Return a single article by ID."""
    return JsonResponse({"id": article_id, "title": "Example"})


def author_detail(request: HttpRequest, author_id: int) -> JsonResponse:
    """Return a single author by ID."""
    return JsonResponse({"id": author_id})
