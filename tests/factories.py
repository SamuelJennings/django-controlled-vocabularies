"""factory_boy factories for the vocabulary models.

Downstream stories build their fixtures on these instead of hand-constructing
schemes and concepts. Both factories drive the human-facing field (``name`` /
``label``) via a sequence so the derived, uniqueness-guarded slugs never collide
across repeated calls: ``ConceptScheme.slug`` is unique app-wide and
``Concept.slug`` is unique within its scheme, and the models raise
``ValidationError`` on a collision rather than auto-suffixing.
"""

import factory

from controlled_vocabularies.models import (
    Concept,
    ConceptLabel,
    ConceptNote,
    ConceptRelation,
    ConceptScheme,
)


class ConceptSchemeFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`ConceptScheme` with an app-wide-unique name."""

    class Meta:
        model = ConceptScheme

    name = factory.Sequence(lambda n: f"Vocabulary {n}")


class ConceptFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`Concept`, auto-creating its owning scheme.

    ``label`` is the preferred label in the scheme's effective default language
    (``en`` in the test suite) — the concept's identity anchor. The opt-in
    ``multilingual`` trait hangs a second-language preferred label plus notes off
    the concept so a single ``ConceptFactory(multilingual=True)`` call yields a
    concept whose preferred labels and notes span more than one language.
    """

    class Meta:
        model = Concept

    scheme = factory.SubFactory(ConceptSchemeFactory)
    label = factory.Sequence(lambda n: f"Concept {n}")

    class Params:
        multilingual = factory.Trait(
            # en preferred label is the anchor ``label`` above; de is a real
            # ConceptLabel PREFERRED row (the field owns only the default language).
            german_label=factory.RelatedFactory(
                "tests.factories.ConceptLabelFactory",
                factory_related_name="concept",
                language="de",
                kind=ConceptLabel.Kind.PREFERRED,
                text=factory.Sequence(lambda n: f"Konzept {n}"),
            ),
            english_note=factory.RelatedFactory(
                "tests.factories.ConceptNoteFactory",
                factory_related_name="concept",
                language="en",
                kind=ConceptNote.Kind.DEFINITION,
                value=factory.Sequence(lambda n: f"Definition {n}"),
            ),
            german_note=factory.RelatedFactory(
                "tests.factories.ConceptNoteFactory",
                factory_related_name="concept",
                language="de",
                kind=ConceptNote.Kind.DEFINITION,
                value=factory.Sequence(lambda n: f"Definition {n}"),
            ),
        )


class ConceptLabelFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`ConceptLabel`, auto-creating its owning concept.

    Defaults to a German (``de``) preferred label: a non-default-language
    preferred label is a standalone row, whereas the default language's preferred
    label lives on :attr:`Concept.label` and may not be duplicated here.
    """

    class Meta:
        model = ConceptLabel

    concept = factory.SubFactory(ConceptFactory)
    language = "de"
    kind = ConceptLabel.Kind.PREFERRED
    text = factory.Sequence(lambda n: f"Label {n}")


class ConceptNoteFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`ConceptNote`, auto-creating its owning concept.

    Defaults to an English (``en``) definition — the primary documentary note.
    """

    class Meta:
        model = ConceptNote

    concept = factory.SubFactory(ConceptFactory)
    language = "en"
    kind = ConceptNote.Kind.DEFINITION
    value = factory.Sequence(lambda n: f"Definition {n}")


class ConceptRelationFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`ConceptRelation` between two concepts in one vocabulary.

    ``source`` and ``target`` are auto-created in the *same* scheme — a relation is
    intra-vocabulary — via ``SelfAttribute`` so the cross-vocabulary guard never trips.
    ``kind`` defaults to ``BROADER`` (``source`` is the narrower/child); pass
    ``kind=ConceptRelation.Kind.RELATED`` for a symmetric association.
    """

    class Meta:
        model = ConceptRelation

    source = factory.SubFactory(ConceptFactory)
    target = factory.SubFactory(ConceptFactory, scheme=factory.SelfAttribute("..source.scheme"))
    kind = ConceptRelation.Kind.BROADER


def relation_graph(scheme=None):
    """Build a small navigable graph in one vocabulary and return its concepts.

    A broader/narrower pair (``child`` under ``parent``) and a separate related pair
    (``left`` and ``right``), all in one scheme, built through the validated write helpers
    (``add_broader``/``add_related``). Returns a dict of the pieces so a test can assert
    on the graph in a couple of lines.
    """
    scheme = scheme or ConceptSchemeFactory()
    parent = ConceptFactory(scheme=scheme)
    child = ConceptFactory(scheme=scheme)
    left = ConceptFactory(scheme=scheme)
    right = ConceptFactory(scheme=scheme)
    child.add_broader(parent)
    left.add_related(right)
    return {"scheme": scheme, "parent": parent, "child": child, "left": left, "right": right}
