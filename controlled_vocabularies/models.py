"""Models for controlled_vocabularies.

The relational models are the source of truth for a vocabulary and its concepts.
In this slice a vocabulary is a :class:`ConceptScheme`; its identifier (URI) is
computed from a configured base address and the slug, never stored (research R1).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies import conf


class ConceptScheme(models.Model):
    """A controlled vocabulary — a named container for concepts (a SKOS concept scheme).

    The ``slug`` is derived from ``name`` on every save (dynamic while unpublished,
    research R5) and is unique app-wide. The ``uri`` is composed on read.
    """

    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
        help_text=_("The human-readable name of the vocabulary. Its slug is derived automatically from this."),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
        help_text=_("Optional explanation of what this vocabulary covers."),
    )
    slug = models.SlugField(
        max_length=255,
        unique=True,
        allow_unicode=True,
        verbose_name=_("slug"),
        help_text=_(
            "A URL-safe identifier derived automatically from the name. A slug must be unique across all vocabularies."
        ),
    )

    class Meta:
        verbose_name = _("vocabulary")
        verbose_name_plural = _("vocabularies")

    def __str__(self) -> str:
        return self.name

    @property
    def uri(self) -> str:
        """The scheme's URI: the configured base address plus its slug."""
        return f"{conf.get_base_uri()}/{self.slug}"

    @property
    def effective_default_language(self) -> str:
        """The language whose preferred label anchors this vocabulary's concepts.

        Falls back to the application's configured default language
        (``settings.LANGUAGE_CODE``). A per-vocabulary override is a later story
        (US-4); until then every vocabulary anchors identity in the app default.
        """
        return settings.LANGUAGE_CODE

    def save(self, *args, **kwargs):
        """Derive the slug from ``name`` and refuse an empty or colliding slug."""
        self.slug = slugify(self.name, allow_unicode=True)
        if not self.slug:
            raise ValidationError({"name": _("Name must produce a non-empty slug.")})
        # Refuse a slug that collides with another scheme rather than minting a
        # duplicate identifier or silently auto-suffixing it (research R4).
        if ConceptScheme.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError(
                {
                    "slug": ValidationError(
                        _("A vocabulary with the slug '%(slug)s' already exists."),
                        params={"slug": self.slug},
                    )
                }
            )
        super().save(*args, **kwargs)


class ConceptManager(models.Manager["Concept"]):
    """Default manager for :class:`Concept`, adding URI-based lookup.

    Subclasses the standard manager so ``Concept.objects`` keeps all default
    behaviour and gains :meth:`get_by_uri`.
    """

    def get_by_uri(self, uri: str) -> "Concept":
        """Return the concept identified by ``uri``.

        Requires ``uri`` to sit under the configured base address, strips that
        base, splits the remainder into its ``scheme-slug/concept-slug`` parts
        and resolves the concept by scheme slug and slug. The URI — not the
        primary key — is the identity (Article IX); a URI outside the base or a
        well-formed URI with no matching concept raises
        :class:`Concept.DoesNotExist`, the standard ORM lookup behaviour.
        Unicode slugs resolve the same as ASCII ones.
        """
        base = conf.get_base_uri()
        if not uri.startswith(base):
            raise self.model.DoesNotExist(f"No concept matches the URI {uri!r}.")
        remainder = uri.removeprefix(base).strip("/")
        parts = remainder.split("/")
        if len(parts) != 2:
            raise self.model.DoesNotExist(f"No concept matches the URI {uri!r}.")
        scheme_slug, concept_slug = parts
        return self.get(scheme__slug=scheme_slug, slug=concept_slug)


