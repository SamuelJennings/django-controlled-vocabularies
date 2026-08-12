"""Models exercising :class:`~controlled_vocabularies.fields.ConceptField`'s
and :class:`~controlled_vocabularies.fields.ConceptsField`'s public APIs.

Three models carry ``ConceptField`` (FS-009, T002), a different way US-1
through US-5 there need to test against:

- :class:`Specimen` — a required ``ConceptField``.
- :class:`Sample` — an optional ``ConceptField`` with a ``related_name``.
- :class:`Artifact` — an optional ``ConceptField`` on a model that already
  defines ``get_mineral_label`` itself, so US-5's ``contribute_to_class()``
  collision guard (T011) has a real pre-existing definition to leave alone
  rather than a synthetic one.

:class:`Deposit` and :class:`Survey` carry ``ConceptsField`` (FS-010 T003) —
the minimum needed to prove the generated membership model against a real
declaration: one required field, and two required fields declared
``related_name="+"`` on one model, so the hidden related_name rewrite
``contribute_to_class`` replicates (T003) has two live fields that would
otherwise clash. FS-010 T001 adds the rest of the consuming models this
feature needs.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies.fields import ConceptField, ConceptsField


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


class Deposit(models.Model):
    """Carries a required ``ConceptsField`` against the "rock-type" vocabulary
    (T003, T009's enforced half)."""

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
        help_text=_("The deposit's catalogue name."),
    )
    rock_types = ConceptsField(
        vocabulary="rock-type",
        verbose_name=_("rock types"),
        help_text=_("The rock types present at this deposit."),
    )

    def __str__(self) -> str:
        return self.name


class Survey(models.Model):
    """Carries two required ``ConceptsField``s against the same vocabulary
    (T003, T009): one required field enforced and the other silently skipped
    is the failure T009's enumeration case exists to catch, and it needs two
    of them on one model to be visible at all. Both declare
    ``related_name="+"`` so T003's hidden related_name rewrite has two live
    fields that would otherwise clash to prove itself against."""

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
        help_text=_("The survey's catalogue name."),
    )
    primary_minerals = ConceptsField(
        vocabulary="mineral",
        related_name="+",
        verbose_name=_("primary minerals"),
        help_text=_("The minerals this survey primarily targets."),
    )
    secondary_minerals = ConceptsField(
        vocabulary="mineral",
        related_name="+",
        verbose_name=_("secondary minerals"),
        help_text=_("The minerals this survey secondarily targets."),
    )

    def __str__(self) -> str:
        return self.name
