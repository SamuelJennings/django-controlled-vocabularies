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
    Collection,
    CollectionMember,
    Concept,
    ConceptLabel,
    ConceptNote,
    ConceptRelation,
    ConceptScheme,
)
from tests.testapp.models import (
    Artifact,
    Deposit,
    FieldNote,
    Outcrop,
    Photograph,
    RockSample,
    Sample,
    Specimen,
    Survey,
)


class ConceptSchemeFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`ConceptScheme` with an app-wide-unique name.

    The opt-in ``external`` trait gives the scheme a fixed, plausible externally
    assigned ``static_uri`` (FS-005), as if it had arrived from an import
    rather than been authored here.
    """

    class Meta:
        model = ConceptScheme

    name = factory.Sequence(lambda n: f"Vocabulary {n}")

    class Params:
        external = factory.Trait(
            static_uri=factory.Sequence(lambda n: f"http://publisher.example.org/vocab/{n}"),
        )


class ConceptFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`Concept`, auto-creating its owning scheme.

    ``label`` is the preferred label in the scheme's effective default language
    (``en`` in the test suite) — the concept's identity anchor. The opt-in
    ``multilingual`` trait hangs a second-language preferred label plus notes off
    the concept so a single ``ConceptFactory(multilingual=True)`` call yields a
    concept whose preferred labels and notes span more than one language. The
    opt-in ``external`` trait gives the concept a fixed, plausible externally
    assigned ``static_uri`` (FS-005), independent of its (by default,
    provisional) scheme's own identifier.
    """

    class Meta:
        model = Concept

    scheme = factory.SubFactory(ConceptSchemeFactory)
    label = factory.Sequence(lambda n: f"Concept {n}")

    class Params:
        external = factory.Trait(
            static_uri=factory.Sequence(lambda n: f"http://publisher.example.org/concept/{n}"),
        )
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


class CollectionFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`Collection`, auto-creating its owning scheme.

    ``name`` drives the derived, per-scheme-unique slug via a sequence so repeated
    calls never collide. Unordered by default; pass ``ordered=True`` for an ordered
    collection. The opt-in ``external`` trait gives the collection a fixed,
    plausible externally assigned ``static_uri`` (FS-005).
    """

    class Meta:
        model = Collection

    scheme = factory.SubFactory(ConceptSchemeFactory)
    name = factory.Sequence(lambda n: f"Collection {n}")

    class Params:
        external = factory.Trait(
            static_uri=factory.Sequence(lambda n: f"http://publisher.example.org/collection/{n}"),
        )


class CollectionMemberFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`CollectionMember` joining a collection to a concept.

    ``collection`` and ``concept`` are auto-created in the *same* scheme — a
    membership is intra-vocabulary — via ``SelfAttribute`` so the cross-vocabulary
    guard never trips.
    """

    class Meta:
        model = CollectionMember

    collection = factory.SubFactory(CollectionFactory)
    concept = factory.SubFactory(ConceptFactory, scheme=factory.SelfAttribute("..collection.scheme"))


def collection_with_members(scheme=None, labels=("Granite", "Basalt", "Gabbro"), ordered=False):
    """Build a collection populated with concepts and return ``(collection, members)``.

    The concepts are created in the collection's own scheme and added through
    :meth:`Collection.add` (so validation and, for an ordered collection, positions are
    honoured). ``members`` is the list in the order they were added — for an ordered
    collection this is the sequence :meth:`Collection.members` reads back. Lets a test
    assert on a populated (or ordered) collection in a couple of lines.
    """
    scheme = scheme or ConceptSchemeFactory()
    collection = CollectionFactory(scheme=scheme, ordered=ordered)
    members = [ConceptFactory(scheme=scheme, label=label) for label in labels]
    for concept in members:
        collection.add(concept)
    return collection, members


class SpecimenFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`~tests.testapp.models.Specimen` (T002), whose
    ``rock_type`` is required — auto-created via a plain :class:`ConceptFactory`
    concept, since :class:`ConceptField` places no constraint on a concept's
    own scheme slug beyond what a consuming record's ``full_clean()`` checks.
    """

    class Meta:
        model = Specimen

    name = factory.Sequence(lambda n: f"Specimen {n}")
    rock_type = factory.SubFactory(ConceptFactory)


class SampleFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`~tests.testapp.models.Sample` (T002). ``mineral``
    is optional and left unset by default — pass a concept explicitly where a
    test needs one attached."""

    class Meta:
        model = Sample

    name = factory.Sequence(lambda n: f"Sample {n}")


class ArtifactFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`~tests.testapp.models.Artifact` (T002) — the model
    whose own ``get_mineral_label()`` T011's collision guard must leave alone.
    ``mineral`` is optional and left unset by default."""

    class Meta:
        model = Artifact

    name = factory.Sequence(lambda n: f"Artifact {n}")


class DepositFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`~tests.testapp.models.Deposit` (FS-010 T003).
    ``rock_types`` is a many-valued relation and cannot be set at
    construction — attach concepts with ``.add()`` after the instance
    exists, as :class:`~tests.testapp.models.Deposit`'s own tests do."""

    class Meta:
        model = Deposit

    name = factory.Sequence(lambda n: f"Deposit {n}")


class SurveyFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`~tests.testapp.models.Survey` (FS-010 T003), whose
    two ``ConceptsField``s (``primary_minerals``, ``secondary_minerals``) are
    both left unset by default, for the same reason as
    :class:`DepositFactory`."""

    class Meta:
        model = Survey

    name = factory.Sequence(lambda n: f"Survey {n}")


class OutcropFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`~tests.testapp.models.Outcrop` (FS-010 T001).
    ``minerals`` is optional and left unset by default, for the same reason
    as :class:`DepositFactory`."""

    class Meta:
        model = Outcrop

    name = factory.Sequence(lambda n: f"Outcrop {n}")


class RockSampleFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`~tests.testapp.models.RockSample` (FS-010 T001).
    ``primary_mineral`` (``ConceptField``) and ``associated_minerals``
    (``ConceptsField``) are both optional and left unset by default."""

    class Meta:
        model = RockSample

    name = factory.Sequence(lambda n: f"Rock sample {n}")


class FieldNoteFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`~tests.testapp.models.FieldNote` (FS-010 T001).
    ``keywords`` is optional and left unset by default."""

    class Meta:
        model = FieldNote

    name = factory.Sequence(lambda n: f"Field note {n}")


class PhotographFactory(factory.django.DjangoModelFactory):
    """Build a saved :class:`~tests.testapp.models.Photograph` (FS-010 T001).
    ``keywords`` is optional and left unset by default."""

    class Meta:
        model = Photograph

    name = factory.Sequence(lambda n: f"Photograph {n}")
