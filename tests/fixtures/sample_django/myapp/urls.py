"""URL configuration for the blog application."""

from __future__ import annotations

from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("articles/", views.article_list, name="article-list"),
    path("articles/<int:article_id>/", views.article_detail, name="article-detail"),
    path("authors/<int:author_id>/", views.author_detail, name="author-detail"),
]
