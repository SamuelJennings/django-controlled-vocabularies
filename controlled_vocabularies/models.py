"""Models for controlled_vocabularies.

The relational models are the source of truth for a vocabulary and its concepts.
In this slice a vocabulary is a :class:`ConceptScheme`; its identifier (URI) is
computed from a configured base address and the slug, never stored (research R1).
"""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_unicode_slug
from django.db import models
from django.db.models import F, Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies import conf


def _configured_language_codes() -> set[str]:
    """The language codes the application is configured for (``settings.LANGUAGES``).

    Validated at runtime rather than baked into a field's ``choices``: binding
    ``choices=settings.LANGUAGES`` on a model field freezes the maintainer's
    language list into the shipped migration, so a downstream project with a
    different ``LANGUAGES`` sees spurious ``makemigrations`` drift. Reading the
    setting here keeps validation correct per install with nothing frozen.
    """
    return {code for code, _label in settings.LANGUAGES}


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
    default_language = models.CharField(
        max_length=16,
        blank=True,
        verbose_name=_("default language"),
        help_text=_(
            "The language whose preferred label anchors this vocabulary's concepts' identity. "
            "Leave blank to fall back to the application's configured default language. "
            "Must be one of the application's configured languages."
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

        Returns the per-vocabulary :attr:`default_language` override when set,
        otherwise the application's configured default language
        (``settings.LANGUAGE_CODE``). Independently-authored vocabularies can thus
        anchor identity in their own language (FR-009/FR-011).
        """
        return self.default_language or settings.LANGUAGE_CODE

    def save(self, *args, **kwargs):
        """Derive the slug from ``name``, freeze the default language once concepts
        exist, and refuse an empty or colliding slug."""
        # Freeze the default language once the vocabulary has concepts. Each concept's
        # identity anchor (``Concept.label``) is its preferred label in the effective
        # default language; changing that language afterwards would silently reinterpret
        # every anchor and break the one-preferred-label-per-language invariant. Before
        # any concept exists there is nothing to disturb, so the change is free.
        if self.pk is not None:
            stored = ConceptScheme.objects.filter(pk=self.pk).values_list("default_language", flat=True).first()
            if stored is not None and stored != self.default_language and self.concepts.exists():
                raise ValidationError(
                    {
                        "default_language": _(
                            "A vocabulary's default language cannot be changed once it has concepts, "
                            "because it would reinterpret their identity."
                        )
                    }
                )
        # An override, when given, must be one of the application's configured
        # languages (validated at runtime, since the field carries no settings-derived
        # choices — see _configured_language_codes).
        if self.default_language and self.default_language not in _configured_language_codes():
            raise ValidationError(
                {
                    "default_language": ValidationError(
                        _("'%(language)s' is not one of the application's configured languages."),
                        params={"language": self.default_language},
                    )
                }
            )
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
        # Match on a '/'-terminated base so a sibling path that merely shares the
        # base as a raw prefix (e.g. '<base>X/a/b') is not treated as in-base.
        prefix = f"{conf.get_base_uri()}/"
        if not uri.startswith(prefix):
            raise self.model.DoesNotExist(f"No concept matches the URI {uri!r}.")
        remainder = uri[len(prefix) :].strip("/")
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
    slug_is_manual = models.BooleanField(
        default=False,
        verbose_name=_("slug set manually"),
        help_text=_(
            "Whether the slug was set explicitly rather than derived from the label. "
            "A manual slug is left untouched when the label later changes."
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

    def set_slug(self, slug: str) -> None:
        """Set an explicit slug that survives later relabels (FR-010).

        Marks the slug manual and saves, so from now on :meth:`save` leaves it
        untouched when :attr:`label` changes. The value is stored exactly as given
        rather than re-slugified — this same mechanism later carries an imported
        vocabulary's own slugs unchanged (spec R2). The usual non-empty and
        within-scheme uniqueness checks still apply (FR-012).
        """
        self.slug = slug
        self.slug_is_manual = True
        self.save()

    def save(self, *args, **kwargs):
        """Derive the slug from ``label`` (unless set manually) and refuse an empty or colliding slug."""
        if not self.slug_is_manual:
            # An auto slug tracks the default-language label; a manual one is left
            # exactly as set (FR-010).
            self.slug = slugify(self.label, allow_unicode=True)
            if not self.slug:
                # FR-002: the default-language preferred label is the required identity
                # anchor. Name the language through a *named* placeholder so the msgid
                # stays static and translatable (decisions.md §9).
                raise ValidationError(
                    {
                        "label": ValidationError(
                            _("A preferred label in the default language '%(language)s' is required."),
                            params={"language": self.scheme.effective_default_language},
                        )
                    }
                )
        else:
            # A manual slug is stored verbatim (not re-slugified) but must still be a
            # well-formed single-segment slug: an empty or malformed value (spaces, '/',
            # control chars) would corrupt the composed URI and break get_by_uri
            # (Article IX — identity IS the URI). save() never runs full_clean(), so the
            # SlugField validator is applied explicitly here.
            if not self.slug:
                raise ValidationError({"slug": _("An explicit slug must not be empty.")})
            try:
                validate_unicode_slug(self.slug)
            except ValidationError as exc:
                raise ValidationError(
                    {
                        "slug": ValidationError(
                            _(
                                "An explicit slug must be a valid slug — letters, numbers, "
                                "hyphens or underscores, with no spaces or slashes."
                            ),
                        )
                    }
                ) from exc
        # Refuse a slug that collides with another concept in the same scheme
        # rather than minting a duplicate identifier or silently auto-suffixing
        # it (research R4). This guards both derived and explicit slugs (FR-012);
        # the UniqueConstraint is the integrity backstop.
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
        # Iterate the cached related set rather than .filter(): a caller's
        # prefetch_related('labels') then collapses the FR-007 read path to one query
        # instead of issuing a fresh query per call (a .filter() would bypass the cache).
        for row in self.labels.all():
            if row.language == language and row.kind == ConceptLabel.Kind.PREFERRED:
                return row.text
        return None

    def alt_labels(self, language: str) -> list[str]:
        """Return this concept's alternative label texts in ``language``.

        A concept may carry any number of alternative labels per language (FR-005);
        this returns just those in ``language``, ordered as the model orders labels,
        and an empty list when the concept has none in that language (FR-007). Reads
        the cached related set so it stays cheap under ``prefetch_related``.
        """
        return [
            row.text
            for row in self.labels.all()
            if row.language == language and row.kind == ConceptLabel.Kind.ALTERNATIVE
        ]

    def hidden_labels(self, language: str) -> list[str]:
        """Return this concept's hidden label texts in ``language``.

        Hidden labels — misspellings and search-only variants — are held separately
        from alternatives; like them they may occur any number of times per language
        (FR-005) and read back an empty list when absent (FR-007). Reads the cached
        related set so it stays cheap under ``prefetch_related``.
        """
        return [
            row.text for row in self.labels.all() if row.language == language and row.kind == ConceptLabel.Kind.HIDDEN
        ]

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
        for row in self.concept_notes.all():
            if row.language == language and row.kind == ConceptNote.Kind.DEFINITION:
                return row.value
        return None

    def notes(self, language: str, kind: str | None = None) -> list[str]:
        """Return this concept's documentary note values in ``language``.

        With ``kind=None`` this spans every kind — the definition and the SKOS
        documentary notes alike; pass a :class:`ConceptNote.Kind` to narrow to one.
        Values read back ordered as the model orders notes, and an empty list when the
        concept has none matching (FR-006/FR-007).
        """
        return [
            row.value
            for row in self.concept_notes.all()
            if row.language == language and (kind is None or row.kind == kind)
        ]

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

    # --- relations (FS-003) ------------------------------------------------
    # Concepts form an intra-vocabulary graph via ConceptRelation. Only one
    # direction of the hierarchy is stored (a BROADER row: source is the
    # narrower/child, target is the broader/parent); the narrower direction is
    # derived by reading from the target side, so the data can never assert one
    # direction without the other (research R1). `related` is symmetric and
    # stored once. Adding or removing a relation never touches this concept's
    # slug or URI (FR-004/FR-005).

    def broader(self) -> "models.QuerySet[Concept]":
        """Concepts one step broader than this one (FR-001).

        The targets of this concept's BROADER rows. Empty when it has no broader
        concept (FR-004). Returns a queryset so a caller can filter or order further.
        """
        return Concept.objects.filter(
            relations_as_target__source=self,
            relations_as_target__kind=ConceptRelation.Kind.BROADER,
        )

    def narrower(self) -> "models.QuerySet[Concept]":
        """Concepts one step narrower than this one — the derived inverse (FR-002).

        The sources of BROADER rows whose target is this concept. Never asserted
        directly: it is read back from the single stored broader edge.
        """
        return Concept.objects.filter(
            relations_as_source__target=self,
            relations_as_source__kind=ConceptRelation.Kind.BROADER,
        )

    def add_broader(self, other: "Concept") -> "ConceptRelation":
        """Give this concept a broader concept and return the created relation (FR-001).

        Records ``self skos:broader other`` — this concept becomes the narrower one,
        ``other`` the broader. Validated before saving: a self, cross-vocabulary,
        duplicate, or disjointness-violating edge is refused with a translatable
        message (FR-006/FR-009/FR-007/FR-008). Never touches this concept's slug/URI.
        """
        return self._add_relation(other, ConceptRelation.Kind.BROADER)

    def remove_broader(self, other: "Concept") -> None:
        """Remove the broader edge to ``other`` if present; a no-op otherwise (FR-005)."""
        ConceptRelation.objects.filter(source=self, target=other, kind=ConceptRelation.Kind.BROADER).delete()

    def related(self) -> "models.QuerySet[Concept]":
        """Concepts related to this one — the symmetric association (FR-003).

        Spans both columns of the ``related`` rows touching this concept (a related row
        is stored once, PK-ordered, so this concept may sit in either column) and returns
        the *other* endpoint each time. Empty when it has none (FR-004).
        """
        as_source = Concept.objects.filter(
            relations_as_target__source=self,
            relations_as_target__kind=ConceptRelation.Kind.RELATED,
        )
        as_target = Concept.objects.filter(
            relations_as_source__target=self,
            relations_as_source__kind=ConceptRelation.Kind.RELATED,
        )
        return (as_source | as_target).distinct()

    def add_related(self, other: "Concept") -> "ConceptRelation":
        """Relate this concept to ``other`` and return the created relation (FR-003).

        The association is symmetric and stored once: the model orders the endpoints by
        primary key, so asserting it in the mirror order resolves to the same row and is
        refused as a duplicate (FR-007). A self, cross-vocabulary, or disjointness-violating
        edge is refused (FR-006/FR-009/FR-008). Never touches either concept's slug/URI.
        """
        return self._add_relation(other, ConceptRelation.Kind.RELATED)

    def remove_related(self, other: "Concept") -> None:
        """Remove the related edge with ``other`` if present; a no-op otherwise (FR-005).

        Matches the pair in either stored order, so removal works from either concept.
        """
        ConceptRelation.objects.filter(kind=ConceptRelation.Kind.RELATED).filter(
            Q(source=self, target=other) | Q(source=other, target=self)
        ).delete()

    def _add_relation(self, other: "Concept", kind: str) -> "ConceptRelation":
        """Create, validate, and save a relation of ``kind`` from this concept to ``other``.

        The write path for the ``add_*`` helpers: it runs ``full_clean`` so the
        friendly validation messages fire, then saves (the model ``save`` backstops
        the invariants that have no DB constraint for the ``create``/factory path).
        Related edges are canonicalised by the model before persistence (research R2).
        """
        row = ConceptRelation(source=self, target=other, kind=kind)
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
        indexes = [
            # The (language, kind, text) label lookup/search path (FR-015); the FK
            # is auto-indexed. Deliberate per Article XIII (decisions.md, data-model).
            models.Index(fields=["language", "kind", "text"], name="cv_label_lang_kind_text_idx"),
        ]
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
        """Enforce the label invariants with translatable messages.

        The ``language`` must be one of the application's configured languages. A
        preferred label in the scheme's effective default language is refused — that
        language's preferred label is :attr:`Concept.label`, the identity anchor, and
        holding it here too would split identity across two places. A second preferred
        label in a language that already has one is refused as well (FR-001). The partial
        ``UniqueConstraint`` remains the integrity backstop for the duplicate-preferred
        rule; the default-language rule is additionally backstopped in :meth:`save`
        (no cross-table constraint against ``Concept.label`` is possible). Messages carry
        the language through a *named* placeholder (decisions.md §9).
        """
        super().clean()
        if self.language and self.language not in _configured_language_codes():
            raise ValidationError(
                {
                    "language": ValidationError(
                        _("'%(language)s' is not one of the application's configured languages."),
                        params={"language": self.language},
                    )
                }
            )
        if self.kind != self.Kind.PREFERRED:
            return
        self._reject_default_language_preferred()
        already_preferred = (
            ConceptLabel.objects.filter(concept=self.concept, language=self.language, kind=self.Kind.PREFERRED)
            .exclude(pk=self.pk)
            .exists()
        )
        if already_preferred:
            raise ValidationError(
                {
                    "language": ValidationError(
                        _("A preferred label in the language '%(language)s' already exists for this concept."),
                        params={"language": self.language},
                    )
                }
            )

    def _reject_default_language_preferred(self) -> None:
        """Refuse a PREFERRED row in the scheme's effective default language.

        That language's preferred label is :attr:`Concept.label`; a row here too would
        plant a second identity anchor. Called from :meth:`clean` and again from
        :meth:`save`, because ``.objects.create()`` and factories bypass ``full_clean``
        and this invariant has no DB-level constraint to fall back on (a check against a
        column on another table is not expressible).
        """
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

    def save(self, *args, **kwargs):
        """Persist the label, backstopping the default-language-preferred rule.

        ``clean()`` runs only on ``full_clean``; ``.create()``/factories bypass it, so the
        default-language guard is re-checked here to keep a second identity anchor from
        being planted through any save path (review finding).
        """
        self._reject_default_language_preferred()
        super().save(*args, **kwargs)


class ConceptNote(models.Model):
    """A language-tagged documentary note on a concept (a SKOS documentary property).

    Covers the definition and the six SKOS documentary notes. Each is free prose in one
    language and may recur any number of times per (concept, language, kind) — SKOS sets
    no cardinality limit on notes, so there is no uniqueness here. The ``kind`` records
    which SKOS property the note fills; the kind→predicate mapping for RDF export lands
    with the exporter that first needs it (roadmap R2/R4), not here.
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

    def clean(self):
        """Validate that ``language`` is one of the application's configured languages.

        The field carries no settings-derived ``choices`` (that would freeze the list
        into the migration), so the check runs here at ``full_clean`` — the path
        ``Concept.add_note`` takes.
        """
        super().clean()
        if self.language and self.language not in _configured_language_codes():
            raise ValidationError(
                {
                    "language": ValidationError(
                        _("'%(language)s' is not one of the application's configured languages."),
                        params={"language": self.language},
                    )
                }
            )


class ConceptRelation(models.Model):
    """A directed, intra-vocabulary link between two concepts (a SKOS semantic relation).

    Concepts form a graph: a ``broader``/``narrower`` hierarchy (an inverse pair) and a
    symmetric ``related`` association. Only one direction of the hierarchy is stored — a
    ``BROADER`` row where :attr:`source` is the narrower/child and :attr:`target` the
    broader/parent — and ``narrower`` is read back from the target side, so the data can
    never assert one direction without the other (``docs/brainstorm.md``; research R1). A
    ``related`` row is symmetric and stored once, its endpoints ordered by primary key so
    an assertion in either order resolves to the same row (research R2). Cross-vocabulary
    links are mappings, a separate mechanism, and are refused here (FR-009).
    """

    class Kind(models.TextChoices):
        """The stored relation kind. ``narrower`` is not stored — it is the inverse read of ``broader``."""

        BROADER = "broader", _("broader")
        RELATED = "related", _("related")

    source = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="relations_as_source",
        verbose_name=_("source concept"),
        help_text=_(
            "One end of the relation. For a broader link this is the narrower (child) concept; "
            "for a related link it is the lower-numbered of the pair."
        ),
    )
    target = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="relations_as_target",
        verbose_name=_("target concept"),
        help_text=_(
            "The other end of the relation. For a broader link this is the broader (parent) concept; "
            "for a related link it is the higher-numbered of the pair."
        ),
    )
    kind = models.CharField(
        max_length=16,
        choices=Kind.choices,
        verbose_name=_("kind"),
        help_text=_("The kind of link: a broader/narrower hierarchy edge, or a symmetric related association."),
    )

    class Meta:
        verbose_name = _("concept relation")
        verbose_name_plural = _("concept relations")
        ordering = ("source", "kind", "target")
        constraints = [
            # No duplicate edge (FR-007). With related's PK-canonicalisation this also
            # blocks a mirror-order related duplicate. A reversed *broader* edge is a
            # different, permitted edge (a 2-cycle), so the ordered triple is exact.
            models.UniqueConstraint(fields=["source", "target", "kind"], name="unique_concept_relation"),
            # No self-relation (FR-006), enforced at the database.
            models.CheckConstraint(condition=~Q(source=F("target")), name="concept_relation_not_self"),
        ]
        indexes = [
            # The reverse reads — derived narrower (query by target, kind=BROADER) and the
            # incoming half of related (FR-012, research R6). Source-leading is covered by
            # the unique constraint; both FKs are auto-indexed. Deliberate per Article XIII.
            models.Index(fields=["target", "kind"], name="cv_relation_target_kind_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.source} {self.kind} {self.target}"

    def _canonicalise(self) -> None:
        """Order a ``related`` row's endpoints by primary key so it is stored once.

        ``related`` is symmetric; storing ``(a, b)`` and ``(b, a)`` as separate rows would
        let the same association exist twice. Ordering the endpoints by PK gives a single
        canonical form, so the ordinary unique constraint catches a mirror-order duplicate
        (research R2). Broader rows are directional and left untouched. Both endpoints are
        always persisted before a relation is made, so the PKs exist.
        """
        if (
            self.kind == self.Kind.RELATED
            and self.source_id is not None
            and self.target_id is not None
            and self.source_id > self.target_id
        ):
            self.source_id, self.target_id = self.target_id, self.source_id

    def _reject_self(self) -> None:
        """Refuse a relation from a concept to itself (FR-006).

        The DB ``CheckConstraint`` is the backstop; this raises the curator-facing message.
        """
        if self.source_id is not None and self.source_id == self.target_id:
            raise ValidationError(_("A concept cannot be in a relation with itself."))

    def _reject_cross_scheme(self) -> None:
        """Refuse a relation whose two concepts belong to different vocabularies (FR-009).

        Broader/narrower/related are intra-vocabulary; a cross-vocabulary link is a mapping,
        a separate mechanism that is out of scope. No single-table or cross-table DB
        constraint can express this, so it is enforced here and backstopped in :meth:`save`.
        The message names both vocabularies through *named* placeholders (decisions.md §9).
        """
        if self.source_id is None or self.target_id is None:
            return
        if self.source.scheme_id != self.target.scheme_id:
            raise ValidationError(
                _(
                    "A relation can only join concepts in the same vocabulary; "
                    "'%(source)s' and '%(target)s' are in different vocabularies."
                ),
                params={"source": self.source.scheme.name, "target": self.target.scheme.name},
            )

    def _reject_disjointness_violation(self) -> None:
        """Refuse a pair already joined by the *other* kind of relation (FR-008).

        SKOS makes ``related`` disjoint from the ``broader``/``narrower`` hierarchy: a pair
        of concepts may be joined one way or the other, not both. This refuses a new relation
        when a relation of the other kind already joins the same unordered pair in either
        stored direction. It is a single indexed lookup on the pair — **no hierarchy
        traversal**, so it is scoped to *directly*-asserted pairs (a transitively hierarchical
        pair may still be related; the transitive check would need the walk this slice avoids).
        Has no single-table DB constraint (it spans two rows and two kinds), so it lives here
        and is backstopped in :meth:`save`. The message names the conflicting kind.
        """
        if self.source_id is None or self.target_id is None:
            return
        other_kind = self.Kind.RELATED if self.kind == self.Kind.BROADER else self.Kind.BROADER
        conflict = (
            ConceptRelation.objects.filter(kind=other_kind)
            .filter(
                Q(source_id=self.source_id, target_id=self.target_id)
                | Q(source_id=self.target_id, target_id=self.source_id)
            )
            .exclude(pk=self.pk)
            .exists()
        )
        if conflict:
            raise ValidationError(
                _(
                    "These concepts are already joined as '%(kind)s'; a broader/narrower "
                    "pair and a related pair are mutually exclusive."
                ),
                params={"kind": self.Kind(other_kind).label},
            )

    def clean(self):
        """Validate the relation invariants with translatable messages (``full_clean`` path)."""
        super().clean()
        self._canonicalise()
        self._reject_self()
        self._reject_cross_scheme()
        self._reject_disjointness_violation()

    def save(self, *args, **kwargs):
        """Persist the relation, backstopping the constraint-less invariants.

        ``clean()`` runs only under ``full_clean``; ``.objects.create()``/``bulk_create``/
        factories bypass it, so canonicalisation and the same-vocabulary / not-self /
        disjointness rules are re-applied here to keep a bad row out through any save path
        (the #15/#16 pattern).
        """
        self._canonicalise()
        self._reject_self()
        self._reject_cross_scheme()
        self._reject_disjointness_violation()
        super().save(*args, **kwargs)
