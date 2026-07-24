"""factory_boy factories for the vocabulary models.

Downstream stories build their fixtures on these instead of hand-constructing
schemes and concepts. Both factories drive the human-facing field (``name`` /
``label``) via a sequence so the derived, uniqueness-guarded slugs never collide
across repeated calls: ``ConceptScheme.slug`` is unique app-wide and
``Concept.slug`` is unique within its scheme, and the models raise
``ValidationError`` on a collision rather than auto-suffixing.
"""

import factory

from controlled_vocabularies.models import Concept, ConceptScheme


class ConceptSchemeFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`ConceptScheme` with an app-wide-unique name."""

    class Meta:
        model = ConceptScheme

    name = factory.Sequence(lambda n: f"Vocabulary {n}")


class ConceptFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`Concept`, auto-creating its owning scheme."""

    class Meta:
        model = Concept

    scheme = factory.SubFactory(ConceptSchemeFactory)
    label = factory.Sequence(lambda n: f"Concept {n}")
