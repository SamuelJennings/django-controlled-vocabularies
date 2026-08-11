"""System check surfacing a :class:`~controlled_vocabularies.fields.ConceptField`
naming a vocabulary that has not been imported yet.

Registered untagged in :meth:`~controlled_vocabularies.apps.ControlledVocabulariesConfig.ready`
(FR-004, ``research.md`` R3): ``Tags.database`` checks are skipped unless ``--database`` is
passed to ``manage.py check``, which is exactly the bare invocation this check exists to make
useful.
"""

from django.apps import apps
from django.core import checks
from django.utils.translation import gettext_lazy as _

from .fields import ConceptField
from .models import ConceptScheme

CHECK_ID = "controlled_vocabularies.W001"


def check_concept_field_vocabularies(app_configs, **kwargs):
    """Warn about every :class:`ConceptField` naming a vocabulary absent from the database.

    Walks every installed model for declared ``ConceptField`` instances and resolves the
    distinct vocabulary slugs those fields name in **one** query, rather than one per field.
    """
    concept_fields = [
        field for model in apps.get_models() for field in model._meta.get_fields() if isinstance(field, ConceptField)
    ]
    if not concept_fields:
        return []

    slugs = {field.vocabulary for field in concept_fields}
    existing = set(ConceptScheme.objects.filter(slug__in=slugs).values_list("slug", flat=True))

    return [
        checks.Warning(
            _("%(model)s.%(field)s names vocabulary '%(vocabulary)s', which has no matching ConceptScheme yet.")
            % {"model": field.model._meta.label, "field": field.name, "vocabulary": field.vocabulary},
            hint=_("Import this vocabulary, or silence this check with SILENCED_SYSTEM_CHECKS."),
            obj=field,
            id=CHECK_ID,
        )
        for field in concept_fields
        if field.vocabulary not in existing
    ]
