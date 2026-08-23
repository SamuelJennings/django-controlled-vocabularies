"""``seed_demo`` is one command, destructive and repeatable (T016, FR-016, User Story 3
scenarios 2 and 3).

Runs the real command against the test database via ``call_command`` given a ``Command``
instance directly, rather than by name — the standard way to exercise a management command
that lives in an app not installed for the test suite (``demo`` carries only the front end's
own settings and urlconf under ``tests.settings``, T015). Nothing about the command itself is
faked: the same ``ConceptScheme``/``Concept`` models and the same
``controlled_vocabularies.exchange.import_skos`` path a real run uses.

There is no ``demo/management/commands/test_seed_demo.py`` for this to mirror by Article X's
own rule — this file's subject is the command's observable behaviour against the demo's own
seed content, not a module under ``controlled_vocabularies/`` — so it is part of the
``tests/test_demo/`` non-mirror exception (``[tool.forge.conformance] non-mirror-paths``, T015).
"""

import pytest
from django.core.management import call_command

from controlled_vocabularies.models import Concept, ConceptScheme
from demo.management.commands.seed_demo import Command


def run_seed_demo():
    call_command(Command())


@pytest.mark.django_db
class TestSeedDemo:
    """FR-016, User Story 3 scenarios 2 and 3."""

    def test_both_vocabularies_exist_with_their_concepts_after_one_run(self):
        run_seed_demo()
        schemes = list(ConceptScheme.objects.all())
        assert len(schemes) == 2
        for scheme in schemes:
            assert scheme.concepts.count() > 0

    def test_a_second_run_returns_the_same_counts(self):
        run_seed_demo()
        first = {scheme.name: scheme.concepts.count() for scheme in ConceptScheme.objects.all()}

        run_seed_demo()
        second = {scheme.name: scheme.concepts.count() for scheme in ConceptScheme.objects.all()}

        assert first == second

    def test_a_vocabulary_added_by_hand_between_runs_is_gone_afterwards(self):
        run_seed_demo()
        ConceptScheme.objects.create(name="Added by hand")

        run_seed_demo()

        assert not ConceptScheme.objects.filter(name="Added by hand").exists()

    def test_one_vocabulary_reads_as_imported_and_the_other_as_authored_here(self):
        run_seed_demo()

        imported = ConceptScheme.objects.exclude(static_uri__isnull=True)
        authored = ConceptScheme.objects.filter(static_uri__isnull=True)

        assert imported.count() == 1
        assert authored.count() == 1

    def test_seeded_concepts_carry_alternative_and_hidden_labels_through_the_real_importer(self):
        # T016, US-3: a search can find something a reader is never shown, which needs a
        # hidden label content asserting on a search cannot exercise. Loaded through
        # import_skos() (seed_demo.py), never a fixture behind it — the same path a real
        # project's own import runs.
        run_seed_demo()

        dataset = Concept.objects.get(label="Dataset")
        assert dataset.alt_labels("en") == ["Data set"]
        # A plausible misspelling of the seeded term, not an arbitrary string — the one a
        # reader might actually type without knowing the concept is called "Dataset".
        assert dataset.hidden_labels("en") == ["Datset"]

        fieldwork = Concept.objects.get(label="Fieldwork")
        assert fieldwork.alt_labels("en") == ["Field work"]
        assert fieldwork.hidden_labels("en") == ["Feildwork"]

    def test_a_second_run_does_not_duplicate_the_seeded_labels(self):
        run_seed_demo()
        run_seed_demo()

        dataset = Concept.objects.get(label="Dataset")
        assert dataset.alt_labels("en") == ["Data set"]
        assert dataset.hidden_labels("en") == ["Datset"]
