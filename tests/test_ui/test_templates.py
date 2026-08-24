"""Tests proving the ui templates carry no vocabulary link and no untranslated reader-visible
text (T009, FR-013, decisions.md D1, and the repo's every-string-translated convention), and,
from 015-read-single-record T002, the ``property_row`` component's own rendering and CSS.
"""

import re
from pathlib import Path

import mvp
import pytest
from bs4 import BeautifulSoup
from django.template.loader import render_to_string
from django.urls import reverse

from tests.factories import ConceptSchemeFactory

TEMPLATES_ROOT = Path(__file__).resolve().parents[2] / "controlled_vocabularies" / "ui" / "templates"
ROW_TEMPLATE_PATH = TEMPLATES_ROOT / "controlled_vocabularies" / "ui" / "conceptscheme_list_item.html"
CONCEPT_ROW_TEMPLATE_PATH = TEMPLATES_ROOT / "controlled_vocabularies" / "ui" / "concept_list_item.html"
PROPERTY_ROW_TEMPLATE = "cotton/controlled_vocabularies/property_row.html"
PROPERTY_ROW_TEMPLATE_PATH = TEMPLATES_ROOT / "cotton" / "controlled_vocabularies" / "property_row.html"
# mvp is a namespace package (no __init__.py), so it carries no __file__ — its own
# __path__ is the only way to locate the package directory.
MVP_CSS_PATH = Path(mvp.__path__[0]) / "static" / "css" / "django-mvp.css"

# Django syntax that is already known-safe and is stripped before the reader-visible-text scan:
# a developer comment, a blocktrans block (translated, content and all), any remaining tag
# (including a `{% trans %}` — its quoted content is translated, so removing tag and content
# together is correct), and a variable interpolation (dynamic — not a literal string this
# template owns the wording of).
_COMMENT_RE = re.compile(r"{%\s*comment\s*%}.*?{%\s*endcomment\s*%}", re.DOTALL)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_BLOCKTRANS_RE = re.compile(r"{%\s*blocktrans.*?{%\s*endblocktrans\s*%}", re.DOTALL)
_TAG_RE = re.compile(r"{%.*?%}", re.DOTALL)
_VAR_RE = re.compile(r"{{.*?}}", re.DOTALL)
_TEXT_NODE_RE = re.compile(r">([^<{]+)<")
_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def bare_reader_visible_text_nodes(source: str) -> list[str]:
    """Every text-node fragment left after Django's own translation and comment syntax is
    stripped out — a non-empty result names a string the convention (every reader-visible
    string wrapped in a translation tag) failed to wrap. Scoped to text nodes (content
    between tags), not attribute values — this app's own templates put every reader-visible
    string there deliberately, for exactly this reason (T009: attribute-value scanning
    cannot tell a literal string from a structural token like a slot name or a size key
    without a real HTML/template parser, which does not earn its cost at this app's size).
    """
    stripped = _COMMENT_RE.sub("", source)
    stripped = _HTML_COMMENT_RE.sub("", stripped)
    stripped = _BLOCKTRANS_RE.sub("", stripped)
    stripped = _TAG_RE.sub("", stripped)
    stripped = _VAR_RE.sub("", stripped)
    return [node for node in _TEXT_NODE_RE.findall(stripped) if _WORD_RE.search(node)]


class TestRowPartialLinksToTheVocabulary:
    """FR-013, T004 — the row partial's own source, the inverse of what #140 asserted here.

    #140 held that no entry may link to a vocabulary, because no address served one; T001
    gives every vocabulary a page, so the entry now leads to it. What remains true from #140
    is the second assertion: the in-site link is reversed from the route's name, never
    composed from the identifier base address, which is a public identifier and may point at
    another site's publisher entirely.
    """

    def test_the_row_partial_source_reverses_the_vocabularys_own_route(self):
        source = ROW_TEMPLATE_PATH.read_text()
        assert "{% url 'controlled_vocabularies_ui:vocabulary-detail'" in source

    def test_the_row_partial_source_contains_no_local_url_reference(self):
        source = ROW_TEMPLATE_PATH.read_text()
        assert "local_url" not in source


class TestRenderedPageLinksToEachVocabulary:
    """FR-013 stated the second way: scanning the page as actually rendered."""

    @pytest.mark.django_db
    def test_every_entry_on_the_page_carries_an_anchor_to_its_own_page(self, client):
        schemes = [ConceptSchemeFactory(), ConceptSchemeFactory()]

        response = client.get(reverse("controlled_vocabularies_ui:vocabulary-list"))
        content = response.content.decode()

        hrefs = re.findall(r'href="([^"]*)"', content)
        for scheme in schemes:
            assert reverse("controlled_vocabularies_ui:vocabulary-detail", kwargs={"slug": scheme.slug}) in hrefs


