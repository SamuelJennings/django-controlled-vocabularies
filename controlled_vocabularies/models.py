"""Models for controlled_vocabularies.

The relational models are the source of truth for a vocabulary and its concepts.
In this slice a vocabulary is a :class:`ConceptScheme`; its identifier (URI) is
computed from a configured base address and the slug, never stored (research R1).
"""

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from controlled_vocabularies import conf


class ConceptScheme(models.Model):
    """A controlled vocabulary — a named container for concepts (a SKOS concept scheme).

    The ``slug`` is derived from ``name`` on every save (dynamic while unpublished,
    research R5) and is unique app-wide. The ``uri`` is composed on read.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=255, unique=True, allow_unicode=True)

    def __str__(self) -> str:
        return self.name

    @property
    def uri(self) -> str:
        """The scheme's URI: the configured base address plus its slug."""
        return f"{conf.get_base_uri()}/{self.slug}"

    def save(self, *args, **kwargs):
        """Derive the slug from ``name`` and refuse an empty or colliding slug."""
        self.slug = slugify(self.name, allow_unicode=True)
        if not self.slug:
            raise ValidationError({"name": "Name must produce a non-empty slug."})
        # Refuse a slug that collides with another scheme rather than minting a
        # duplicate identifier or silently auto-suffixing it (research R4).
        if ConceptScheme.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError({"slug": f"A vocabulary with the slug '{self.slug}' already exists."})
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

    scheme = models.ForeignKey(ConceptScheme, on_delete=models.CASCADE, related_name="concepts")
    label = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, allow_unicode=True)

    objects = ConceptManager()

    class Meta:
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
            raise ValidationError({"label": "Label must produce a non-empty slug."})
        # Refuse a slug that collides with another concept in the same scheme
        # rather than minting a duplicate identifier or silently auto-suffixing
        # it (research R4). The UniqueConstraint is the integrity backstop.
        if Concept.objects.filter(scheme=self.scheme, slug=self.slug).exclude(pk=self.pk).exists():
            raise ValidationError({"slug": f"A concept with the slug '{self.slug}' already exists in this vocabulary."})
        super().save(*args, **kwargs)
