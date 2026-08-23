"""Root URL configuration for the test project (011 T002, 012 T001, 013 T006).

``controlled_vocabularies.urls`` is included under a non-empty prefix chosen by
this test project, not at the root, so a hard-coded path in the widget would be
caught rather than accidentally matching. ``controlled_vocabularies.ui.urls`` is
mounted the same way, under its own prefix and its own namespace (plan.md Key
design decisions #4), so a hard-coded path in the ui app would be caught too.

The browsing routes are mounted at the path
``CONTROLLED_VOCABULARIES_BASE_URI`` names (014 T004): a vocabulary's identifier
is composed from that setting rather than reversed, so the two disagreeing means
a locally held vocabulary's identifier leads nowhere. That is what
``controlled_vocabularies.ui.W001`` reports, and a test project of all things
should not be the misconfiguration its own check exists to find.

The default admin site is mounted for the admin suite. A consuming project is not
required to mount one — ``tests/settings_no_admin.py`` is the configuration that
proves it.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("widget/", include("controlled_vocabularies.urls")),
    path("vocabularies/", include("controlled_vocabularies.ui.urls")),
]
