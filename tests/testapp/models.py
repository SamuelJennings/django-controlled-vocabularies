"""Models exercising :class:`~controlled_vocabularies.fields.ConceptField`'s
public API (T002).

Three models, each carrying the field a different way US-1 through US-5 need
to test against:

- :class:`Specimen` — a required ``ConceptField``.
- :class:`Sample` — an optional ``ConceptField`` with a ``related_name``.
- :class:`Artifact` — an optional ``ConceptField`` on a model that already
  defines ``get_mineral_label`` itself, so US-5's ``contribute_to_class()``
  collision guard (T011) has a real pre-existing definition to leave alone
  rather than a synthetic one.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies.fields import ConceptField


class Specimen(models.Model):
    """Carries a required concept from the "rock-type" vocabulary."""

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
        help_text=_("The specimen's catalogue name."),
    )
    rock_type = ConceptField(
        vocabulary="rock-type",
        verbose_name=_("rock type"),
        help_text=_("The rock type this specimen is classified as."),
    )

    def __str__(self) -> str:
        return self.name


class Sample(models.Model):
    """Carries an optional concept from the "mineral" vocabulary, with a
    reverse accessor (``mineral.samples``)."""

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
        help_text=_("The sample's catalogue name."),
    )
    mineral = ConceptField(
        vocabulary="mineral",
        null=True,
        blank=True,
        related_name="samples",
        verbose_name=_("mineral"),
        help_text=_("The mineral this sample is classified as, if known."),
    )

    def __str__(self) -> str:
        return self.name


class Artifact(models.Model):
    """Carries an optional concept from the "mineral" vocabulary, on a model
    that already defines ``get_mineral_label()`` — the name US-5's
    ``contribute_to_class()`` (T011) would generate for a field named
    ``mineral``. The collision guard is tested against this real, pre-existing
    definition rather than a synthetic one.
    """

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
        help_text=_("The artifact's catalogue name."),
    )
    mineral = ConceptField(
        vocabulary="mineral",
        null=True,
        blank=True,
        verbose_name=_("mineral"),
        help_text=_("The mineral this artifact is classified as, if known."),
    )

    def __str__(self) -> str:
        return self.name

    def get_mineral_label(self) -> str:
        """Pre-existing — must survive T011's ``contribute_to_class()`` guard untouched."""
        return "this artifact's own label, not the field's"
