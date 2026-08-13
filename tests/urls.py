"""Root URL configuration for the test project (T002).

``controlled_vocabularies.urls`` is included under a non-empty prefix chosen by
this test project, not at the root, so a hard-coded path in the widget would be
caught rather than accidentally matching.
"""

from django.urls import include, path

urlpatterns = [
    path("vocabularies/", include("controlled_vocabularies.urls")),
]
