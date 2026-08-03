"""Models for controlled_vocabularies.

The relational models are the source of truth for a vocabulary and its concepts.
A record's ``uri`` is its permanent identity: an externally assigned identifier
held verbatim when one was supplied (``permanent_uri``, FS-005), or otherwise
composed from a configured base address and the slug exactly as R1 did.
"""

import urllib.parse
from typing import TypeVar

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.validators import validate_unicode_slug
from django.db import models
from django.db.models import F, Max, Q
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from controlled_vocabularies import conf

#: Schemes that can carry executable content and must never be accepted as an
#: externally assigned permanent URI (FR-004) — a stored identifier is later
#: rendered as a link by the browsing interface, so a hostile scheme accepted
#: here becomes a hazard there.
_UNSAFE_PERMANENT_URI_SCHEMES = frozenset({"javascript", "data", "vbscript"})

#: The length bound for a permanent URI (FR-004, decisions.md D5): far beyond any
#: identifier real SKOS vocabularies use, and inside the unique-index limit of
#: every mainstream database, including MySQL's 3072-byte cap on ``utf8mb4``.
PERMANENT_URI_MAX_LENGTH = 500


def validate_permanent_uri(value: str) -> None:
    """Validate an externally assigned permanent URI (FR-004).

    Requires a well-formed absolute identifier — a non-empty scheme and a
    non-empty remainder, so a bare relative path is refused — refuses a
    scheme that can carry executable content, and caps length at 500
    characters. Used both as a field validator (so ``full_clean()`` catches
    it) and called directly from each model's ``save()``, because Django's
    ``save()`` never calls ``full_clean()`` and the import path this feature
    exists to serve writes through ``save()`` directly (research R5).
    """
    parsed = urllib.parse.urlsplit(value)
    if not parsed.scheme or not (parsed.netloc or parsed.path):
        raise ValidationError(
            _("'%(uri)s' is not a well-formed absolute identifier with a scheme."),
            params={"uri": value},
            code="permanent_uri_not_absolute",
        )
    if parsed.scheme.lower() in _UNSAFE_PERMANENT_URI_SCHEMES:
        raise ValidationError(
            _("'%(uri)s' uses the scheme '%(scheme)s', which is not permitted."),
            params={"uri": value, "scheme": parsed.scheme},
            code="permanent_uri_unsafe_scheme",
        )
    if len(value) > PERMANENT_URI_MAX_LENGTH:
        raise ValidationError(
            _("A permanent URI cannot exceed %(max_length)s characters; '%(uri)s' has %(length)s."),
            params={"max_length": PERMANENT_URI_MAX_LENGTH, "uri": value, "length": len(value)},
            code="permanent_uri_too_long",
        )


def _permanent_uri_still_deferred(instance: "PermanentUriModel") -> bool:
    """True when the column was never loaded and has not been assigned since.

    Nothing about the identifier can have changed in that case, so every check
    below can be skipped — and must be, because merely reading
    ``instance.permanent_uri`` to check it would fetch the column that was
    deliberately left behind.
    """
    return "permanent_uri" in instance.get_deferred_fields()


def _stored_permanent_uri(instance: "PermanentUriModel") -> str | None:
    """The identifier the database currently holds for ``instance``.

    ``None`` both for a row holding no identifier and for one that does not
    exist in the database yet (``instance.pk is None``) — a new row cannot
    rewrite anything stored, so there is nothing to read back for it.
    """
    if instance.pk is None:
        return None
    return type(instance)._base_manager.filter(pk=instance.pk).values_list("permanent_uri", flat=True).first()


def _permanent_uri_models() -> tuple[type["PermanentUriModel"], ...]:
    """Every concrete model that carries a ``permanent_uri`` column (T028).

    Derived from :class:`PermanentUriModel`'s live subclasses rather than a
    hardcoded tuple, so a fourth model enrols itself in the cross-model
    uniqueness check the moment it subclasses the abstract base — forgetting to
    add it to a hand-maintained list is no longer possible.
    """
    return tuple(model for model in PermanentUriModel.__subclasses__() if not model._meta.abstract)


