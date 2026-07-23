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
