"""Registers the vocabulary model with the demo's admin site (T015, FR-014, User Story 3).

The package itself registers nothing — a curator interface is a later feature, and a package
that registered its own models would take that decision away from every project installing it
(``controlled_vocabularies/admin.py``). But the demo's own story promises a reader can "add a
vocabulary by hand and watch it appear on the list", and ``demo/urls.py`` mounts the admin for
exactly that. Registering it here, in the demo project rather than in the package, is what makes
the documented step work without deciding anything on a real project's behalf.

Deliberately not registered: ``Concept``. A hand-added vocabulary shows a concept count of zero,
which is the truthful entry for one, and seeded content already demonstrates a non-zero count.
"""

from django.contrib import admin

from controlled_vocabularies.models import ConceptScheme


@admin.register(ConceptScheme)
class ConceptSchemeAdmin(admin.ModelAdmin):
    """The four fields the list page reads, and nothing else.

    ``slug`` and ``slug_is_manual`` are left off the form because a scheme derives its slug from
    its name on every save while the flag is unset. ``slug`` is a required, unique field with no
    ``blank=True``, so a form carrying it would refuse a submission that left it empty — the
    admin would demand a value the model is about to compute.
    """

    fields = ("name", "description", "default_language", "static_uri")
    list_display = ("name", "slug", "static_uri")
    search_fields = ("name", "description")
