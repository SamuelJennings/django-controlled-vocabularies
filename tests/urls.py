"""Root URL configuration for the test project (011 T002, 012 T001, 013 T006).

``controlled_vocabularies.urls`` is included under a non-empty prefix chosen by
this test project, not at the root, so a hard-coded path in the widget would be
caught rather than accidentally matching. ``controlled_vocabularies.ui.urls`` is
mounted the same way, under its own prefix and its own namespace (plan.md Key
design decisions #4), so a hard-coded path in the ui app would be caught too.

The default admin site is mounted for the admin suite. A consuming project is not
required to mount one — ``tests/settings_no_admin.py`` is the configuration that
proves it.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("vocabularies/", include("controlled_vocabularies.urls")),
    path("browse/", include("controlled_vocabularies.ui.urls")),
]
