"""URL configuration for the opt-in vocabulary-browsing front end (013-find-a-vocabulary T006).

``app_name`` is distinct from the core app's own ``controlled_vocabularies`` namespace, so a
project can mount both without either shadowing the other's reverses (plan.md Key design
decisions #4). Views are imported relatively, staying inside this app's own package.
"""

from django.urls import path

from .views import VocabularyDetailView, VocabularyListView

app_name = "controlled_vocabularies_ui"

urlpatterns = [
    path("", VocabularyListView.as_view(), name="vocabulary-list"),
    # <str:slug>, not <slug:slug>: the models slugify with allow_unicode=True, and Django's
    # slug converter matches ASCII only, so a vocabulary named in a non-Latin script would
    # 404 on its own page under the obvious converter. Mounted after the list route so
    # nothing here shadows a route this app adds later.
    path("<str:slug>/", VocabularyDetailView.as_view(), name="vocabulary-detail"),
]
