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
import os
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command
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


class TestImportSkosCommandRefusesABadPath:
    """T004 — spec Acceptance Scenario 4 and Edge Cases: a missing path fails naming the path,
    writes nothing, and exits non-zero via `CommandError`; a path that exists but cannot be
    opened for permission reasons is reported distinctly, not as absent (spec Edge Cases)."""

    def test_a_missing_path_is_refused_naming_the_path_and_writes_nothing(self, db):
        missing = str(FIXTURES / "does-not-exist.ttl")
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", missing, stdout=StringIO())
        assert missing in str(exc_info.value)
        assert ConceptScheme.objects.count() == 0

    @pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root ignores file permissions")
    def test_an_unreadable_path_is_reported_distinctly_from_a_missing_one(self, db, tmp_path):
        unreadable = tmp_path / "vocab.ttl"
        unreadable.write_bytes((FIXTURES / "rocks.ttl").read_bytes())
        unreadable.chmod(0o000)
        try:
            with pytest.raises(CommandError) as missing_exc:
                call_command("import_skos", str(FIXTURES / "does-not-exist.ttl"), stdout=StringIO())
            with pytest.raises(CommandError) as unreadable_exc:
                call_command("import_skos", str(unreadable), stdout=StringIO())
        finally:
            unreadable.chmod(0o644)
        assert str(missing_exc.value) != str(unreadable_exc.value)
        assert "is not readable" in str(unreadable_exc.value)
        assert "is not readable" not in str(missing_exc.value)
        assert ConceptScheme.objects.count() == 0
