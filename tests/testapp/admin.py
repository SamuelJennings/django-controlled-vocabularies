"""Admin registrations for the test project's consuming models.

Test-only. The package itself registers nothing in the admin — the curator
interface is a later roadmap item, and ``controlled_vocabularies/admin.py``
exists solely to hold a lazily resolved import.

Every registration here is deliberately bare: no ``ModelAdmin`` in this module
declares anything about a concept field, because the requirement under test is
that declaring the model field is enough. Registrations that *do* declare
something — ``autocomplete_fields``, ``raw_id_fields``, a widget of their own,
``readonly_fields`` — live on their own admin sites in ``tests/test_admin.py``,
so that the default site stays a clean statement of the default behaviour.
"""

from django.contrib import admin

from tests.testapp.models import Outcrop, RockSample, Specimen


@admin.register(Specimen)
class SpecimenAdmin(admin.ModelAdmin):
    """A model carrying a single-value concept field, declaring nothing."""


@admin.register(Outcrop)
class OutcropAdmin(admin.ModelAdmin):
    """A model carrying a multi-value concept field, declaring nothing."""


@admin.register(RockSample)
class RockSampleAdmin(admin.ModelAdmin):
    """A model carrying both kinds of concept field, declaring nothing."""
