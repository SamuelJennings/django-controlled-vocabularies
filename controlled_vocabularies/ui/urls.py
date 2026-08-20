"""URL configuration for the opt-in vocabulary-browsing front end (013-find-a-vocabulary T006).

``app_name`` is distinct from the core app's own ``controlled_vocabularies`` namespace, so a
project can mount both without either shadowing the other's reverses (plan.md Key design
decisions #4). Views are imported relatively, staying inside this app's own package.
"""

from django.urls import path

from .views import VocabularyListView

app_name = "controlled_vocabularies_ui"

urlpatterns = [
    path("", VocabularyListView.as_view(), name="vocabulary-list"),
]