def _reject_permanent_uri_held_by_another_model(instance: "PermanentUriModel") -> None:
    """Refuse a ``permanent_uri`` already held by a record of a *different* model.

    Uniqueness within one model is a database constraint (FR-006, per-model
    ``UniqueConstraint``). No portable constraint spans the three tables, so this
    covers the cross-model case (research R4): a concept and a collection, say,
    must not hold the same externally assigned identifier. Only runs when the
    column is actually set, so nothing is paid for a still-provisional record.
    """
    if not instance.permanent_uri:
        return
    model = type(instance)
    others = [candidate for candidate in _permanent_uri_models() if candidate is not model]
    if any(candidate._default_manager.filter(permanent_uri=instance.permanent_uri).exists() for candidate in others):
        raise ValidationError(
            {
                "permanent_uri": ValidationError(
                    _("The permanent URI '%(uri)s' is already held by another record."),
                    params={"uri": instance.permanent_uri},
                    code="permanent_uri_held_elsewhere",
                )
            }
        )


def _normalise_blank_permanent_uri(instance: "PermanentUriModel") -> None:
    """Store the *absence* of an identifier as ``None``, never as ``""``.

    ``permanent_uri`` is nullable so the partial ``UniqueConstraint`` — which
    only covers non-null values — leaves provisional records unconstrained. An
    empty string is not null, so it falls inside that constraint while
    :attr:`uri` and :attr:`has_permanent_uri` both read it as absent: the record
    behaves as provisional yet occupies the unique slot, and the second one
    saved fails at the database with an opaque ``IntegrityError``. Assigning
    ``""`` rather than ``None`` is the ordinary shape of importer and serializer
    code (``node.get("about") or ""``), which is exactly the path this feature
    exists to serve, so it is normalised here rather than left to every caller.
    """
    if instance.permanent_uri == "":
        instance.permanent_uri = None


def _check_permanent_uri(instance: "PermanentUriModel", *, validate_format: bool) -> None:
    """Every ``permanent_uri`` invariant a ``save()`` or ``full_clean()`` owes, in
    one place.

    The single authority for "is an identifier already stored" is the database,
    read back here with :func:`_stored_permanent_uri` — never an in-memory
    snapshot taken at some earlier load. A snapshot goes stale the moment a
    second instance of the same row is saved, refreshed, or constructed with an
    explicit ``pk``: a three-lens review found all three bypass a
    snapshot-based guard and let a save rewrite or silently clear an identifier
    a *different* instance had already stored (T029). A read-back cannot go
    stale, at the cost of one indexed query per save of an existing row whose
    column is loaded; an insert pays nothing, since :func:`_stored_permanent_uri`
    short-circuits on ``instance.pk is None``.

    ``validate_format`` is ``False`` from ``clean()``, called only under
    ``full_clean()``, where the field validator already ran
    :func:`validate_permanent_uri`; it is ``True`` from ``save()``, which never
    calls ``full_clean()`` and is the path the import work this feature exists
    to serve actually uses (research R5).
    """
    if _permanent_uri_still_deferred(instance):
        return
    _normalise_blank_permanent_uri(instance)
    stored = _stored_permanent_uri(instance)
    if stored is not None and instance.permanent_uri != stored:
        raise ValidationError(
            {
                "permanent_uri": ValidationError(
                    _("The permanent URI '%(uri)s' is fixed and cannot be changed or cleared once stored."),
                    params={"uri": stored},
                    code="permanent_uri_fixed",
                )
            }
        )
    if not instance.permanent_uri:
        return
    if validate_format:
        try:
            validate_permanent_uri(instance.permanent_uri)
        except ValidationError as exc:
            raise ValidationError({"permanent_uri": exc}) from exc
    if instance.permanent_uri == stored:
        # Nothing about the value changed, so nothing that depends on it could
        # have either — skip the cross-model probe's wasted queries (T029).
        return
    _reject_permanent_uri_held_by_another_model(instance)