class Concept(models.Model):
    """A single term within a vocabulary (a SKOS concept).

    The ``slug`` is derived from ``label`` on every save (dynamic while
    unpublished, research R5) and is unique within its scheme — the same slug
    may recur in a different scheme. The ``uri`` is composed on read from the
    owning scheme's URI (research R1). ``label`` is the default-language
    preferred label; richer multi-label support arrives with a later story.
    """

    scheme = models.ForeignKey(
        ConceptScheme,
        on_delete=models.CASCADE,
        related_name="concepts",
        verbose_name=_("vocabulary"),
        help_text=_("The vocabulary this concept belongs to."),
    )
    label = models.CharField(
        max_length=255,
        verbose_name=_("preferred label"),
        help_text=_(
            "The preferred label in the vocabulary's effective default language. "
            "It is the concept's identity anchor: the slug is derived from it, and "
            "preferred labels in other languages are held as separate labels."
        ),
    )
    slug = models.SlugField(
        max_length=255,
        allow_unicode=True,
        verbose_name=_("slug"),
        help_text=_(
            "A URL-safe identifier derived automatically from the label. A slug must be unique within a given vocabulary."
        ),
    )

    objects = ConceptManager()

    class Meta:
        verbose_name = _("concept")
        verbose_name_plural = _("concepts")
        constraints = [
            models.UniqueConstraint(fields=["scheme", "slug"], name="unique_concept_slug_per_scheme"),
        ]

    def __str__(self) -> str:
        return self.label

    @property
    def uri(self) -> str:
        """The concept's URI: its scheme's URI plus its slug."""
        return f"{self.scheme.uri}/{self.slug}"

    def save(self, *args, **kwargs):
        """Derive the slug from ``label`` and refuse an empty or colliding slug."""
        self.slug = slugify(self.label, allow_unicode=True)
        if not self.slug:
            raise ValidationError({"label": _("Label must produce a non-empty slug.")})
        # Refuse a slug that collides with another concept in the same scheme
        # rather than minting a duplicate identifier or silently auto-suffixing
        # it (research R4). The UniqueConstraint is the integrity backstop.
        if Concept.objects.filter(scheme=self.scheme, slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError(
                {
                    "slug": ValidationError(
                        _("A concept with the slug '%(slug)s' already exists in this vocabulary."),
                        params={"slug": self.slug},
                    )
                }
            )
        super().save(*args, **kwargs)

    def preferred_label(self, language: str | None = None) -> str | None:
        """Return this concept's preferred label in ``language``.

        ``language=None`` means the scheme's effective default language, whose
        preferred label is :attr:`label` itself. For any other language the
        preferred label is the matching :class:`ConceptLabel` row's text, or
        ``None`` when the concept has no preferred label in that language (FR-007).
        """
        if language is None or language == self.scheme.effective_default_language:
            return self.label
        row = self.labels.filter(language=language, kind=ConceptLabel.Kind.PREFERRED).first()
        return row.text if row is not None else None

    def alt_labels(self, language: str) -> list[str]:
        """Return this concept's alternative label texts in ``language``.

        A concept may carry any number of alternative labels per language (FR-005);
        this returns just those in ``language``, ordered as the model orders labels,
        and an empty list when the concept has none in that language (FR-007).
        """
        return list(
            self.labels.filter(language=language, kind=ConceptLabel.Kind.ALTERNATIVE).values_list("text", flat=True)
        )

    def hidden_labels(self, language: str) -> list[str]:
        """Return this concept's hidden label texts in ``language``.

        Hidden labels — misspellings and search-only variants — are held separately
        from alternatives; like them they may occur any number of times per language
        (FR-005) and read back an empty list when absent (FR-007).
        """
        return list(self.labels.filter(language=language, kind=ConceptLabel.Kind.HIDDEN).values_list("text", flat=True))

    def add_label(self, language: str, kind: str, text: str) -> "ConceptLabel":
        """Add a label of any :class:`ConceptLabel.Kind` and return the created row.

        The row is validated before it is saved: a second preferred label in a
        language that already has one is refused (FR-001), as is a preferred label in
        the effective default language (that one lives on :attr:`label`). Alternative
        and hidden labels carry no such uniqueness — any number may share a language
        (FR-005). Adding a label never touches this concept's slug or URI (FR-004).
        """
        row = ConceptLabel(concept=self, language=language, kind=kind, text=text)
        row.full_clean()
        row.save()
        return row

    def definition(self, language: str) -> str | None:
        """Return this concept's first definition in ``language``.

        The definition is the primary documentary note (SKOS ``definition``). A
        concept may hold more than one per language (FR-006); this returns the first
        by the model's ordering, or ``None`` when it has none in that language (FR-007).
        """
        row = self.concept_notes.filter(language=language, kind=ConceptNote.Kind.DEFINITION).first()
        return row.value if row is not None else None

    def notes(self, language: str, kind: str | None = None) -> list[str]:
        """Return this concept's documentary note values in ``language``.

        With ``kind=None`` this spans every kind — the definition and the SKOS
        documentary notes alike; pass a :class:`ConceptNote.Kind` to narrow to one.
        Values read back ordered as the model orders notes, and an empty list when the
        concept has none matching (FR-006/FR-007).
        """
        rows = self.concept_notes.filter(language=language)
        if kind is not None:
            rows = rows.filter(kind=kind)
        return list(rows.values_list("value", flat=True))

    def add_note(self, language: str, kind: str, value: str) -> "ConceptNote":
        """Add a documentary note of any :class:`ConceptNote.Kind` and return the row.

        The row is validated before it is saved (``full_clean``): its ``language`` and
        ``kind`` must be configured choices and ``value`` non-empty. Notes carry no
        uniqueness — SKOS permits repeated notes of a kind per language (FR-006) — and
        adding one never touches this concept's slug or URI (FR-004).
        """
        row = ConceptNote(concept=self, language=language, kind=kind, value=value)
        row.full_clean()
        row.save()
        return row


class ConceptLabel(models.Model):
    """A language-tagged label for a concept, other than the identity anchor.

    The concept's preferred label in the vocabulary's effective default language
    is :attr:`Concept.label`; every other preferred label — and, in later stories,
    alternative and hidden labels — is one of these rows. At most one ``PREFERRED``
    label may exist per (concept, language), enforced by a partial unique constraint.
    """

    class Kind(models.TextChoices):
        """The lexical role of a label (SKOS ``prefLabel`` / ``altLabel`` / ``hiddenLabel``)."""

        PREFERRED = "preferred", _("preferred")
        ALTERNATIVE = "alternative", _("alternative")
        HIDDEN = "hidden", _("hidden")

    concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="labels",
        verbose_name=_("concept"),
        help_text=_("The concept this label names."),
    )
    language = models.CharField(
        max_length=16,
        choices=settings.LANGUAGES,
        verbose_name=_("language"),
        help_text=_("The language this label is written in, from the application's configured languages."),
    )
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        verbose_name=_("kind"),
        help_text=_("Whether this is the language's preferred label or an alternative or hidden one."),
    )
    text = models.CharField(
        max_length=255,
        verbose_name=_("text"),
        help_text=_("The label text, as it reads in this language."),
    )

    class Meta:
        verbose_name = _("label")
        verbose_name_plural = _("labels")
        ordering = ("language", "kind", "text")
        constraints = [
            models.UniqueConstraint(
                fields=["concept", "language"],
                # Kind.PREFERRED by value: a nested class body cannot see its
                # sibling Kind, so the enum's string value is used directly.
                condition=Q(kind="preferred"),
                name="one_preferred_label_per_language",
            ),
        ]

    def __str__(self) -> str:
        return self.text

    def clean(self):
        """Refuse a preferred label in the scheme's effective default language.

        That language's preferred label is :attr:`Concept.label`, the identity
        anchor; holding it here too would split identity across two places.
        """
        super().clean()
        if self.kind == self.Kind.PREFERRED and self.language == self.concept.scheme.effective_default_language:
            raise ValidationError(
                {
                    "language": ValidationError(
                        _(
                            "The preferred label in the default language '%(language)s' is the "
                            "concept's own label, not a separate label."
                        ),
                        params={"language": self.language},
                    )
                }
            )


