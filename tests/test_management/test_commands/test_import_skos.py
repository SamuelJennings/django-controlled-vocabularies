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
import socket
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


class TestImportSkosCommandFormatOption:
    """T005 — spec Acceptance Scenario 3: `--format` reaches `from_file` as the `serialization`
    keyword, the same one the programmatic entry point already accepts. The command does not
    reimplement format guessing (tasks.md T005) — a fixture built under `tmp_path` rather than
    committed to `tests/fixtures/skos/`, per decisions.md D11's own precedent, so it is never
    swept by `TestEverySkosPredicateIsReadOrReported`'s directory walk."""

    def test_a_file_whose_extension_names_no_format_imports_when_format_is_given(self, db, tmp_path):
        mystery = tmp_path / "vocab.mysteryext"
        mystery.write_bytes((FIXTURES / "rocks.ttl").read_bytes())
        call_command("import_skos", str(mystery), format="turtle", stdout=StringIO())
        assert ConceptScheme.objects.filter(static_uri=ROCKS_URI).exists()

    def test_the_same_file_without_format_is_refused_with_the_existing_message(self, db, tmp_path):
        mystery = tmp_path / "vocab.mysteryext"
        mystery.write_bytes((FIXTURES / "rocks.ttl").read_bytes())
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", str(mystery), stdout=StringIO())
        assert "not in a serialization this application reads" in str(exc_info.value)
        assert ConceptScheme.objects.count() == 0


class TestImportSkosCommandURLFailureModes:
    """T010, FR-014, spec Edge Cases — every URL retrieval failure exits non-zero (raises
    `CommandError`), names the URL, and leaves the database untouched. Uses `http_stub` and
    `hanging_socket` (tests/conftest.py, T006) — no real network call anywhere in this class."""

    def test_an_unreachable_host_is_refused_naming_the_url(self, db):
        # A closed local socket: connecting to it fails immediately with "connection refused" —
        # a local failure, not a real network call.
        closed = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        closed.bind(("127.0.0.1", 0))
        port = closed.getsockname()[1]
        closed.close()
        url = f"http://127.0.0.1:{port}/vocab.ttl"
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", url, stdout=StringIO())
        assert url in str(exc_info.value)
        assert ConceptScheme.objects.count() == 0

    def test_a_non_2xx_status_is_refused_naming_the_url(self, db, http_stub):
        http_stub.set_response("/vocab.ttl", status=500, body=b"boom")
        url = http_stub.url + "/vocab.ttl"
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", url, stdout=StringIO())
        assert url in str(exc_info.value)
        assert ConceptScheme.objects.count() == 0

    def test_an_html_body_fails_as_unreadable_content_not_an_empty_vocabulary(self, db, http_stub):
        http_stub.set_response(
            "/vocab.ttl", status=200, body=b"<html><body>Not a vocabulary</body></html>", content_type="text/html"
        )
        url = http_stub.url + "/vocab.ttl"
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", url, stdout=StringIO())
        assert url in str(exc_info.value)
        assert "could not be parsed" in str(exc_info.value)
        assert ConceptScheme.objects.count() == 0

    def test_a_connection_that_never_answers_fails_on_a_timeout_rather_than_hanging(self, db, hanging_socket):
        url = hanging_socket
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", url, stdout=StringIO())
        assert url in str(exc_info.value)
        assert ConceptScheme.objects.count() == 0


class TestImportSkosCommandURLParity:
    """T011, SC-002, FR-003 — `SourceResolver` wired into `Command`: a URL import of a document
    with absolute identifiers produces the same records and report as the identical bytes from
    disk, and a document with relative identifiers is stored under the address it was served
    from, never under a `file://` path (decisions.md D10)."""

    _RELATIVE_URIS_TURTLE = """
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

<>
    a skos:ConceptScheme ;
    skos:prefLabel "Relative vocabulary"@en ;
    skos:hasTopConcept <concept-a> .

<concept-a>
    a skos:Concept ;
    skos:inScheme <> ;
    skos:topConceptOf <> ;
    skos:prefLabel "Concept A"@en .
"""

    def test_a_url_import_and_a_disk_import_of_absolute_identifiers_produce_the_same_records_and_report(
        self, db, http_stub
    ):
        rocks_bytes = (FIXTURES / "rocks.ttl").read_bytes()
        http_stub.set_response("/rocks.ttl", status=200, body=rocks_bytes, content_type="text/turtle")

        url_out = StringIO()
        call_command("import_skos", http_stub.url + "/rocks.ttl", stdout=url_out)
        url_records = set(Concept.objects.values_list("static_uri", flat=True))
        url_scheme_name = ConceptScheme.objects.get(static_uri=ROCKS_URI).name
        url_report = url_out.getvalue()

        Concept.objects.all().delete()
        ConceptScheme.objects.all().delete()

        disk_out = StringIO()
        call_command("import_skos", str(FIXTURES / "rocks.ttl"), stdout=disk_out)
        disk_records = set(Concept.objects.values_list("static_uri", flat=True))
        disk_scheme_name = ConceptScheme.objects.get(static_uri=ROCKS_URI).name

        assert url_records == disk_records
        assert url_scheme_name == disk_scheme_name
        assert url_report == disk_out.getvalue()

    def test_relative_identifiers_are_stored_under_the_stubs_address_not_a_file_path(self, db, http_stub):
        http_stub.set_response(
            "/relative.ttl", status=200, body=self._RELATIVE_URIS_TURTLE.encode(), content_type="text/turtle"
        )
        scheme_uri = http_stub.url + "/relative.ttl"
        concept_uri = http_stub.url + "/concept-a"
        call_command("import_skos", scheme_uri, stdout=StringIO())
        assert ConceptScheme.objects.filter(static_uri=scheme_uri).exists()
        assert Concept.objects.filter(static_uri=concept_uri).exists()
        assert not ConceptScheme.objects.filter(static_uri__startswith="file://").exists()
        assert not Concept.objects.filter(static_uri__startswith="file://").exists()