def _configured_language_codes() -> set[str]:
    """The language codes the application is configured for (``settings.LANGUAGES``).

    Validated at runtime rather than baked into a field's ``choices``: binding
    ``choices=settings.LANGUAGES`` on a model field freezes the maintainer's
    language list into the shipped migration, so a downstream project with a
    different ``LANGUAGES`` sees spurious ``makemigrations`` drift. Reading the
    setting here keeps validation correct per install with nothing frozen.
    """
    return {code for code, _label in settings.LANGUAGES}


_ModelT = TypeVar("_ModelT", bound=models.Model)


class PermanentUriLookupMixin(models.Manager[_ModelT]):
    """Adds :meth:`get_by_uri` to a manager (research R6).

    Shared by the ``ConceptScheme``, ``Concept``, and ``Collection`` managers so
    #50's importer can upsert a vocabulary or a collection by identifier the same
    way it already can a concept, without three drifting implementations.
    """

    def get_by_uri(self, uri: str) -> _ModelT:
        """Return the record identified by ``uri``, fixed or provisional (FR-007).

        An exact match on the stored ``permanent_uri`` is tried first, so a fixed
        identifier resolves correctly even when it happens to sit under this
        site's own configured base address (FR-003, research R6). On no match
        this falls back to :meth:`_get_by_local_parse`, the model's
        base-relative composition, which raises the model's ``DoesNotExist``
        when nothing resolves either way.
        """
        try:
            return self.get(permanent_uri=uri)
        except ObjectDoesNotExist:
            return self._get_by_local_parse(uri)

    def _get_by_local_parse(self, uri: str) -> _ModelT:
        """Resolve a provisional, base-relative identifier. Implemented per model."""
        raise NotImplementedError


class PermanentUriModel(models.Model):
    """Abstract base for a model carrying an externally assigned identifier (T028).

    ``ConceptScheme``, ``Concept``, and ``Collection`` each subclass this rather
    than repeating the ``permanent_uri`` field, ``uri``, ``has_permanent_uri``,
    the permanent-URI half of ``clean()``, and the save-tail validation hook
    byte-identically three times. A concrete subclass supplies only its own
    ``local_url`` composition, its ``Meta.constraints`` entry name, and its
    ``permanent_uri`` field's ``help_text`` wording (by redeclaring the field —
    an ordinary Django abstract-base override, not a second column).
    """

    permanent_uri = models.CharField(
        max_length=PERMANENT_URI_MAX_LENGTH,
        null=True,
        blank=True,
        verbose_name=_("permanent URI"),
        help_text=_(
            "The identifier assigned by this record's publisher, held exactly as given. "
            "Fixed once set. Leave blank for a record authored here, which reports the "
            "identifier composed from this site's address instead."
        ),
        validators=[validate_permanent_uri],
    )

    class Meta:
        abstract = True

    @property
    def uri(self) -> str:
        """The record's permanent URI: its identity.

        The externally assigned identifier when one is held (fixed, held
        verbatim), otherwise :attr:`local_url` (provisional, follows a rename
        or a change to the configured address).
        """
        return self.permanent_uri or self.local_url

    @property
    def local_url(self) -> str:
        """Where this record is viewed on this site (FR-008). Implemented per model."""
        raise NotImplementedError

    @property
    def has_permanent_uri(self) -> bool:
        """Whether this record's permanent URI is externally fixed (research R2).

        Recorded by the presence of :attr:`permanent_uri`, never inferred by
        comparing it against the configured base address (FR-003).
        """
        return bool(self.permanent_uri)

    def clean(self):
        """Refuse a ``permanent_uri`` that rewrites or clears a stored one, or is
        already held by a record of a different model.

        Field validators (:func:`validate_permanent_uri`) already cover format on the
        ``full_clean()`` path; the checks here need a query beyond one field so they
        live here rather than on the field itself (research R4).
        """
        super().clean()
        _check_permanent_uri(self, validate_format=False)

    def save(self, *args, **kwargs):
        """Validate ``permanent_uri`` — reading the database, never a stale
        snapshot — before the write."""
        _check_permanent_uri(self, validate_format=True)
        super().save(*args, **kwargs)