class ConceptNote(models.Model):
    """A language-tagged documentary note on a concept (a SKOS documentary property).

    Covers the definition and the six SKOS documentary notes. Each is free prose in one
    language and may recur any number of times per (concept, language, kind) — SKOS sets
    no cardinality limit on notes, so there is no uniqueness here. The ``kind`` records
    which SKOS property the note fills; :data:`SKOS_CURIE` maps it to the RDF predicate.
    """

    class Kind(models.TextChoices):
        """The SKOS documentary property a note fills (``definition`` / ``scopeNote`` / …)."""

        DEFINITION = "definition", _("definition")
        SCOPE = "scope", _("scope note")
        EXAMPLE = "example", _("example")
        EDITORIAL = "editorial", _("editorial note")
        HISTORY = "history", _("history note")
        CHANGE = "change", _("change note")
        NOTE = "note", _("note")

    concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="concept_notes",
        verbose_name=_("concept"),
        help_text=_("The concept this note describes."),
    )
    language = models.CharField(
        max_length=16,
        choices=settings.LANGUAGES,
        verbose_name=_("language"),
        help_text=_("The language this note is written in, from the application's configured languages."),
    )
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        verbose_name=_("kind"),
        help_text=_(
            "Which SKOS documentary property this note fills — its definition, a scope note, an example, and so on."
        ),
    )
    # value is free documentary prose with no lookup path this slice, so it is
    # deliberately left unindexed (Article XIII; decisions.md §20).
    value = models.TextField(
        verbose_name=_("value"),
        help_text=_("The note text, as it reads in this language."),
    )

    class Meta:
        verbose_name = _("note")
        verbose_name_plural = _("notes")
        ordering = ("language", "kind")

    def __str__(self) -> str:
        return self.value


# The SKOS predicate CURIE each note Kind maps to on RDF export — a straight
# kind→predicate lookup, since the stored kind is the logical name, not the CURIE
# (decisions.md §19).
SKOS_CURIE = {
    ConceptNote.Kind.DEFINITION: "skos:definition",
    ConceptNote.Kind.SCOPE: "skos:scopeNote",
    ConceptNote.Kind.EXAMPLE: "skos:example",
    ConceptNote.Kind.EDITORIAL: "skos:editorialNote",
    ConceptNote.Kind.HISTORY: "skos:historyNote",
    ConceptNote.Kind.CHANGE: "skos:changeNote",
    ConceptNote.Kind.NOTE: "skos:note",
}
