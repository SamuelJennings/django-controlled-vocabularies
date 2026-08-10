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
from django.apps import apps
from django.core.management import CommandError, call_command
from django.utils.functional import Promise

from controlled_vocabularies.exchange.skos import import_skos
from controlled_vocabularies.management import sources
from controlled_vocabularies.management.commands import import_skos as import_skos_command
from controlled_vocabularies.management.commands.import_skos import Command
from controlled_vocabularies.models import Concept, ConceptScheme

FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "skos"
SECURITY_FIXTURES = Path(__file__).parent.parent.parent / "fixtures" / "security"
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

    def test_a_connection_that_never_answers_fails_on_a_timeout_rather_than_hanging(
        self, db, hanging_socket, monkeypatch
    ):
        # The shipped timeout is set for real publishers, which is far longer than a test
        # should wait to prove the same behaviour.
        monkeypatch.setattr(sources, "_TIMEOUT_SECONDS", 0.5)
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


class TestImportSkosCommandRehearsal:
    """T012, spec Acceptance Scenario 1, `decisions.md` D4, `research.md` R5 — `--rehearse`
    runs the whole import inside an outer transaction it then abandons. `transactional_db`,
    not `db`: under `db` the test itself already runs inside a transaction rolled back at the
    end, which would make a broken rehearsal (one that never actually rolls back) pass anyway.
    """

    @staticmethod
    def _snapshot() -> dict[str, list[dict[str, object]]]:
        """Every row of every model this app defines, field values included — proves every
        table is unchanged rather than only that row counts match (tasks.md T012)."""
        return {
            model._meta.label: list(model.objects.order_by("pk").values())  # type: ignore[attr-defined]
            for model in apps.get_app_config("controlled_vocabularies").get_models()
        }

    def test_a_rehearsal_against_a_populated_database_leaves_every_table_unchanged(self, transactional_db):
        import_skos(FIXTURES / "rocks.ttl")
        before = self._snapshot()

        call_command("import_skos", str(FIXTURES / "rocks_updated.ttl"), rehearse=True, stdout=StringIO())

        assert self._snapshot() == before

    def test_a_rehearsal_of_a_new_vocabulary_against_an_empty_database_creates_nothing(self, transactional_db):
        before = self._snapshot()

        call_command("import_skos", str(FIXTURES / "rocks.ttl"), rehearse=True, stdout=StringIO())

        assert self._snapshot() == before
        assert ConceptScheme.objects.count() == 0


class TestImportSkosCommandRehearsalFidelity:
    """T013, spec Acceptance Scenarios 2-3, SC-003 — a rehearsal and a live run against the
    same starting state produce equal reports, compared by bucket rather than by rendered
    text; a source that would be refused is refused the same way whether rehearsed or not."""

    def test_a_rehearsal_and_a_live_run_against_the_same_state_produce_equal_reports(
        self, transactional_db, monkeypatch
    ):
        import_skos(FIXTURES / "rocks.ttl")

        captured = []
        real_import_skos = import_skos_command.import_skos

        def spy(*args, **kwargs):
            report = real_import_skos(*args, **kwargs)
            captured.append(report)
            return report

        monkeypatch.setattr(import_skos_command, "import_skos", spy)

        call_command("import_skos", str(FIXTURES / "rocks_updated.ttl"), rehearse=True, stdout=StringIO())
        rehearsed_report = captured.pop()

        call_command("import_skos", str(FIXTURES / "rocks_updated.ttl"), stdout=StringIO())
        live_report = captured.pop()

        assert rehearsed_report.created == live_report.created
        assert rehearsed_report.updated == live_report.updated
        assert rehearsed_report.set_aside == live_report.set_aside
        assert rehearsed_report.normalized == live_report.normalized
        assert rehearsed_report.absent_from_source == live_report.absent_from_source
        assert rehearsed_report.fatal == live_report.fatal == []

    def test_a_refused_source_is_reported_as_refused_when_rehearsed_and_still_exits_non_zero(self, transactional_db):
        with pytest.raises(CommandError):
            call_command("import_skos", str(FIXTURES / "no_scheme_declared.ttl"), rehearse=True, stdout=StringIO())
        assert ConceptScheme.objects.count() == 0


class TestImportSkosCommandRehearsalLine:
    """T014, FR-010, `decisions.md` D9 — the rehearsal line reaches the command's actual
    output: present for a rehearsal, absent for a live run of the same source."""

    def test_the_rehearsal_line_is_present_for_a_rehearsal_and_absent_for_a_live_run(self, db):
        rehearsal_out = StringIO()
        call_command("import_skos", str(FIXTURES / "rocks.ttl"), rehearse=True, stdout=rehearsal_out)
        assert "nothing was kept" in rehearsal_out.getvalue()

        live_out = StringIO()
        call_command("import_skos", str(FIXTURES / "rocks.ttl"), stdout=live_out)
        assert "nothing was kept" not in live_out.getvalue()


class TestImportSkosCommandRefusalPrintsEveryFatalFinding:
    """T020, FR-011, spec US-5 Acceptance Scenario 3 — where the importer collects more than
    one fatal finding, the command prints all of them, not only the first; the exit status
    is non-zero; the database is unchanged. ``multiple_fatal_problems.ttl`` already carries
    two distinct fatal findings at the exchange layer (test_exchange/test_skos.py
    ``TestFatalFindingsAndAtomicity``) — surfaced here unchanged, not re-detected."""

    def test_every_fatal_finding_prints_not_just_the_first(self, db):
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", str(FIXTURES / "multiple_fatal_problems.ttl"), stdout=StringIO())
        message = str(exc_info.value)
        assert "'Nameless' has no identifier that survives re-serialization" in message
        assert "'ftp://mirror.example.org/mixed/refused' is not an identifier the application accepts" in message
        assert exc_info.value.returncode != 0
        assert ConceptScheme.objects.count() == 0
        assert Concept.objects.count() == 0