class ConceptSchemeManager(PermanentUriLookupMixin["ConceptScheme"]):
    """Default manager for :class:`ConceptScheme`, adding permanent-URI-based lookup."""

    def _get_by_local_parse(self, uri: str) -> "ConceptScheme":
        """Resolve ``{base}/{slug}`` — R1's scheme URI composition, unchanged.

        A remainder containing a further ``/`` belongs to a concept or a
        collection, not a scheme, and is refused rather than mistaken for one.
        """
        prefix = f"{conf.get_base_uri()}/"
        if not uri.startswith(prefix):
            raise self.model.DoesNotExist(f"No vocabulary matches the URI {uri!r}.")
        slug = uri[len(prefix) :].strip("/")
        if not slug or "/" in slug:
            raise self.model.DoesNotExist(f"No vocabulary matches the URI {uri!r}.")
        return self.get(slug=slug)


class ConceptScheme(PermanentUriModel):
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
    permanent_uri = models.CharField(
        max_length=PERMANENT_URI_MAX_LENGTH,
        null=True,
        blank=True,
        verbose_name=_("permanent URI"),
        help_text=_(
            "The identifier assigned by this vocabulary's publisher, held exactly as given. "
            "Fixed once set. Leave blank for a vocabulary authored here, which reports the "
            "identifier composed from this site's address instead."
        ),
        validators=[validate_permanent_uri],
    )

    objects = ConceptSchemeManager()

    class Meta:
        verbose_name = _("vocabulary")
        verbose_name_plural = _("vocabularies")
        constraints = [
            models.UniqueConstraint(
                fields=["permanent_uri"],
                condition=Q(permanent_uri__isnull=False),
                name="conceptscheme_permanent_uri_unique",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def local_url(self) -> str:
        """Where this scheme is viewed on this site (FR-008), always this
        site's own — the configured base address and its slug — regardless of
        who assigned :attr:`permanent_uri`.
        """
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


class ConceptManager(PermanentUriLookupMixin["Concept"]):
    """Default manager for :class:`Concept`, adding permanent-URI-based lookup.

    Subclasses the standard manager so ``Concept.objects`` keeps all default
    behaviour and gains :meth:`~PermanentUriLookupMixin.get_by_uri`, which keeps
    its existing name and exact local behaviour (FR-014) and additionally
    resolves an externally assigned identifier.
    """

    def _get_by_local_parse(self, uri: str) -> "Concept":
        """Resolve ``{base}/{scheme-slug}/{concept-slug}`` — R1's concept URI
        composition, unchanged.

        Splits the remainder below the configured base into its
        ``scheme-slug/concept-slug`` parts and resolves by scheme slug and
        slug. The URI — not the primary key — is the identity (Article IX); a
        URI outside the base or a well-formed URI with no matching concept
        raises :class:`Concept.DoesNotExist`, the standard ORM lookup
        behaviour. Unicode slugs resolve the same as ASCII ones.
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


class Concept(PermanentUriModel):
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
    permanent_uri = models.CharField(
        max_length=PERMANENT_URI_MAX_LENGTH,
        null=True,
        blank=True,
        verbose_name=_("permanent URI"),
        help_text=_(
            "The identifier assigned by this concept's publisher, held exactly as given. "
            "Fixed once set. Leave blank for a concept authored here, which reports the "
            "identifier composed from this site's address instead."
        ),
        validators=[validate_permanent_uri],
    )

    objects = ConceptManager()

    class Meta:
        verbose_name = _("concept")
        verbose_name_plural = _("concepts")
        constraints = [
            models.UniqueConstraint(fields=["scheme", "slug"], name="unique_concept_slug_per_scheme"),
            models.UniqueConstraint(
                fields=["permanent_uri"],
                condition=Q(permanent_uri__isnull=False),
                name="concept_permanent_uri_unique",
            ),
        ]

    def __str__(self) -> str:
        return self.label

    @property
    def local_url(self) -> str:
        """Where this concept is viewed on this site (FR-008), always this
        site's own regardless of who assigned :attr:`permanent_uri`.

        Composed from the *scheme's* :attr:`~ConceptScheme.local_url`, never
        from its ``uri`` — a concept added locally to a vocabulary whose own
        identifier is externally fixed still needs a place on this site, not
        one on the publisher's domain (spec.md Edge Cases §4).
        """
        return f"{self.scheme.local_url}/{self.slug}"

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

    def collections(self) -> list["Collection"]:
        """The collections this concept is a member of (empty when it belongs to none).

        Read from the reverse membership relation. Collections are an organisational
        overlay: reading or changing membership never touches the concept's identity,
        labels, or relations (FS-004 FR-008).
        """
        return list(Collection.objects.filter(memberships__concept=self).distinct())


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


class CollectionManager(PermanentUriLookupMixin["Collection"]):
    """Default manager for :class:`Collection`, adding permanent-URI-based lookup."""

    def _get_by_local_parse(self, uri: str) -> "Collection":
        """Resolve ``{base}/{scheme-slug}/collection/{slug}`` — R1's collection
        URI composition, unchanged.

        The literal ``collection`` segment is required, so a concept's identifier
        (``{base}/{scheme-slug}/{slug}``, two segments) is never mistaken for one.
        """
        prefix = f"{conf.get_base_uri()}/"
        if not uri.startswith(prefix):
            raise self.model.DoesNotExist(f"No collection matches the URI {uri!r}.")
        remainder = uri[len(prefix) :].strip("/")
        parts = remainder.split("/")
        if len(parts) != 3 or parts[1] != "collection":
            raise self.model.DoesNotExist(f"No collection matches the URI {uri!r}.")
        scheme_slug, _collection_segment, collection_slug = parts
        return self.get(scheme__slug=scheme_slug, slug=collection_slug)


class Collection(PermanentUriModel):
    """A named grouping of concepts within one vocabulary (a SKOS collection).

    A collection captures a grouping the ``broader``/``narrower`` hierarchy does not
    express — how a curator wants a vocabulary organised and displayed. Its members are
    concepts of the *same* vocabulary (:class:`CollectionMember` enforces it); membership
    is many-to-many and asserts no semantic relation between members (FS-004 FR-008). When
    :attr:`ordered` (a ``skos:OrderedCollection``) the members carry a deliberate sequence
    read back by :meth:`members`; otherwise the collection is a set. The ``slug`` is derived
    from ``name`` on save and unique within the scheme; the ``uri`` is composed on read under
    a ``/collection/`` segment so it can never collide with a concept URI (research R4).
    """

    scheme = models.ForeignKey(
        ConceptScheme,
        on_delete=models.CASCADE,
        related_name="collections",
        verbose_name=_("vocabulary"),
        help_text=_("The vocabulary this collection belongs to. Its members are concepts of this vocabulary."),
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_("name"),
        help_text=_("The human-readable name of the collection. Its slug is derived automatically from this."),
    )
    slug = models.SlugField(
        max_length=255,
        allow_unicode=True,
        verbose_name=_("slug"),
        help_text=_(
            "A URL-safe identifier derived automatically from the name. A slug must be unique within a given vocabulary."
        ),
    )
    ordered = models.BooleanField(
        default=False,
        verbose_name=_("ordered"),
        help_text=_(
            "Whether the collection's members carry a deliberate sequence (a SKOS ordered collection). "
            "An unordered collection is a plain set."
        ),
    )
    permanent_uri = models.CharField(
        max_length=PERMANENT_URI_MAX_LENGTH,
        null=True,
        blank=True,
        verbose_name=_("permanent URI"),
        help_text=_(
            "The identifier assigned by this collection's publisher, held exactly as given. "
            "Fixed once set. Leave blank for a collection authored here, which reports the "
            "identifier composed from this site's address instead."
        ),
        validators=[validate_permanent_uri],
    )

    objects = CollectionManager()

    class Meta:
        verbose_name = _("collection")
        verbose_name_plural = _("collections")
        constraints = [
            models.UniqueConstraint(fields=["scheme", "slug"], name="unique_collection_slug_per_scheme"),
            models.UniqueConstraint(
                fields=["permanent_uri"],
                condition=Q(permanent_uri__isnull=False),
                name="collection_permanent_uri_unique",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def local_url(self) -> str:
        """Where this collection is viewed on this site (FR-008), always this
        site's own regardless of who assigned :attr:`permanent_uri`.

        Composed from the *scheme's* :attr:`~ConceptScheme.local_url`, never
        from its ``uri`` — a collection added locally to a vocabulary whose own
        identifier is externally fixed still needs a place on this site, not
        one on the publisher's domain (spec.md Edge Cases §4). The
        ``/collection/`` segment keeps a collection's identity space disjoint
        from a concept's (whose local URL is ``{scheme.local_url}/{slug}``),
        so the two can never mint the same address when RDF projection lands
        (research R4).
        """
        return f"{self.scheme.local_url}/collection/{self.slug}"

    def save(self, *args, **kwargs):
        """Derive the slug from ``name`` and refuse an empty or colliding slug.

        The same identity discipline :class:`ConceptScheme`/:class:`Concept` use: a
        non-empty slug, and no collision with another collection in the same vocabulary
        (the ``UniqueConstraint`` is the integrity backstop), with translatable
        named-placeholder messages.
        """
        self.slug = slugify(self.name, allow_unicode=True)
        if not self.slug:
            raise ValidationError({"name": _("Name must produce a non-empty slug.")})
        if Collection.objects.filter(scheme=self.scheme, slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError(
                {
                    "slug": ValidationError(
                        _("A collection with the slug '%(slug)s' already exists in this vocabulary."),
                        params={"slug": self.slug},
                    )
                }
            )
        super().save(*args, **kwargs)

    def add(self, concept: "Concept") -> "CollectionMember":
        """Add ``concept`` to the collection as a member; append it (FS-004 FR-002).

        A concept already in the collection is held once — the existing membership is
        returned unchanged, never duplicated (FR-004). A concept from another vocabulary is
        refused (FR-005), validated on this write path via ``full_clean`` so the curator-facing
        message fires. The new member's ``position`` is the current maximum plus one, so an
        ordered collection reads members back in the order they were added.
        """
        existing = self.memberships.filter(concept=concept).first()
        if existing is not None:
            return existing
        highest = self.memberships.aggregate(highest=Max("position"))["highest"]
        position = 0 if highest is None else highest + 1
        member = CollectionMember(collection=self, concept=concept, position=position)
        member.full_clean()
        member.save()
        return member

    def remove(self, concept: "Concept") -> None:
        """Remove ``concept``'s membership if present; a no-op otherwise (FS-004 FR-002).

        Only the membership row is deleted — the concept itself, and its membership in any
        other collection, are untouched (FR-003).
        """
        self.memberships.filter(concept=concept).delete()

    def members(self) -> list["Concept"]:
        """The collection's member concepts (empty when it has none).

        When :attr:`ordered`, returned in ascending ``position`` — the deliberate sequence
        (FR-006); removing a member leaves the survivors in their original relative order,
        because a gap between positions does not affect the read (FR-007). When not ordered,
        returned as a set (no promised sequence).
        """
        memberships = self.memberships.select_related("concept")
        memberships = memberships.order_by("position", "id") if self.ordered else memberships.order_by("id")
        return [membership.concept for membership in memberships]

    def set_member_order(self, concepts: "list[Concept]") -> None:
        """Reassign the members' positions to the given sequence (FS-004 FR-007).

        Valid only on an ordered collection — ordering is meaningless for a set, so an
        unordered collection refuses it with a translatable message (FR-006). ``concepts``
        must be exactly the collection's current member set; otherwise it is refused. After
        it returns, :meth:`members` reflects the new sequence.
        """
        if not self.ordered:
            raise ValidationError(
                _("Only an ordered collection can have its members ordered; '%(name)s' is not ordered."),
                params={"name": self.name},
            )
        current = {membership.concept_id for membership in self.memberships.all()}
        given = [concept.pk for concept in concepts]
        if len(given) != len(current) or set(given) != current:
            raise ValidationError(_("The given concepts must be exactly this collection's current members."))
        position_of = {concept_id: index for index, concept_id in enumerate(given)}
        for membership in self.memberships.all():
            new_position = position_of[membership.concept_id]
            if membership.position != new_position:
                membership.position = new_position
                membership.save(update_fields=["position"])


class CollectionMember(models.Model):
    """The membership edge joining a :class:`Collection` to one member :class:`Concept`.

    A through model because the edge carries a ``position`` (the sort key for an ordered
    collection) and must be validated for scheme-confinement — a bare ``ManyToManyField``
    offers neither. Held once per ``(collection, concept)`` by a unique constraint (FR-004);
    both endpoints must belong to the same vocabulary (FR-005). ``on_delete=CASCADE`` on both
    FKs because a membership is not consumer data and is meaningless without both ends — the
    same reasoning ``ConceptRelation`` uses for a relation edge; Article IX's
    ``PROTECT``/deprecation governs consumer references and concept retirement (#19), which
    this slice does not touch.
    """

    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="memberships",
        verbose_name=_("collection"),
        help_text=_("The collection this membership belongs to."),
    )
    concept = models.ForeignKey(
        Concept,
        on_delete=models.CASCADE,
        related_name="collection_memberships",
        verbose_name=_("concept"),
        help_text=_("The member concept. It must belong to the collection's own vocabulary."),
    )
    position = models.PositiveIntegerField(
        default=0,
        verbose_name=_("position"),
        help_text=_(
            "The member's place in an ordered collection's sequence. Meaningful only when the "
            "collection is ordered; ignored otherwise."
        ),
    )

    class Meta:
        verbose_name = _("collection member")
        verbose_name_plural = _("collection members")
        ordering = ("collection", "position", "id")
        constraints = [
            # A concept is held once per collection (FR-004). This also provides the
            # collection-leading membership index.
            models.UniqueConstraint(fields=["collection", "concept"], name="unique_collection_member"),
        ]
        indexes = [
            # Backs the ordered members() read (Article XIII, deliberate). The reverse
            # read (a concept's collections) is covered by the auto-indexed concept FK.
            models.Index(fields=["collection", "position"], name="cv_collection_member_order_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.concept} in {self.collection}"

    def _reject_cross_scheme(self) -> None:
        """Refuse a member from a different vocabulary than the collection's (FR-005).

        A collection groups only its own vocabulary's concepts. No single- or cross-table DB
        constraint can express this equality, so it is enforced here and backstopped in
        :meth:`save`. The message names both vocabularies through *named* placeholders so the
        translatable msgid stays static.
        """
        if self.collection_id is None or self.concept_id is None:
            return
        if self.collection.scheme_id != self.concept.scheme_id:
            raise ValidationError(
                _(
                    "A collection can only group concepts from its own vocabulary; "
                    "'%(concept_scheme)s' is not '%(collection_scheme)s'."
                ),
                params={
                    "concept_scheme": self.concept.scheme.name,
                    "collection_scheme": self.collection.scheme.name,
                },
            )

    def clean(self):
        """Validate the membership invariants with translatable messages (``full_clean`` path)."""
        super().clean()
        self._reject_cross_scheme()

    def save(self, *args, **kwargs):
        """Persist the membership, backstopping the scheme-confinement rule.

        ``clean()`` runs only under ``full_clean``; ``.objects.create``/factories bypass it,
        so the same-vocabulary rule is re-applied here to keep a cross-vocabulary row out
        through any save path (the #15/#16/#17 pattern).
        """
        self._reject_cross_scheme()
        super().save(*args, **kwargs)
