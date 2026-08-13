"""URL configuration for :mod:`controlled_vocabularies` (T002, FR-002).

The package owns this endpoint's route; the consuming project chooses the address
it is mounted at, with ``include("controlled_vocabularies.urls")`` under a prefix
of its own choosing. The widget resolves the URL by *name*, never by path, so the
prefix is honoured (plan.md A2).
"""

from django.urls import path

from .views import ConceptAutocompleteView

app_name = "controlled_vocabularies"

urlpatterns = [
    path("concepts/", ConceptAutocompleteView.as_view(), name="concept-autocomplete"),
]
