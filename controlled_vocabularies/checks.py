"""System check surfacing a :class:`~controlled_vocabularies.fields.ConceptField` or
:class:`~controlled_vocabularies.fields.ConceptsField` naming a vocabulary that has not been
imported yet.

Registered untagged in :meth:`~controlled_vocabularies.apps.ControlledVocabulariesConfig.ready`
(FR-004, ``research.md`` R3): ``Tags.database`` checks are skipped unless ``--database`` is
passed to ``manage.py check``, which is exactly the bare invocation this check exists to make
useful.
"""

from django.apps import apps
from django.core import checks
from django.db import DatabaseError
from django.utils.translation import gettext_lazy as _

from .fields import ConceptField, ConceptsField
from .models import ConceptScheme

CHECK_ID = "controlled_vocabularies.W001"


def check_concept_field_vocabularies(app_configs, **kwargs):
    """Warn about every named vocabulary absent from the database.

    Walks every installed model for declared ``ConceptField`` and ``ConceptsField`` instances
    and resolves the distinct vocabulary slugs those fields name in **one** query, rather than
    one per field. ``ConceptField.vocabulary`` is always a single slug; ``ConceptsField.vocabulary``
    is a tuple naming zero, one or several (``decisions.md`` D9), so each field contributes every
    slug it names to the flattened distinct set rather than one. A field naming no vocabulary
    (the empty tuple) names nothing that could be missing, so it contributes nothing and is never
    warned about. Where a field names several and only one is absent, the warning names that slug
    rather than the field's whole declaration, so a developer reading ``manage.py check`` learns
    which vocabulary to import.

    The check runs before ``migrate`` (``BaseCommand.requires_system_checks`` defaults to
    ``"__all__"``), so on a fresh install it runs against a database with no tables yet. A
    missing table is not evidence that a vocabulary is absent, so that state — surfaced as
    ``ProgrammingError``, ``OperationalError`` or an unreachable database, all subclasses of
    ``DatabaseError`` — yields no warnings rather than raising (FR-003, ``research.md`` R3).
    """
    fields_with_slugs = [
        (field, (field.vocabulary,) if isinstance(field, ConceptField) else field.vocabulary)
        for model in apps.get_models()
        for field in model._meta.get_fields()
        if isinstance(field, (ConceptField, ConceptsField))
    ]
    if not fields_with_slugs:
        return []

    slugs = {slug for _field, named in fields_with_slugs for slug in named}
    try:
        existing = set(ConceptScheme.objects.filter(slug__in=slugs).values_list("slug", flat=True))
    except DatabaseError:
        return []

    return [
        checks.Warning(
            _("%(model)s.%(field)s names vocabulary '%(vocabulary)s', which has no matching ConceptScheme yet.")
            % {"model": field.model._meta.label, "field": field.name, "vocabulary": slug},
            hint=_("Import this vocabulary, or silence this check with SILENCED_SYSTEM_CHECKS."),
            obj=field,
            id=CHECK_ID,
        )
        for field, named in fields_with_slugs
        for slug in named
        if slug not in existing
    ]