class TestImportSkosCommandRefusesAnUndeterminedVocabulary:
    """T021, FR-013, spec US-5 Acceptance Scenario 1, decisions.md D2 — a source declaring no
    concept scheme is refused as not being SKOS, which falls out of the existing
    ``VOCABULARY_UNDETERMINED`` fatal because the command names no target. The same refusal
    covers two further spec Edge Cases that reach it for the same reason: an empty file, and
    a file that parses to a graph carrying no SKOS content at all, both refused rather than
    importing an empty vocabulary. The two new fixtures are built under ``tmp_path``, not
    committed to ``tests/fixtures/skos/``, per decisions.md D11's own precedent."""

    _NOT_SKOS_MESSAGE = "declares no vocabulary of its own, and no target vocabulary was named"

    def test_a_source_declaring_no_concept_scheme_is_refused_as_not_skos(self, db):
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", str(FIXTURES / "no_scheme_declared.ttl"), stdout=StringIO())
        assert self._NOT_SKOS_MESSAGE in str(exc_info.value)
        assert exc_info.value.returncode != 0
        assert ConceptScheme.objects.count() == 0

    def test_an_empty_file_is_refused_rather_than_importing_an_empty_vocabulary(self, db, tmp_path):
        empty = tmp_path / "empty.ttl"
        empty.write_text("")
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", str(empty), stdout=StringIO())
        assert self._NOT_SKOS_MESSAGE in str(exc_info.value)
        assert exc_info.value.returncode != 0
        assert ConceptScheme.objects.count() == 0

    def test_a_graph_with_no_skos_content_is_refused_rather_than_importing_an_empty_vocabulary(self, db, tmp_path):
        no_skos = tmp_path / "no_skos.ttl"
        no_skos.write_text(
            '@prefix dc: <http://purl.org/dc/elements/1.1/> .\n<http://example.org/thing> dc:title "Just a thing" .\n'
        )
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", str(no_skos), stdout=StringIO())
        assert self._NOT_SKOS_MESSAGE in str(exc_info.value)
        assert exc_info.value.returncode != 0
        assert ConceptScheme.objects.count() == 0


class TestImportSkosCommandSafetyScanRefusalReachedFromBothSourceForms:
    """T021, spec US-5 Acceptance Scenario 2 — a source the safety scan refuses is refused
    with that reason and nothing parses further, proven from a filesystem path and from a
    URL served over ``http_stub`` (T006), no real network call either way. Reinstates the
    same measured fixtures ``test_exchange/test_skos.py`` already proves are wired to the
    scan (``entity_bomb.rdf``, ``remote_context_string.jsonld``), surfaced through the
    command rather than re-detected."""

    def test_an_unsafe_rdf_xml_document_is_refused_from_a_path(self, db):
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", str(SECURITY_FIXTURES / "entity_bomb.rdf"), stdout=StringIO())
        assert "e0" in str(exc_info.value)
        assert exc_info.value.returncode != 0
        assert ConceptScheme.objects.count() == 0

    def test_an_unsafe_rdf_xml_document_is_refused_from_a_url(self, db, http_stub):
        body = (SECURITY_FIXTURES / "entity_bomb.rdf").read_bytes()
        http_stub.set_response("/entity_bomb.rdf", status=200, body=body, content_type="application/rdf+xml")
        url = http_stub.url + "/entity_bomb.rdf"
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", url, stdout=StringIO())
        assert "e0" in str(exc_info.value)
        assert exc_info.value.returncode != 0
        assert ConceptScheme.objects.count() == 0

    def test_an_unsafe_json_ld_document_is_refused_from_a_path(self, db):
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", str(SECURITY_FIXTURES / "remote_context_string.jsonld"), stdout=StringIO())
        assert "http://127.0.0.1:1/x.json" in str(exc_info.value)
        assert exc_info.value.returncode != 0
        assert ConceptScheme.objects.count() == 0

    def test_an_unsafe_json_ld_document_is_refused_from_a_url(self, db, http_stub):
        body = (SECURITY_FIXTURES / "remote_context_string.jsonld").read_bytes()
        http_stub.set_response(
            "/remote_context_string.jsonld", status=200, body=body, content_type="application/ld+json"
        )
        url = http_stub.url + "/remote_context_string.jsonld"
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", url, stdout=StringIO())
        assert "http://127.0.0.1:1/x.json" in str(exc_info.value)
        assert exc_info.value.returncode != 0
        assert ConceptScheme.objects.count() == 0


class TestImportSkosCommandSurfacesAnAmbiguousVocabularyRefusalUnchanged:
    """T021, spec Edge Cases — a source declaring more than one concept scheme is already
    refused by the importer (test_exchange/test_skos.py
    ``TestChoosingBetweenDeclaredVocabularies``); the command surfaces that refusal
    unchanged rather than reinterpreting it."""

    def test_a_source_declaring_more_than_one_concept_scheme_is_refused_unchanged(self, db):
        with pytest.raises(CommandError) as exc_info:
            call_command("import_skos", str(FIXTURES / "two_vocabularies.ttl"), stdout=StringIO())
        message = str(exc_info.value)
        assert "http://example.org/alpha/" in message
        assert "http://example.org/beta/" in message
        assert exc_info.value.returncode != 0
        assert ConceptScheme.objects.count() == 0
