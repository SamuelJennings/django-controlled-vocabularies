"""T002 — the ``management`` package skeleton (Article XIV).

No behaviour lands here: this only proves the package the command (T003
onward) and the renderer (T015) build on is importable. The command itself
is out of this story's scope.

T003 onward (below): the ``import_skos`` command itself — one positional
``source``, a ``--format`` option, and ``handle()`` delegating the whole
import to :func:`~controlled_vocabularies.exchange.skos.import_skos` and
rendering the result through :class:`~controlled_vocabularies.management.rendering.ReportRenderer`
(plan.md "Rendering", tasks.md US-1).
"""

import importlib
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.utils.functional import Promise

from controlled_vocabularies.management.commands.import_skos import Command
from controlled_vocabularies.models import Concept, ConceptScheme

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "skos"
ROCKS_URI = "http://example.org/rocks/"


class TestManagementPackageSkeleton:
    def test_management_package_is_importable(self):
        module = importlib.import_module("controlled_vocabularies.management")
        assert module.__file__ is not None

    def test_management_commands_package_is_importable(self):
        module = importlib.import_module("controlled_vocabularies.management.commands")
        assert module.__file__ is not None


class TestImportSkosCommandCreatesAndUpdates:
    """T003 — spec Acceptance Scenarios 1-2: an empty database gets the vocabulary and its
    concepts, named by count; a second run against the same file reports updates and creates
    no duplicate concept. Every line comes from ``ReportRenderer`` (plan.md "Rendering")."""

    def test_importing_into_an_empty_database_creates_the_vocabulary_and_names_the_count(self, db):
        out = StringIO()
        call_command("import_skos", str(FIXTURES / "rocks.ttl"), stdout=out)
        scheme = ConceptScheme.objects.get(static_uri=ROCKS_URI)
        assert scheme.name == "Rock types"
        assert Concept.objects.count() == 5
        output = out.getvalue()
        assert "8 records created." in output
        assert "0 records updated." in output

    def test_reimporting_the_same_file_reports_updates_and_creates_no_duplicate_concept(self, db):
        call_command("import_skos", str(FIXTURES / "rocks.ttl"), stdout=StringIO())
        out = StringIO()
        call_command("import_skos", str(FIXTURES / "rocks.ttl"), stdout=out)
        assert ConceptScheme.objects.filter(static_uri=ROCKS_URI).count() == 1
        assert Concept.objects.count() == 5
        output = out.getvalue()
        assert "8 records updated." in output
        assert "0 records created." in output


class TestImportSkosCommandHelpIsTranslatable:
    """T003 — Article XII: ``Command.help`` and every argument's ``help`` are ``gettext_lazy``
    from the first line written."""

    def test_command_help_is_lazily_translatable(self):
        assert isinstance(Command.help, Promise)

    def test_every_argument_help_is_lazily_translatable(self):
        # Only this command's own arguments — Django's base arguments (verbosity,
        # settings, pythonpath, ...) carry Django's own plain-str help and are not
        # this story's to translate.
        command = Command()
        parser = command.create_parser("manage.py", "import_skos")
        ours = {action.dest: action for action in parser._actions if action.dest in ("source", "format")}
        assert set(ours) == {"source", "format"}
        for dest, action in ours.items():
            assert action.help, f"{dest} has no help text"
            assert isinstance(action.help, Promise), f"{dest} help is not lazily translatable"
