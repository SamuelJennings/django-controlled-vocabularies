"""URL configuration for the demo project (T015, FR-014, FR-015, FR-018)."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("browse/", include("controlled_vocabularies.ui.urls")),
    # django-mvp's mobile footer menu declares a "home" item pointing at a view named "home",
    # and the shell renders that menu on every page. Without a route of that name,
    # django-flex-menus writes a reversal failure to stderr on every render and serves a dead
    # Home button, and the demo's own root address — the first thing anyone opening a server
    # tries — returns 404 (FR-015).
    path(
        "",
        RedirectView.as_view(pattern_name="controlled_vocabularies_ui:vocabulary-list"),
        name="home",
    ),
]