class TestConceptRowPartialLinksToItsOwnPage:
    """015-read-single-record T019, FR-015 — the inverse of what T008 asserted here.

    T008 held that a concept's row carries nothing to follow, because no address served
    one; this feature gives every concept a page, so the row now leads to it. The row
    renders in an isolated context holding only the object (`render_list_item` builds a
    fresh context per row), so the address is reversed from ``object.scheme`` and
    ``object.slug`` alone, never from a variable the surrounding page happens to carry.
    """

    def test_the_row_partial_source_reverses_the_concepts_own_route(self):
        source = CONCEPT_ROW_TEMPLATE_PATH.read_text()
        assert "{% url 'controlled_vocabularies_ui:concept-detail'" in source

    def test_the_row_partial_source_contains_no_local_url_reference(self):
        source = CONCEPT_ROW_TEMPLATE_PATH.read_text()
        assert "local_url" not in source


class TestEveryShippedTemplateWrapsReaderVisibleTextInATranslationTag:
    """Every reader-visible string is translatable (repo convention, checked mechanically per T009)."""

    @pytest.mark.parametrize(
        "path",
        sorted(TEMPLATES_ROOT.rglob("*.html")),
        ids=lambda p: str(p.relative_to(TEMPLATES_ROOT)),
    )
    def test_no_bare_reader_visible_text_outside_a_translation_tag(self, path):
        fragments = bare_reader_visible_text_nodes(path.read_text())
        assert fragments == []


class TestPropertyRowRendersAPlainValue:
    """A term and a plain value render as a ``<dt>``/``<dd>`` pair (T002, FR-016)."""

    def test_emits_a_dt_dd_pair_carrying_the_term_and_the_value(self):
        html = render_to_string(
            PROPERTY_ROW_TEMPLATE,
            {"term": "skos:definition", "value": "A coarse-grained igneous rock."},
        )
        soup = BeautifulSoup(html, "html.parser")

        dt = soup.find("dt")
        dd = soup.find("dd")
        assert dt is not None
        assert dd is not None
        assert dt.get_text(strip=True) == "skos:definition"
        assert "A coarse-grained igneous rock." in dd.get_text()
        # A plain value never composes a link — that only happens for a record-valued row.
        assert dd.find("a") is None


class TestPropertyRowRendersARecordValue:
    """A record-valued row also carries the record's short form, its canonical identifier
    as reader-reachable text, and its in-site link (T002, FR-016, plan.md Key design
    decision #6). ``href`` is a plain string here, exactly as :func:`render_to_string`
    receives one in isolation — reversing it through the app's own namespace is the
    caller's job (T003), not this component's.
    """

    def test_renders_the_short_form_as_the_in_site_links_own_text(self):
        html = render_to_string(
            PROPERTY_ROW_TEMPLATE,
            {
                "term": "skos:broader",
                "short_form": "geology:granite",
                "uri": "http://publisher.example.org/concept/granite",
                "href": "/vocabularies/geology/granite/",
            },
        )
        soup = BeautifulSoup(html, "html.parser")

        anchor = soup.find("dd").find("a", href="/vocabularies/geology/granite/")
        assert anchor is not None
        assert anchor.get_text(strip=True) == "geology:granite"

    def test_the_canonical_identifier_is_reader_reachable_text_not_a_title_attribute(self):
        # FR-007: a title attribute is invisible to a keyboard user and unreliable for a
        # screen reader, so the identifier must appear as ordinary text, not tucked away
        # in an attribute a pointer is needed to reveal.
        html = render_to_string(
            PROPERTY_ROW_TEMPLATE,
            {
                "term": "skos:broader",
                "short_form": "geology:granite",
                "uri": "http://publisher.example.org/concept/granite",
                "href": "/vocabularies/geology/granite/",
            },
        )
        soup = BeautifulSoup(html, "html.parser")
        dd = soup.find("dd")

        assert "http://publisher.example.org/concept/granite" in dd.get_text()
        for element in dd.find_all(True):
            assert element.get("title") is None


def _tailwind_selector(class_token: str) -> str:
    """The class selector as the shipped stylesheet actually spells it: Tailwind
    backslash-escapes a colon or a slash inside a compiled class name (memory: "built CSS
    escapes the colon" — the same is true of the slash a class like
    ``text-base-content/60`` carries), so a plain ``.token{`` search returns a false zero
    for a class that is plainly present.
    """
    escaped = class_token.replace("/", r"\/").replace(":", r"\:")
    return f".{escaped}{{"


class TestPropertyRowClasses:
    """Every class the component names by hand is present in django-mvp's own shipped
    stylesheet (T002) — this package ships none of its own, and django-mvp's is prebuilt
    from django-mvp's own templates, so an invented class would be silently inert.
    """

    def test_every_class_the_component_names_is_present_in_the_shipped_stylesheet(self):
        source = PROPERTY_ROW_TEMPLATE_PATH.read_text()
        css = MVP_CSS_PATH.read_text()

        tokens = {token for group in re.findall(r'class="([^"]*)"', source) for token in group.split()}

        assert tokens, "the component names no class at all — nothing for this test to prove"
        for token in tokens:
            assert _tailwind_selector(token) in css, f"{token!r} is not in the shipped stylesheet"

    def test_the_presence_check_discriminates_rather_than_passing_regardless(self):
        # A control class the build has no reason to emit: this package's own component
        # could never legitimately name it, so its absence proves the check above tells a
        # real class from an absent one instead of matching anything handed to it — which
        # is exactly the failure mode an invented class would hit in silence otherwise.
        css = MVP_CSS_PATH.read_text()
        assert _tailwind_selector("cv-property-row-invented-class") not in css
